from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('chat/', views.chat_page, name='chat'),
    path('thuc-don/', views.meal_plans, name='meal_plans'),
    path('theo-doi/', views.nutrition, name='nutrition'),
    path('mon-an/', views.foods, name='foods'),
    path('ho-so/', views.profile, name='profile'),

    path('api/chat/send/', views.chat_send, name='chat_send'),
    path('api/chat/clear/', views.chat_clear, name='chat_clear'),
    path('api/nutrition/log/', views.nutrition_log, name='nutrition_log'),
    path('api/nutrition/delete/<int:log_id>/', views.nutrition_delete, name='nutrition_delete'),
    path('api/meal-plan/add/', views.meal_plan_add, name='meal_plan_add'),
    path('api/meal-plan/delete/<int:plan_id>/', views.meal_plan_delete, name='meal_plan_delete'),
    path('api/profile/save/', views.profile_save, name='profile_save'),
    path('api/foods/search/', views.foods_search, name='foods_search'),
]
