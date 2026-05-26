import json
import calendar
from datetime import date
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from apps.nutrition.models import Food, FoodIngredient, IngredientPrice
from apps.meal_plans.models import MealPlan
from apps.users.views import get_current_account
from app.services.meal_plan_generator_service import MealPlanGeneratorService


MEAL_TYPES = [
    ('Bữa sáng', 'Bữa sáng'),
    ('Bữa trưa', 'Bữa trưa'),
    ('Bữa tối', 'Bữa tối'),
    ('Bữa phụ', 'Bữa phụ'),
]


def _estimate_meal_cost(meal_plan):
    """
    Ước tính chi phí của một meal plan dựa trên giá nguyên liệu từ DB.
    
    Return: float (VND) hoặc None nếu không có dữ liệu giá
    """
    food = meal_plan.food
    servings = Decimal(str(meal_plan.servings or 1))
    total_cost = Decimal('0')
    
    try:
        ingredients = FoodIngredient.objects.filter(food=food).select_related('ingredient')
        for fi in ingredients:
            price_obj = IngredientPrice.objects.filter(ingredient=fi.ingredient).first()
            if price_obj:
                # Tính cost dựa trên quantity_grams
                quantity_kg = (Decimal(str(fi.quantity_grams or 0)) * servings) / Decimal('1000')
                cost = quantity_kg * Decimal(str(price_obj.price_per_unit))
                total_cost += cost
    except Exception:
        return None
    
    return float(total_cost) if total_cost > 0 else None


def meal_plans(request):
    account = get_current_account(request)
    if not account:
        return render(request, 'error.html', {'message': 'Vui lòng đăng nhập'}, status=401)
    
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    cal = calendar.monthcalendar(year, month)

    first_day = f'{year}-{month:02d}-01'
    if month == 12:
        last_day = f'{year+1}-01-01'
    else:
        last_day = f'{year}-{month+1:02d}-01'

    # FIX: Filter by account so each user sees only their own meal plans
    plans = MealPlan.objects.filter(
        account=account,
        date__gte=first_day, 
        date__lt=last_day
    ).select_related('food')
    plans_by_date = {}
    for p in plans:
        key = str(p.date)
        plans_by_date.setdefault(key, []).append(p)

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    month_names = ['', 'Thang 1', 'Thang 2', 'Thang 3', 'Thang 4', 'Thang 5', 'Thang 6',
                   'Thang 7', 'Thang 8', 'Thang 9', 'Thang 10', 'Thang 11', 'Thang 12']

    foods = Food.objects.all().order_by('name')
    context = {
        'calendar': cal,
        'year': year,
        'month': month,
        'month_name': month_names[month],
        'plans_by_date': plans_by_date,
        'plans_by_date_json': json.dumps({k: [{'food': p.food.name, 'meal_type': p.meal_type, 'id': p.id} for p in v] for k, v in plans_by_date.items()}),
        'plans_by_date_data': {k: [{'food': p.food.name, 'meal_type': p.meal_type, 'id': p.id} for p in v] for k, v in plans_by_date.items()},
        'meal_type_colors': {
            'Bữa sáng': 'bg-warning text-dark',
            'Bữa trưa': 'bg-success text-white',
            'Bữa tối': 'bg-primary text-white',
            'Bữa phụ': 'bg-secondary text-white',
        },
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'today': today,
        'today_str': today.isoformat(),
        'foods': foods,
        'meal_types': MEAL_TYPES,
        'active': 'meal_plans',
    }
    return render(request, 'user/meal_plans.html', context)


@csrf_exempt
@require_POST
def meal_plan_add(request):
    """
    API tạo meal plan từ request user.
    
    Nhận: {
        'request': str (yêu cầu từ user, e.g. "tạo thực đơn giảm cân"),
        'date': str (YYYY-MM-DD, optional)
    }
    
    Hoặc (legacy):
    {
        'food_id': int,
        'date': str,
        'meal_type': str,
        'servings': float
    }
    """
    try:
        account = get_current_account(request)
        
        if not account:
            return JsonResponse({'error': 'Vui lòng đăng nhập'}, status=401)
        
        data = json.loads(request.body)
        
        # Kiểm tra xem là request mới (AI-based) hay legacy request
        user_request = data.get('request', '').strip()
        
        if user_request:
            # Luồng mới: tạo meal plan từ request user sử dụng AI + DB
            target_date = data.get('date')
            if target_date:
                try:
                    target_date = __import__('datetime').datetime.strptime(target_date, '%Y-%m-%d').date()
                except:
                    target_date = None
            
            result = MealPlanGeneratorService.generate_meal_plan(
                account=account,
                request_text=user_request,
                target_date=target_date,
            )
            
            if not result['success']:
                return JsonResponse({'error': result['message']}, status=400)
            
            # Format response
            meal_plans_data = []
            for plan in result['meal_plans']:
                cost = _estimate_meal_cost(plan)
                meal_plans_data.append({
                    'id': plan.id,
                    'food': plan.food.name,
                    'date': str(plan.date),
                    'meal_type': plan.meal_type,
                    'servings': float(plan.servings),
                    'calories': float((plan.food.calories or 0) * (plan.servings or 1)),
                    'cost_estimate': cost,  # Chi phí ước tính (VND)
                })
            
            
            return JsonResponse({
                'success': True,
                'meal_plans': meal_plans_data,
                'message': result['message'],
                'request_type': result['request_type'],
                'api_used': result['api_fallback_used'],
            })
        
        else:
            # Luồng legacy: add single food to meal plan
            food = get_object_or_404(Food, id=data.get('food_id'))
            plan = MealPlan.objects.create(
                account=account,
                food=food,
                date=data.get('date', date.today().isoformat()),
                meal_type=data.get('meal_type', 'Bữa sáng'),
                servings=float(data.get('servings', 1)),
                notes=data.get('notes', ''),
            )
            return JsonResponse({
                'id': plan.id,
                'food': food.name,
                'date': str(plan.date),
                'meal_type': plan.meal_type,
                'servings': float(plan.servings),
            })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as exc:
        return JsonResponse({'error': f'Internal error: {exc}'}, status=500)


@csrf_exempt
@require_POST
def meal_plan_delete(request, plan_id):
    account = get_current_account(request)
    if not account:
        return JsonResponse({'error': 'Vui lòng đăng nhập'}, status=401)
    
    # FIX: Ensure user can only delete their own meal plans
    plan = get_object_or_404(MealPlan, id=plan_id, account=account)
    plan.delete()
    return JsonResponse({'ok': True})
