"""Chat routes."""

from django.urls import path

from apps.chat import views

app_name = 'chat'

urlpatterns = [
    path('chat/', views.chat_page, name='chat'),
    path('chat/send/', views.chat_send, name='chat_send'),
    path('api/chat/send/', views.chat_send, name='api_chat_send'),
    path('api/chat/clear/', views.chat_clear, name='api_chat_clear'),
]
