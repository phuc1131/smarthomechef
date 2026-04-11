import os
import json
import random
from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

from .models import UserProfile, Food, MealPlan, NutritionLog, ChatMessage

try:
    from google import genai
    from google.genai import types as genai_types
    base_url = os.environ.get("AI_INTEGRATIONS_GEMINI_BASE_URL")
    api_key = os.environ.get("AI_INTEGRATIONS_GEMINI_API_KEY", "dummy")
    if base_url:
        ai_client = genai.Client(api_key=api_key, http_options={"base_url": base_url})
    else:
        ai_client = genai.Client(api_key=api_key)
    AI_AVAILABLE = True
except Exception:
    ai_client = None
    AI_AVAILABLE = False

MEAL_TYPES = [
    ('Bữa sáng', 'Bữa sáng'),
    ('Bữa trưa', 'Bữa trưa'),
    ('Bữa tối', 'Bữa tối'),
    ('Bữa phụ', 'Bữa phụ'),
]


def get_profile():
    return UserProfile.objects.first()


def dashboard(request):
    today = date.today().isoformat()

    today_logs = NutritionLog.objects.filter(date=today)
    today_calories = sum(float(l.total_calories or 0) for l in today_logs)
    today_protein = sum(float(l.total_protein or 0) for l in today_logs)
    today_carbs = sum(float(l.total_carbs or 0) for l in today_logs)
    today_fat = sum(float(l.total_fat or 0) for l in today_logs)

    week_start = (date.today() - timedelta(days=6)).isoformat()
    week_plans = MealPlan.objects.filter(date__gte=week_start, date__lte=today).count()
    total_foods = Food.objects.count()
    profile = get_profile()

    streak = 0
    check_date = date.today()
    for _ in range(30):
        if NutritionLog.objects.filter(date=check_date.isoformat()).exists():
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    foods = list(Food.objects.all())
    suggestions = random.sample(foods, min(4, len(foods))) if foods else []

    calorie_target = profile.daily_calorie_target if profile else 2000
    calorie_pct = min(100, int(today_calories / calorie_target * 100)) if calorie_target else 0

    context = {
        'today_calories': round(today_calories, 1),
        'today_protein': round(today_protein, 1),
        'today_carbs': round(today_carbs, 1),
        'today_fat': round(today_fat, 1),
        'calorie_target': calorie_target or 2000,
        'calorie_pct': calorie_pct,
        'meals_logged': today_logs.count(),
        'week_plans': week_plans,
        'total_foods': total_foods,
        'streak': streak,
        'profile': profile,
        'suggestions': suggestions,
        'today': date.today(),
        'active': 'dashboard',
    }
    return render(request, 'app/dashboard.html', context)


def chat_page(request):
    messages = ChatMessage.objects.all().order_by('created_at')
    messages_json = json.dumps([
        {'role': m.role, 'content': m.content}
        for m in messages
    ], ensure_ascii=False)
    return render(request, 'app/chat.html', {
        'messages_json': messages_json,
        'active': 'chat',
    })


@csrf_exempt
@require_POST
def chat_send(request):
    data = json.loads(request.body)
    user_text = data.get('message', '').strip()
    if not user_text:
        return JsonResponse({'error': 'Tin nhan trong'}, status=400)

    ChatMessage.objects.create(role='user', content=user_text)

    if not AI_AVAILABLE or not ai_client:
        msg = ChatMessage.objects.create(role='assistant', content='Xin loi, tinh nang AI chua duoc kich hoat. Vui long kiem tra cau hinh.')
        return JsonResponse({'role': msg.role, 'content': msg.content})

    profile = get_profile()
    system_context = (
        'Ban la "Noi Tro AI", tro ly noi tro thong minh nguoi Viet. '
        'Ban giup goi y mon an, tu van dinh duong va len thuc don. '
        'Hay tra loi bang tieng Viet, than thien va huu ich. '
        'Uu tien cac mon an Viet Nam truyen thong va lanh manh.\n'
    )
    if profile:
        system_context += (
            f'Nguoi dung: {profile.name}, '
            f'tuoi {profile.age or "?"}, '
            f'nang {profile.weight or "?"}kg, '
            f'muc tieu: {profile.health_goal or "chua cung cap"}.'
        )

    all_messages = ChatMessage.objects.all().order_by('created_at')
    contents = []
    for msg in all_messages:
        role = 'model' if msg.role == 'assistant' else 'user'
        contents.append(genai_types.Content(role=role, parts=[genai_types.Part(text=msg.content)]))

    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_context,
                max_output_tokens=2048,
            ),
        )
        ai_text = response.text or 'Xin loi, toi khong co cau tra loi phu hop luc nay.'
    except Exception:
        ai_text = 'Xin loi, toi gap su co khi ket noi AI. Vui long thu lai sau.'

    msg = ChatMessage.objects.create(role='assistant', content=ai_text)
    return JsonResponse({'role': msg.role, 'content': msg.content})


@csrf_exempt
@require_POST
def chat_clear(request):
    ChatMessage.objects.all().delete()
    return JsonResponse({'ok': True})


def meal_plans(request):
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    import calendar
    cal = calendar.monthcalendar(year, month)

    first_day = f'{year}-{month:02d}-01'
    if month == 12:
        last_day = f'{year+1}-01-01'
    else:
        last_day = f'{year}-{month+1:02d}-01'

    plans = MealPlan.objects.filter(date__gte=first_day, date__lt=last_day).select_related('food')
    plans_by_date = {}
    for p in plans:
        key = p.date[:10]
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
    return render(request, 'app/meal_plans.html', context)


@csrf_exempt
@require_POST
def meal_plan_add(request):
    data = json.loads(request.body)
    food = get_object_or_404(Food, id=data.get('food_id'))
    plan = MealPlan.objects.create(
        food=food,
        date=data.get('date', date.today().isoformat()),
        meal_type=data.get('meal_type', 'Bua sang'),
        servings=float(data.get('servings', 1)),
        notes=data.get('notes', ''),
    )
    return JsonResponse({'id': plan.id, 'food': food.name, 'date': plan.date, 'meal_type': plan.meal_type})


@csrf_exempt
@require_POST
def meal_plan_delete(request, plan_id):
    plan = get_object_or_404(MealPlan, id=plan_id)
    plan.delete()
    return JsonResponse({'ok': True})


def nutrition(request):
    today = date.today()
    selected_date_str = request.GET.get('date', today.isoformat())
    try:
        date.fromisoformat(selected_date_str)
    except ValueError:
        selected_date_str = today.isoformat()

    day_logs = NutritionLog.objects.filter(date=selected_date_str).select_related('food')
    total_cal = sum(float(l.total_calories or 0) for l in day_logs)
    total_pro = sum(float(l.total_protein or 0) for l in day_logs)
    total_car = sum(float(l.total_carbs or 0) for l in day_logs)
    total_fat_v = sum(float(l.total_fat or 0) for l in day_logs)

    trend = []
    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        logs = NutritionLog.objects.filter(date=d)
        trend.append({
            'date': (today - timedelta(days=i)).strftime('%d/%m'),
            'calories': round(sum(float(l.total_calories or 0) for l in logs), 1),
            'protein': round(sum(float(l.total_protein or 0) for l in logs), 1),
            'carbs': round(sum(float(l.total_carbs or 0) for l in logs), 1),
            'fat': round(sum(float(l.total_fat or 0) for l in logs), 1),
        })

    profile = get_profile()
    calorie_target = profile.daily_calorie_target if profile else 2000
    foods = Food.objects.all().order_by('name')

    context = {
        'selected_date': selected_date_str,
        'day_logs': day_logs,
        'total_cal': round(total_cal, 1),
        'total_pro': round(total_pro, 1),
        'total_car': round(total_car, 1),
        'total_fat': round(total_fat_v, 1),
        'calorie_target': calorie_target or 2000,
        'calorie_pct': min(100, int(total_cal / (calorie_target or 2000) * 100)),
        'trend_json': json.dumps(trend),
        'foods': foods,
        'meal_types': MEAL_TYPES,
        'active': 'nutrition',
        'today': today.isoformat(),
    }
    return render(request, 'app/nutrition.html', context)


@csrf_exempt
@require_POST
def nutrition_log(request):
    data = json.loads(request.body)
    food = get_object_or_404(Food, id=data.get('food_id'))
    servings = float(data.get('servings', 1))
    log = NutritionLog.objects.create(
        food=food,
        date=data.get('date', date.today().isoformat()),
        meal_type=data.get('meal_type', 'Bua sang'),
        servings=servings,
        total_calories=round(float(food.calories or 0) * servings, 2),
        total_protein=round(float(food.protein or 0) * servings, 2),
        total_carbs=round(float(food.carbs or 0) * servings, 2),
        total_fat=round(float(food.fat or 0) * servings, 2),
    )
    return JsonResponse({'id': log.id, 'food': food.name, 'calories': float(log.total_calories or 0)})


@csrf_exempt
@require_POST
def nutrition_delete(request, log_id):
    log = get_object_or_404(NutritionLog, id=log_id)
    log.delete()
    return JsonResponse({'ok': True})


def foods(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    food_list = Food.objects.all().order_by('name')
    if query:
        food_list = food_list.filter(name__icontains=query)
    if category:
        food_list = food_list.filter(category=category)
    categories = Food.objects.values_list('category', flat=True).distinct().order_by('category')
    return render(request, 'app/foods.html', {
        'foods': food_list,
        'query': query,
        'category': category,
        'categories': [c for c in categories if c],
        'active': 'foods',
    })


@require_GET
def foods_search(request):
    q = request.GET.get('q', '')
    food_list = Food.objects.filter(name__icontains=q)[:20] if q else Food.objects.all()[:20]
    return JsonResponse([{
        'id': f.id, 'name': f.name,
        'calories': float(f.calories or 0),
        'protein': float(f.protein or 0),
        'carbs': float(f.carbs or 0),
        'fat': float(f.fat or 0),
        'serving_size': f.serving_size or '',
    } for f in food_list], safe=False)


def profile(request):
    prof = get_profile()
    return render(request, 'app/profile.html', {'profile': prof, 'active': 'profile'})


@csrf_exempt
@require_POST
def profile_save(request):
    data = json.loads(request.body)
    prof = get_profile()
    fields = {
        'name': data.get('name', ''),
        'age': data.get('age') or None,
        'weight': data.get('weight') or None,
        'height': data.get('height') or None,
        'gender': data.get('gender', ''),
        'health_goal': data.get('health_goal', ''),
        'medical_conditions': data.get('medical_conditions', ''),
        'dietary_preferences': data.get('dietary_preferences', ''),
        'activity_level': data.get('activity_level', ''),
        'daily_calorie_target': data.get('daily_calorie_target') or None,
    }
    if prof:
        for k, v in fields.items():
            setattr(prof, k, v)
        prof.save()
    else:
        prof = UserProfile.objects.create(**fields)
    return JsonResponse({'ok': True, 'name': prof.name})
