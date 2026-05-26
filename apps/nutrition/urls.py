"""Nutrition and food routes."""

from django.urls import path

from apps.nutrition import views

app_name = 'nutrition'

urlpatterns = [
    path('theo-doi/', views.nutrition, name='nutrition'),
    path('theo-doi/ghi/', views.nutrition_log, name='nutrition_log'),
    path('theo-doi/xoa/<int:log_id>/', views.nutrition_delete, name='nutrition_delete'),
    path('mon-an/', views.foods, name='foods'),
    path('mon-an/tim-kiem/', views.foods_search, name='foods_search'),
    path('api/recipe/rate/', views.rate_recipe, name='rate_recipe'),
    path('api/recipe/ratings/<int:recipe_id>/', views.get_recipe_ratings, name='get_recipe_ratings'),
    path('api/recipe/rating/<int:recipe_id>/<int:account_id>/', views.get_user_recipe_rating, name='get_user_recipe_rating'),
    path('api/recipe/top/', views.get_top_recipes, name='get_top_recipes'),
]
