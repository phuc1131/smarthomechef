from django.urls import path

from app.features.user_panel import views as user_views
from apps.users import views as account_views

urlpatterns = [
    path('', user_views.dashboard, name='dashboard'),
    path('dang-nhap/', user_views.login_page, name='login'),
    path('dang-ky/', user_views.register_page, name='register'),
    path('quen-mat-khau/', account_views.password_reset, name='password_reset'),
    path('auth/login/', user_views.auth_login, name='auth_login'),
    path('auth/register/', user_views.auth_register, name='auth_register'),
    path('auth/logout/', user_views.auth_logout, name='auth_logout'),
    path('chat/', user_views.chat_page, name='chat'),
    path('chat/send/', user_views.chat_send, name='chat_send'),
    path('api/chat/send/', user_views.chat_send, name='api_chat_send'),
    path('api/chat/clear/', user_views.chat_clear, name='api_chat_clear'),
    path('thuc-don/', user_views.meal_plans, name='meal_plans'),
    path('thuc-don/them/', user_views.meal_plan_add, name='meal_plan_add'),
    path('thuc-don/xoa/<int:plan_id>/', user_views.meal_plan_delete, name='meal_plan_delete'),
    path('theo-doi/', user_views.nutrition, name='nutrition'),
    path('theo-doi/ghi/', user_views.nutrition_log, name='nutrition_log'),
    path('theo-doi/xoa/<int:log_id>/', user_views.nutrition_delete, name='nutrition_delete'),
    path('mon-an/', user_views.foods, name='foods'),
    path('mon-an/tim-kiem/', user_views.foods_search, name='foods_search'),
    path('ho-so/', user_views.profile, name='profile'),
    path('ho-so/luu/', user_views.profile_save, name='profile_save'),
    path('doi-mat-khau/', account_views.change_password, name='change_password'),

    # API endpoints used by frontend JavaScript
    path('api/profile/save/', account_views.profile_save, name='api_profile_save'),
    path('api/accounts/delete/', account_views.account_delete, name='api_account_delete'),
    path('api/accounts/list/', account_views.accounts_list, name='api_accounts_list'),
    path('api/accounts/<int:account_id>/', account_views.account_detail, name='api_account_detail'),
]
