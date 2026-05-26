#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from apps.chat.models import ChatMessage, ChatSession, MessageIntent, Intent

# Kiểm tra guest account
from app.utils import get_or_create_guest_account
from apps.chat.views import get_chat_session
guest_account = get_or_create_guest_account()
print(f'Guest Account: {guest_account.username} (ID: {guest_account.id})')

# Kiểm tra chat session
chat_session = get_chat_session(guest_account)
print(f'Chat Session: {chat_session.title} (ID: {chat_session.id})')

# Đếm messages
messages = ChatMessage.objects.filter(session=chat_session)
print(f'\nTổng tin nhắn trong session: {messages.count()}')

if messages.count() > 0:
    print('\n=== CHI TIẾT TIN NHẮN ===')
    for msg in messages.order_by('created_at'):
        # Tìm intent của tin nhắn này
        msg_intent = MessageIntent.objects.filter(message=msg).select_related('intent').first()
        intent_name = msg_intent.intent.name if msg_intent else 'unclassified'
        confidence = msg_intent.confidence if msg_intent else 0
        
        print(f'\n[{msg.role.upper()}]:')
        print(f'  Nội dung: {msg.content[:100]}...' if len(msg.content) > 100 else f'  Nội dung: {msg.content}')
        print(f'  Intent: {intent_name} ({confidence:.0%})')
        print(f'  Lúc: {msg.created_at}')
else:
    print('\n[WARNING] Chưa có tin nhắn nào. Gửi tin nhắn lên chat Page!')

print('\n=== DANH SÁCH INTENT TRONG HỆ THỐNG ===')
for intent in Intent.objects.all():
    count = MessageIntent.objects.filter(intent=intent).count()
    print(f'  - {intent.name}: {count} tin nhắn')
