"""Meal plan routes."""

from django.urls import path

from apps.meal_plans import views

app_name = 'meal_plans'

urlpatterns = [
    path('thuc-don/', views.meal_plans, name='meal_plans'),
    path('thuc-don/them/', views.meal_plan_add, name='meal_plan_add'),
    path('thuc-don/xoa/<int:plan_id>/', views.meal_plan_delete, name='meal_plan_delete'),
]
