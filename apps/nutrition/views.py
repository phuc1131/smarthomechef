import json
from datetime import date, timedelta
from urllib.parse import quote
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg, Count, Q

from apps.nutrition.models import Food, Ingredient, NutritionLog, Recipe, RecipeRating
from apps.users.models import Account
from app.utils import get_profile


MEAL_TYPES = [
    ('Bữa sáng', 'Bữa sáng'),
    ('Bữa trưa', 'Bữa trưa'),
    ('Bữa tối', 'Bữa tối'),
    ('Bữa phụ', 'Bữa phụ'),
]


# ===== NUTRITION HELPERS =====

def _nutrition_totals(log):
    servings = float(log.servings or 0)
    food = log.food
    return {
        'calories': round(float((food.calories if food else 0) or 0) * servings, 2),
        'protein': round(float((food.protein if food else 0) or 0) * servings, 2),
        'carbs': round(float((food.carbs if food else 0) or 0) * servings, 2),
        'fat': round(float((food.fat if food else 0) or 0) * servings, 2),
    }


# ===== NUTRITION VIEWS =====

def nutrition(request):
    today = date.today()
    selected_date_str = request.GET.get('date', today.isoformat())
    try:
        date.fromisoformat(selected_date_str)
    except ValueError:
        selected_date_str = today.isoformat()

    nutrition_log_fields = ('id', 'account_id', 'food_id', 'date', 'meal_type', 'servings', 'created_at', 'food__name', 'food__calories', 'food__protein', 'food__carbs', 'food__fat')
    day_logs = NutritionLog.objects.filter(date=selected_date_str).select_related('food').only(*nutrition_log_fields)
    day_totals = [_nutrition_totals(log) for log in day_logs]
    total_cal = sum(item['calories'] for item in day_totals)
    total_pro = sum(item['protein'] for item in day_totals)
    total_car = sum(item['carbs'] for item in day_totals)
    total_fat_v = sum(item['fat'] for item in day_totals)

    trend = []
    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        logs = NutritionLog.objects.filter(date=d).select_related('food').only(*nutrition_log_fields)
        logs_totals = [_nutrition_totals(log) for log in logs]
        trend.append({
            'date': (today - timedelta(days=i)).strftime('%d/%m'),
            'calories': round(sum(item['calories'] for item in logs_totals), 1),
            'protein': round(sum(item['protein'] for item in logs_totals), 1),
            'carbs': round(sum(item['carbs'] for item in logs_totals), 1),
            'fat': round(sum(item['fat'] for item in logs_totals), 1),
        })

    profile = get_profile(request)
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
        'trend_data': trend,
        'foods': foods,
        'meal_types': MEAL_TYPES,
        'active': 'nutrition',
        'today': today.isoformat(),
    }
    return render(request, 'user/nutrition.html', context)


@csrf_exempt
@require_POST
def nutrition_log(request):
    try:
        data = json.loads(request.body)
        food = get_object_or_404(Food, id=data.get('food_id'))
        servings = float(data.get('servings', 1))
        log = NutritionLog.objects.create(
            food=food,
            date=data.get('date', date.today().isoformat()),
            meal_type=data.get('meal_type', 'Bua sang'),
            servings=servings,
        )
        return JsonResponse({'id': log.id, 'food': food.name, 'calories': round(float(food.calories or 0) * servings, 2)})
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': f'Internal error: {exc}'}, status=500)


@csrf_exempt
@require_POST
def nutrition_delete(request, log_id):
    log = get_object_or_404(NutritionLog, id=log_id)
    log.delete()
    return JsonResponse({'ok': True})


# ===== FOOD VIEWS =====

def foods(request):
    query = (request.GET.get('q', '') or '').strip()
    category = (request.GET.get('category', '') or '').strip()
    should_show_results = bool(query or category)

    category_groups = {
        'Sữa các loại': {
            'food_categories': ['Sua Tuoi', 'Sua Hat Sua Dau', 'Sua Dac', 'Bo Sua Pho Mai'],
            'ingredient_keywords': ['sua', 'pho mai', 'yaourt', 'yogurt'],
            'icon': '🥛',
        },
        'Bánh kẹo': {
            'food_categories': ['Banh Mi', 'Banh Bao'],
            'ingredient_keywords': ['banh', 'keo', 'snack', 'cookie', 'cracker', 'chocolate'],
            'icon': '🍪',
        },
        'Thực phẩm ăn liền': {
            'food_categories': ['Mi', 'Mien Hu Tiu Banh Canh', 'Chao', 'Pho Bun'],
            'ingredient_keywords': ['mi ', 'mien', 'hu tieu', 'banh canh', 'chao', 'pho', 'bun', 'nui'],
            'icon': '🍜',
        },
    }

    legacy_to_group = {
        'Sua Tuoi': 'Sữa các loại',
        'Sua Hat Sua Dau': 'Sữa các loại',
        'Sua Dac': 'Sữa các loại',
        'Bo Sua Pho Mai': 'Sữa các loại',
        'Banh Mi': 'Bánh kẹo',
        'Banh Bao': 'Bánh kẹo',
        'Mi': 'Thực phẩm ăn liền',
        'Mien Hu Tiu Banh Canh': 'Thực phẩm ăn liền',
        'Chao': 'Thực phẩm ăn liền',
        'Pho Bun': 'Thực phẩm ăn liền',
    }
    selected_group = category if category in category_groups else legacy_to_group.get(category)

    def ingredient_group_q(group_name):
        q_expr = Q()
        for kw in category_groups[group_name]['ingredient_keywords']:
            q_expr |= Q(name__icontains=kw) | Q(normalized_name__icontains=kw)
        return q_expr

    ingredient_group_queries = {
        group_name: ingredient_group_q(group_name)
        for group_name in category_groups
    }

    def detect_ingredient_group(ingredient_obj):
        name_l = (ingredient_obj.name or '').lower()
        norm_l = (ingredient_obj.normalized_name or '').lower()
        for group_name, cfg in category_groups.items():
            if any(kw in name_l or kw in norm_l for kw in cfg['ingredient_keywords']):
                return group_name
        return 'Nguyên liệu crawl'

    def food_to_display_row(food_obj):
        return {
            'id': food_obj.id,
            'name': food_obj.name,
            'category': food_obj.category.name if food_obj.category else '',
            'calories': float(food_obj.calories or 0),
            'protein': float(food_obj.protein or 0),
            'carbs': float(food_obj.carbs or 0),
            'fat': float(food_obj.fat or 0),
            'description': food_obj.description or '',
            'is_vegetarian': bool(food_obj.is_vegetarian),
            'is_diabetes_friendly': bool(food_obj.is_diabetes_friendly),
            'is_weight_loss_friendly': bool(food_obj.is_weight_loss_friendly),
            'serving_size': '',
            'rating_avg': None,
            'rating_count': 0,
        }

    def ingredient_to_display_row(ingredient_obj, display_category):
        nutrition = getattr(ingredient_obj, 'nutrition', None)
        return {
            'id': -int(ingredient_obj.id),
            'name': ingredient_obj.name,
            'category': display_category,
            'calories': float(getattr(nutrition, 'calories', 0) or 0),
            'protein': float(getattr(nutrition, 'protein', 0) or 0),
            'carbs': float(getattr(nutrition, 'carbs', 0) or 0),
            'fat': float(getattr(nutrition, 'fat', 0) or 0),
            'description': '',
            'is_vegetarian': False,
            'is_diabetes_friendly': False,
            'is_weight_loss_friendly': False,
            'serving_size': '',
            'rating_avg': None,
            'rating_count': 0,
        }

    foods_qs = Food.objects.select_related('category').all()
    group_union_q = Q()
    for group_q in ingredient_group_queries.values():
        group_union_q |= group_q
    ingredients_qs = Ingredient.objects.select_related('nutrition').filter(is_deleted=False).filter(group_union_q)

    if query:
        foods_qs = foods_qs.filter(name__icontains=query)
        ingredients_qs = ingredients_qs.filter(Q(name__icontains=query) | Q(normalized_name__icontains=query))

    if selected_group:
        foods_qs = foods_qs.filter(category__name__in=category_groups[selected_group]['food_categories'])
        ingredients_qs = ingredients_qs.filter(ingredient_group_queries[selected_group])
    elif category:
        foods_qs = foods_qs.filter(category__name=category)
        ingredients_qs = ingredients_qs.none()

    food_rows = [food_to_display_row(food) for food in foods_qs.order_by('name')]
    ingredient_rows = [
        ingredient_to_display_row(ing, detect_ingredient_group(ing))
        for ing in ingredients_qs.order_by('name')
    ]
    combined_rows = sorted(food_rows + ingredient_rows, key=lambda item: (item.get('name') or '').lower())
    if not should_show_results:
        combined_rows = []

    base_categories = list(Food.objects.values_list('category__name', flat=True).distinct().order_by('category__name'))
    categories = [c for c in base_categories if c]
    for group_name in category_groups.keys():
        if group_name not in categories:
            categories.append(group_name)

    # Keep UI structure unchanged, but disable top featured cards so data only appears below search.
    featured_categories = []
    search_notice = '' if should_show_results else 'Nhập từ khóa hoặc chọn danh mục để hiển thị dữ liệu.'

    return render(request, 'user/foods.html', {
        'foods': combined_rows,
        'query': query,
        'category': category,
        'categories': categories,
        'featured_categories': featured_categories,
        'search_notice': search_notice,
        'active': 'foods',
    })


@require_GET
def foods_search(request):
    try:
        q = request.GET.get('q', '')
        food_list = Food.objects.filter(name__icontains=q)[:20] if q else Food.objects.all()[:20]
        return JsonResponse([{
            'id': f.id, 'name': f.name,
            'calories': float(f.calories or 0),
            'protein': float(f.protein or 0),
            'carbs': float(f.carbs or 0),
            'fat': float(f.fat or 0),
            'serving_size': getattr(f, 'serving_size', '') or '',
        } for f in food_list], safe=False)
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': f'Internal error: {exc}', 'items': []}, status=500)


# ===== RECIPE RATING APIs =====

@require_POST
@csrf_exempt
def rate_recipe(request):
    """
    API endpoint để user đánh giá công thức.
    
    Request body:
    {
        "recipe_id": int,
        "account_id": int,
        "rating": int (1-5),
        "comment": str (optional)
    }
    """
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON'
            }, status=400)
        
        recipe_id = data.get('recipe_id')
        account_id = data.get('account_id')
        rating = data.get('rating')
        comment = data.get('comment', '')
        
        # Validate
        if not recipe_id or not account_id or not rating:
            return JsonResponse({
                'success': False,
                'message': 'Missing required fields: recipe_id, account_id, rating'
            }, status=400)
        
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return JsonResponse({
                'success': False,
                'message': 'Rating must be an integer between 1 and 5'
            }, status=400)
        
        # Get recipe and account
        try:
            recipe = Recipe.objects.get(pk=recipe_id)
            account = Account.objects.get(pk=account_id)
        except Recipe.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'Recipe with ID {recipe_id} not found'
            }, status=404)
        except Account.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'Account with ID {account_id} not found'
            }, status=404)
        
        # Create or update rating
        recipe_rating, created = RecipeRating.objects.update_or_create(
            recipe=recipe,
            account=account,
            defaults={
                'rating': rating,
                'comment': comment.strip() if comment else ''
            }
        )
        
        rating_summary = recipe.ratings.aggregate(
            avg_rating=Avg('rating'),
            total_ratings=Count('id')
        )
        avg_rating = float(rating_summary['avg_rating'] or 0)
        total_ratings = rating_summary['total_ratings'] or 0

        return JsonResponse({
            'success': True,
            'message': f'Recipe {"rated" if not created else "re-rated"} successfully',
            'recipe_rating': {
                'id': recipe_rating.id,
                'recipe_id': recipe_rating.recipe_id,
                'rating': recipe_rating.rating,
                'comment': recipe_rating.comment,
                'created_at': recipe_rating.created_at.isoformat(),
                'updated_at': recipe_rating.updated_at.isoformat()
            },
            'recipe_avg_rating': avg_rating,
            'total_ratings': total_ratings
        })
    except Exception as exc:
        return JsonResponse({
            'success': False,
            'message': f'Internal error: {exc}'
        }, status=500)


@require_GET
def get_recipe_ratings(request, recipe_id):
    """Lấy tất cả ratings cho một công thức."""
    try:
        recipe = Recipe.objects.get(pk=recipe_id)
    except Recipe.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': f'Recipe with ID {recipe_id} not found'
        }, status=404)
    
    ratings = recipe.ratings.all().select_related('account').order_by('-created_at')
    rating_summary = ratings.aggregate(
        avg_rating=Avg('rating'),
        total_ratings=Count('id')
    )
    avg_rating = float(rating_summary['avg_rating'] or 0)
    total_ratings = rating_summary['total_ratings'] or 0

    return JsonResponse({
        'success': True,
        'recipe': {
            'id': recipe.id,
            'name': recipe.title,
            'avg_rating': avg_rating,
            'total_ratings': total_ratings,
            'ratings': [
                {
                    'id': r.id,
                    'rating': r.rating,
                    'comment': r.comment,
                    'account_id': r.account_id,
                    'created_at': r.created_at.isoformat(),
                    'updated_at': r.updated_at.isoformat()
                }
                for r in ratings
            ]
        },
        'message': f'Found {ratings.count()} ratings'
    })


@require_GET
def get_user_recipe_rating(request, recipe_id, account_id):
    """Lấy rating của một user cho một công thức."""
    try:
        recipe = Recipe.objects.get(pk=recipe_id)
        rating = recipe.ratings.filter(account_id=account_id).first()
        
        if rating:
            return JsonResponse({
                'success': True,
                'rating': {
                    'id': rating.id,
                    'rating': rating.rating,
                    'comment': rating.comment,
                    'created_at': rating.created_at.isoformat(),
                    'updated_at': rating.updated_at.isoformat()
                },
                'message': 'User rating found'
            })
        else:
            return JsonResponse({
                'success': True,
                'rating': None,
                'message': 'No rating found for this user'
            })
    
    except Recipe.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': f'Recipe with ID {recipe_id} not found'
        }, status=404)


@require_GET
def get_top_recipes(request):
    """Lấy danh sách công thức được đánh giá cao nhất."""
    limit = int(request.GET.get('limit', 10))
    min_ratings = int(request.GET.get('min_ratings', 0))
    
    query = Recipe.objects.annotate(
        avg_rating=Avg('ratings__rating'),
        total_ratings=Count('ratings')
    )

    if min_ratings > 0:
        query = query.filter(total_ratings__gte=min_ratings)
    
    recipes = query.order_by('-avg_rating', '-total_ratings')[:limit]
    
    return JsonResponse({
        'success': True,
        'recipes': [
            {
                'id': r.id,
                'name': r.title,
                'avg_rating': float(r.avg_rating or 0),
                'total_ratings': r.total_ratings or 0,
            }
            for r in recipes
        ],
        'message': f'Found {len(recipes)} recipes'
    })
