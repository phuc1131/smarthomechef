# Wrapper layer for backward compatibility - all implementation moved to apps.nutrition.views
from apps.nutrition.views import (
    rate_recipe, get_recipe_ratings, get_user_recipe_rating, get_top_recipes
)

__all__ = ['rate_recipe', 'get_recipe_ratings', 'get_user_recipe_rating', 'get_top_recipes']


@require_POST
@csrf_exempt
def rate_recipe(request):
    """
    API endpoint để user đánh giá công thức.
    
    Request body:
    {
        "recipe_id": int,
        "account_id": int,  # hoặc có thể lấy từ request.user
        "rating": int (1-5),
        "comment": str (optional)
    }
    
    Response:
    {
        "success": bool,
        "message": str,
        "recipe_rating": {
            "id": int,
            "recipe_id": int,
            "rating": int,
            "comment": str,
            "created_at": str
        },
        "recipe_avg_rating": float,
        "total_ratings": int
    }
    """
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


@require_GET
def get_recipe_ratings(request, recipe_id):
    """
    Lấy tất cả ratings cho một công thức.
    
    Response:
    {
        "success": bool,
        "recipe": {
            "id": int,
            "name": str,
            "avg_rating": float,
            "total_ratings": int,
            "ratings": [
                {
                    "id": int,
                    "rating": int,
                    "comment": str,
                    "account_name": str,
                    "created_at": str
                }
            ]
        },
        "message": str
    }
    """
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
    """
    Lấy rating của một user cho một công thức.
    
    Response:
    {
        "success": bool,
        "rating": {
            "id": int,
            "rating": int,
            "comment": str,
            "created_at": str,
            "updated_at": str
        } or null,
        "message": str
    }
    """
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
    """
    Lấy danh sách công thức được đánh giá cao nhất.
    
    Query params:
    - limit: int (default 10)
    - min_ratings: int (default 0) - số lượng ratings tối thiểu
    
    Response:
    {
        "success": bool,
        "recipes": [
            {
                "id": int,
                "name": str,
                "avg_rating": float,
                "total_ratings": int
            }
        ],
        "message": str
    }
    """
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
