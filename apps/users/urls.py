from django.urls import path

from apps.users import views

app_name = 'users'

urlpatterns = [
	path('doi-mat-khau/', views.change_password, name='change_password'),
	path('quen-mat-khau/', views.password_reset, name='password_reset'),
	path('ho-so/', views.profile, name='profile'),
	path('ho-so/luu/', views.profile_save, name='profile_save'),
]
