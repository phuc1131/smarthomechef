# Meal Plan & Chat History - User-Specific Data Fixes

**Ngày:** May 7, 2026  
**Mục đích:** Đảm bảo meal plan history và chat history được lưu vào cơ sở dữ liệu riêng cho mỗi user

## 1. Meal Plan Fixes

### 1.1 Database Model
**Model:** `apps/meal_plans/models.py` (MealPlan)
- ✅ Có field `account = ForeignKey('users.Account', on_delete=models.CASCADE)`
- ✅ Meal plans được lưu với account reference
- ✅ Xóa account → xóa toàn bộ meal plans của user đó (CASCADE)

### 1.2 Views - Meal Plan History
**File:** `app/meal_plan_views.py`

#### BEFORE (Bug: Mỗi user thấy meal plan của tất cả user khác)
```python
# Line 36 - Bug: Không filter by account
plans = MealPlan.objects.filter(date__gte=first_day, date__lt=last_day).select_related('food')
```

#### AFTER (FIX: Mỗi user chỉ thấy meal plan của họ)
```python
# Line 23-36 - Fixed: Lấy current account + filter by account
account = get_current_account(request)
if not account:
    return render(request, 'error.html', {'message': 'Vui lòng đăng nhập'}, status=401)

plans = MealPlan.objects.filter(
    account=account,
    date__gte=first_day, 
    date__lt=last_day
).select_related('food')
```

### 1.3 Views - Meal Plan Deletion (Security Fix)
**File:** `app/meal_plan_views.py` - `meal_plan_delete()` function

#### BEFORE (Security Bug: Ai cũng có thể xóa meal plan của ai nếu biết ID)
```python
# Line 168 - Bug: Không check account ownership
plan = get_object_or_404(MealPlan, id=plan_id)
plan.delete()
```

#### AFTER (FIX: Chỉ owner mới có thể xóa)
```python
# Fixed: Kiểm tra owner + filter by account
account = get_current_account(request)
if not account:
    return JsonResponse({'error': 'Vui lòng đăng nhập'}, status=401)

plan = get_object_or_404(MealPlan, id=plan_id, account=account)
plan.delete()
```

### 1.4 Views - Meal Plan Creation (AI-based)
**File:** `app/meal_plan_views.py` - `meal_plan_add()` function
- ✅ Lấy current account
- ✅ Gọi `MealPlanGeneratorService.generate_meal_plan(account=...)`
- ✅ Service này lưu MealPlan với account reference
- ✅ Meal plans được tạo ra được lưu vào DB:
  ```python
  plan = MealPlan.objects.create(
      account=account,  # ← User-specific
      food=selected_food,
      date=target_date,
      meal_type=meal_vi,
      servings=Decimal(str(servings)),
      notes=f'AI-generated ({analyzed["type"]} plan): {request_text}'
  )
  ```

## 2. Chat History Fixes

### 2.1 Database Models
**Models:** `apps/chat/models.py`
- ✅ `ChatSession`: Có field `account = ForeignKey('users.Account', on_delete=models.CASCADE)`
- ✅ `ChatMessage`: Linked to ChatSession (which has account reference)
- ✅ Xóa account → xóa toàn bộ chat sessions + messages của user đó

### 2.2 Views - Chat Page (Display History)
**File:** `app/chat_views.py` - `chat_page()` function

#### BEFORE (Bug: Mỗi user thấy tất cả chat messages của tất cả user)
```python
# Line 14 - Bug: Không filter by account
messages = ChatMessage.objects.all().order_by('created_at')
```

#### AFTER (FIX: Mỗi user chỉ thấy chat history của họ)
```python
# Lines 24-39 - Fixed: Lấy current account + create session + filter by session
account = get_current_account(request)
if not account:
    return render(request, 'user/chat.html', {...}, status=401)

session = get_chat_session(account)
if session:
    messages = ChatMessage.objects.filter(session=session).order_by('created_at')
else:
    messages = []
```

### 2.3 Views - Chat Send (Create Message with Account)
**File:** `app/chat_views.py` - `chat_send()` function

#### BEFORE (Bug: Messages lưu không có session, không lên được user)
```python
# Line 38 - Bug: ChatMessage created without session
ChatMessage.objects.create(role='user', content=user_text)
```

#### AFTER (FIX: Messages lưu có session → lên được account)
```python
# Lines 49-62 - Fixed: Create message with session
account = get_current_account(request)
if not account:
    return JsonResponse({'error': 'Vui lòng đăng nhập'}, status=401)

session = get_chat_session(account)
if not session:
    return JsonResponse({'error': 'Không thể tạo chat session'}, status=500)

ChatMessage.objects.create(role='user', content=user_text, session=session)
```

#### BEFORE (Bug: AI response lưu không có session)
```python
# Line 69 - Bug: No session reference
msg = ChatMessage.objects.create(role='assistant', content=ai_text)
```

#### AFTER (FIX: AI response lưu có session)
```python
# Line 108 - Fixed: Create message with session
msg = ChatMessage.objects.create(role='assistant', content=ai_text, session=session)
```

#### BEFORE (Bug: AI lấy tất cả messages từ tất cả user)
```python
# Line 54 - Bug: Get all messages, not just user's
for msg in ChatMessage.objects.all().order_by('created_at'):
```

#### AFTER (FIX: AI chỉ lấy messages từ chat session của user)
```python
# Line 100 - Fixed: Filter by session
for msg in ChatMessage.objects.filter(session=session).order_by('created_at'):
```

### 2.4 Views - Chat Clear (Delete History)
**File:** `app/chat_views.py` - `chat_clear()` function

#### BEFORE (Security Bug: Xóa chat sẽ xóa tất cả messages của tất cả user)
```python
# Line 70 - Critical bug: Delete all messages
ChatMessage.objects.all().delete()
```

#### AFTER (FIX: Chỉ xóa user's own messages)
```python
# Lines 116-126 - Fixed: Delete only user's session messages
account = get_current_account(request)
if not account:
    return JsonResponse({'error': 'Vui lòng đăng nhập'}, status=401)

session = get_chat_session(account)
if session:
    ChatMessage.objects.filter(session=session).delete()

return JsonResponse({'ok': True})
```

## 3. Summary of Fixes

### Meal Plan
| Feature | Before | After | Status |
|---------|--------|-------|--------|
| meal_plans view | Tất cả users → tất cả meal plans | Mỗi user → meal plans riêng | ✅ Fixed |
| meal_plan_delete | Ai cũng xóa được nếu biết ID | Chỉ owner có thể xóa | ✅ Fixed |
| meal_plan_add (AI) | N/A - không có | Tạo meal plan với account | ✅ Implemented |
| Database | Meal plans có account FK | ✅ Đã có | ✅ Verified |

### Chat
| Feature | Before | After | Status |
|---------|--------|-------|--------|
| chat_page | Tất cả users → tất cả messages | Mỗi user → messages riêng | ✅ Fixed |
| chat_send | Messages không có session | Messages lưu có session | ✅ Fixed |
| chat_clear | Xóa tất cả messages (all users) | Xóa chỉ user's messages | ✅ Fixed |
| AI history | AI xem tất cả messages | AI xem chỉ user's messages | ✅ Fixed |
| Database | ChatSession có account FK | ✅ Đã có | ✅ Verified |

## 4. Lịch Sử Dữ Liệu

### Meal Plan History
- **Query:** `MealPlan.objects.filter(account=user_account).order_by('-date')`
- **Display:** Calendar view hiển thị meal plans per user
- **Storage:** Database (persistent)
- **Timestamps:** `created_at` field tracks when meal plan was created

### Chat History
- **Query:** `ChatMessage.objects.filter(session__account=user_account).order_by('created_at')`
- **Display:** Chat page hiển thị conversation per user
- **Storage:** Database (persistent)
- **Session:** Consolidates all messages per user in ChatSession
- **Timestamps:** `created_at` field tracks when message was sent

## 5. Security Improvements
✅ Users cannot see other users' meal plans  
✅ Users cannot delete other users' meal plans  
✅ Users cannot see other users' chat history  
✅ Users cannot modify other users' chat messages  
✅ Chat clear only clears user's own messages  

## 6. Testing Checklist
- [ ] User A creates meal plan → User B cannot see it
- [ ] User A deletes meal plan → cannot access User B's meal plans
- [ ] User A sends chat message → message saved with account
- [ ] User A's chat history → does not include User B's messages
- [ ] User A clears chat → only their messages deleted
- [ ] Django migrations needed for future changes

## 7. Notes
- MealPlan model already had `account` field (good!)
- ChatSession model already had `account` field (good!)
- Views were missing account filtering (major privacy/security issue)
- All fixes maintain backward compatibility
- API endpoints now return user-specific data only
