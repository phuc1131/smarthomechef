# Code Style Guide

## Naming Conventions

### Python
- **Variables**: `snake_case` - `user_profile`, `chat_session`
- **Functions**: `snake_case` - `get_nutrition_data()`
- **Classes**: `PascalCase` - `UserProfile`, `ChatService`
- **Constants**: `UPPER_SNAKE_CASE` - `MAX_MESSAGE_LENGTH`, `GEMINI_API_KEY`

### Django Models
```python
class UserProfile(models.Model):
    """Mô tả model"""
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profiles'  # Đặt tên table rõ ràng

    def __str__(self):
        return self.name
```

### Database Naming
- **Table names**: `lowercase_snake_case` - `user_profiles`, `chat_messages`
- **Foreign keys**: `fieldname_id` - `account_id`, `session_id`
- **Always use** `db_table` và `db_column` để rõ ràng

## Code Organization

### Views
```python
# app/views.py hoặc app/views/__init__.py
# Tách theo chức năng:
# - Auth views: login, register, logout
# - Dashboard views: dashboard, profile  
# - Chat views: chat, chat_send
# - Nutrition views: foods, nutrition_log
# - Admin views: admin_panel, data_manager
```

### Services
```python
# app/services/name_service.py
# Mỗi service có responsibility riêng
# - ai_service.py: Gemini API calls
# - cache_service.py: Response caching
# - nlp_service.py: Intent classification
```

### Imports
```python
# Thứ tự imports:
# 1. Python standard library
import os
import json
from datetime import datetime

# 2. Third-party
from django.shortcuts import render
from django.db.models import Q

# 3. Local imports
from .models import UserProfile
from .services.ai_service import call_gemini
```

## Documentation

### Docstrings (Vietnamese)
```python
def classify_intent(message_text):
    """
    Phân loại ý định của tin nhắn người dùng.
    
    Args:
        message_text (str): Nội dung tin nhắn
    
    Returns:
        dict: {'intent': 'recommendation', 'confidence': 0.85}
    
    Raises:
        ValueError: Nếu message_text rỗng
    """
    pass
```

### Comments
```python
# Giải thích logic phức tạp, không comment trên từng dòng
# GHI NHỚ QUAN TRỌNG: Các điểm cần chú ý
# TODO: Cải thiện sau
# FIXME: Bug cần sửa
```

## File Organization

```
apps/
├── users/
├── chat/
├── nutrition/
├── meal_plans/
├── admin_panel/
└── core_models/

app/
├── views.py               # Legacy forwarders while migration completes
├── services/              # Shared business logic
├── templates/             # HTML templates
├── static/                # CSS, JS, images
└── management/commands/   # Maintenance commands
```

## Testing

### Test File Naming
- `test_models.py` - Model tests
- `test_views.py` - View tests
- `test_services.py` - Service tests

### Test Structure
```python
import pytest
from django.test import Client
from apps.users.models import UserProfile

class TestUserProfile:
    """Model tests"""
    
    def test_create_user_profile(self):
        """Kiểm tra tạo profile"""
        profile = UserProfile.objects.create(name="Test User")
        assert profile.name == "Test User"
    
    @pytest.mark.django_db
    def test_user_profile_str(self):
        """Kiểm tra __str__"""
        profile = UserProfile.objects.create(name="Test")
        assert str(profile) == "Test"
```

## Code Quality Tools

### Linting
```bash
# PyLint
pylint app/

# Flake8
flake8 app/
```

### Formatting
```bash
# Black (auto format)
black app/ --line-length=120

# isort (organize imports)
isort app/
```

### Type Checking
```bash
# Optional - mypy
mypy app/
```

## Git Commit Messages

```
[FEATURE] Add chat intent classification
[BUGFIX] Fix nutrition calculation rounding
[REFACTOR] Extract AI service logic
[DOCS] Update README
[TEST] Add unit tests for models
[CHORE] Update dependencies

Format: [TYPE] Mô tả (Tiếng Việt hoặc Tiếng Anh)
```
