# Usecase - Noi Tro AI: Ứng Dụng Hỗ Trợ Dinh Dưỡng & Lập Kế Hoạch Ăn Uống

**Ngày cập nhật:** May 7, 2026  
**Phiên bản:** 2.0 (Smart Home Chef - AI Agent) - Enhanced with Detailed Actors & Flows  
**Mục đích:** Hệ thống khuyến cáo dinh dưỡng và lập kế hoạch bữa ăn thông minh.  
**Scope:** Chỉ hỗ trợ thông tin & khuyến cáo (không có mua sắm/đặt hàng).

---

## 0. ACTORS DETAIL - CHI TIẾT TÁC NHÂN & QUYỀN HẠN

### A. Primary Actors (Tác Nhân Chính)

#### 1. **Guest (Khách Truy Cập)**
```
Mô tả: Người dùng chưa đăng nhập
Trạng thái: Không xác thực
Quyền hạn:
  ✓ Xem danh sách thực phẩm (Food Browse)
  ✓ Tìm kiếm thực phẩm (Food Search - DB only)
  ✓ Xem chi tiết thực phẩm (Food Detail)
  ✓ Đăng ký tài khoản (UC-AUTH-001)
  ✓ Đăng nhập (UC-AUTH-002)
  ✓ Gửi tin nhắn chat (UC-CHAT-001) - optional
  ✗ Ghi nhận dinh dưỡng
  ✗ Lập kế hoạch bữa ăn
  ✗ Xem hồ sơ cá nhân
Workflow:
  Guest → Browse Foods → Decide → Register → Login → Become User
```

#### 2. **User (Người Dùng Thường)**
```
Mô tả: Người dùng đã đăng nhập, có tài khoản cá nhân
Trạng thái: Xác thực
Thuộc tính:
  - account_id: ID tài khoản duy nhất
  - username: Tên đăng nhập
  - email: Email
  - profile: UserProfile (age, weight, health_goals, constraints)
  - preference: PersonalizationData (AI learning từ behavior)
  - active_session: ChatSession
Quyền hạn:
  ✓ Tất cả quyền của Guest
  ✓ Ghi nhận dinh dưỡng (UC-NUTRITION-LOG-001)
  ✓ Xem nhật ký ăn uống (UC-NUTRITION-LOG-002)
  ✓ Xem dashboard cá nhân (UC-DASHBOARD-001)
  ✓ Lập kế hoạch bữa ăn (UC-MEAL-PLAN-001/002/003/004)
  ✓ Xem & chỉnh sửa hồ sơ (UC-PROFILE-001/002)
  ✓ Gửi tin nhắn AI chat (UC-CHAT-001)
  ✓ Xem lịch sử chat (UC-CHAT-002)
  ✓ Xóa bản ghi cá nhân của mình
  ✗ Truy cập admin panel
  ✗ Xóa/sửa dữ liệu của user khác
Workflow:
  User Login → View Dashboard → Log Nutrition → Plan Meals → Chat AI → Receive Recommendations
Sessions:
  - Duration: 24 giờ (default)
  - Storage: request.session['user_id']
  - Timeout: 24 giờ inactivity
```

#### 3. **Admin (Quản Trị Viên)**
```
Mô tả: Quản trị viên hệ thống
Trạng thái: Xác thực + role='admin'
Thuộc tính:
  - account_id: ID tài khoản
  - username: Tên admin
  - role: 'admin'
  - permissions: Full system access
Quyền hạn:
  ✓ Tất cả quyền của User
  ✓ CRUD tất cả models (Food, Account, Recipe, ...)
  ✓ Xem thống kê hệ thống (UC-ADMIN-003)
  ✓ Quản lý users (deactivate, ban, view details)
  ✓ Backup/restore data (UC-DATA-CONSOLIDATE-001)
  ✓ Xóa dữ liệu trùng lặp (UC-ADMIN-004)
  ✓ Seed data / migrations
  ✓ Xem system logs
Workflow:
  Admin Login → Access /admin-panel/ → View Dashboard → CRUD Data → Export/Import
```

### B. Secondary Actors (Tác Nhân Hỗ Trợ/Hệ Thống)

#### 1. **Gemini API (Google)**
```
Mô tả: AI Assistant for meal planning & nutrition advice
Endpoint: https://generativelanguage.googleapis.com/v1beta/models/
Models: gemini-1.5-flash, gemini-1.5-pro
Quyền hạn:
  ✓ Generate meal plans
  ✓ Answer nutrition questions
  ✓ Create recipes
  ✓ Provide health advice
  ✓ Generate shopping lists
  ✗ Access to real-time data
  ✗ User personal health records (only summary provided)
Rate Limit: 10 requests/minute (free tier), $10/million tokens (paid)
Fallback: Rule-based responses when API fails/quota exceeded
```

#### 2. **Spoonacular API**
```
Mô tả: Food nutrition database API
Endpoint: https://api.spoonacular.com/
Quyền hạn:
  ✓ Search foods by name
  ✓ Get nutrition details
  ✓ Ingredient information
  ✓ Recipe search (premium)
  ✗ Modify food data
  ✗ User data access
Rate Limit: 150 calls/day (free tier), $3.99/month (unlimited)
Timeout: 5 seconds
Fallback: Use local Food database
```

#### 3. **Database (PostgreSQL/SQLite)**
```
Mô tả: Persistent data storage
Role: Central repository for all user & application data
Quyền hạn:
  ✓ CRUD operations via Django ORM
  ✓ Complex queries with JOIN, GROUP BY
  ✓ Transaction support
  ✗ Direct SQL access (restricted)
  ✗ Schema modifications (only via migrations)
Capacity: 
  - SQLite: ~10K concurrent, up to 1GB
  - PostgreSQL: Unlimited concurrent, TB+ scale
```

#### 4. **System Scheduler (Cron/APScheduler)**
```
Mô tả: Tự động chạy các công việc định kỳ
Jobs:
  1. Daily digest: Send nutrition summary email (every 6pm)
  2. Chat cache cleanup: Delete entries > 30 days (weekly)
  3. Orphan record cleanup: Remove dangling FK records (daily)
  4. Backups: Database backup (daily at 2am)
  5. Analytics: Update system metrics (hourly)
Quyền hạn:
  ✓ Read all tables
  ✓ Update aggregate tables
  ✓ Delete old records
  ✗ Modify user data directly
```

---

## 1. CRITICAL ISSUES - CÁC VẤN ĐỀ NGUY HIỂM

### 🔴 P0 - MUST FIX IMMEDIATELY (5/7/2026)

#### Issue #1: Meal Plan Add - Account Auth Missing
```
Severity: CRITICAL
Status: BROKEN ❌
Endpoint: POST /api/meal-plan/add/
Location: app/features/user_panel/views.py:802-815

Problem:
  account = get_current_account(request)  # Can be None
  MealPlan.objects.create(account=account, ...)  # account=NULL
  
Impact:
  - User tạo meal plan → account=NULL trong DB
  - meal_plans view filters: filter(account=user_account)
  - NULL ≠ user_account → Meal plan INVISIBLE to user
  - User không thấy được dữ liệu mình vừa tạo

Reproduction:
  1. Go to /thuc-don/
  2. Click "Thêm thực đơn"
  3. Select food, date, servings
  4. Click "Thêm vào thực đơn"
  5. ❌ Không thấy meal plan hiển thị trên calendar

Fix:
  Add auth check BEFORE create:
  ```python
  account = get_current_account(request)
  if not account:
    return JsonResponse({'error': 'Vui lòng đăng nhập'}, status=401)
  
  plan = MealPlan.objects.create(account=account, ...)
  ```
```

#### Issue #2: Nutrition Delete - No Account Verification
```
Severity: CRITICAL  
Status: SECURITY BREACH ❌
Endpoint: DELETE /api/nutrition/delete/{log_id}/
Location: app/features/user_panel/views.py:910

Problem:
  get_object_or_404(NutritionLog, id=log_id)
  # Missing account check!
  
Impact:
  - User A can delete User B's nutrition logs
  - Data loss vulnerability
  - No audit trail of who deleted what

Reproduction:
  1. User A logged in, has nutrition log ID=5
  2. User B curl: DELETE /api/nutrition/delete/5/
  3. ❌ User A's data deleted by User B

Fix:
  Add account filter:
  ```python
  account = get_current_account(request)
  log = get_object_or_404(NutritionLog, id=log_id, account=account)
  log.delete()
  ```
```

#### Issue #3: Nutrition Log - Allows NULL Account
```
Severity: CRITICAL
Status: BROKEN ❌
Endpoint: POST /api/nutrition/log/
Location: app/features/user_panel/views.py:890

Problem:
  account = get_current_account(request)  # Can be None
  NutritionLog.objects.create(account=account, ...)  # account=NULL

Impact:
  - Same as meal plan: logs not visible after creation
  - User's nutrition tracking lost

Fix:
  Add null check:
  ```python
  account = get_current_account(request)
  if not account:
    return JsonResponse({'error': 'Vui lòng đăng nhập'}, status=401)
  ```
```

#### Issue #4: Profile Save - No Account Check
```
Severity: CRITICAL
Status: BROKEN ❌
Endpoint: POST /api/profile/save/
Location: app/features/user_panel/views.py:1322

Problem:
  account = get_current_account(request)  # Can be None
  prof = get_profile(account)  # profile_obj could be None
  
Impact:
  - Guest can't save profile
  - New users can't set health goals
  - Recommendations fail without profile

Fix:
  Add checks:
  ```python
  account = get_current_account(request)
  if not account:
    return JsonResponse({'error': 'Vui lòng đăng nhập'}, status=401)
  
  if not account.is_active:
    return JsonResponse({'error': 'Tài khoản đã bị khóa'}, status=403)
  ```
```

### 🟠 P1 - SHOULD FIX THIS WEEK

#### Issue #5: Food Search - No API Fallback
```
Severity: HIGH
Status: NOT IMPLEMENTED ❌
Feature: Food search with Spoonacular fallback
Location: app/features/user_panel/views.py:980

Problem:
  foods_search() only queries local DB
  No Spoonacular API fallback when results empty
  
Impact:
  - New users with empty Food DB can't find foods
  - Limited to 5000 foods in DB (seed data limit)
  - User experience: "Không tìm thấy" instead of exploring API

Current Behavior:
  Query: "salmon" → No results in DB → Return []

Expected Behavior:
  Query: "salmon" → No results in DB → Call Spoonacular → Return API results

Fix:
  ```python
  def foods_search(request):
    q = request.GET.get('q', '').strip()
    foods = Food.objects.filter(name__icontains=q)[:20]
    
    if not foods:
      # Fallback to Spoonacular API
      from app.services.external_apis import fetch_spoonacular_food
      foods = fetch_spoonacular_food(q, limit=10)
    
    return JsonResponse([serialize_food(f) for f in foods])
  ```
```

#### Issue #6: Chat Endpoint - Allows GET Requests
```
Severity: MEDIUM
Status: WRONG METHOD ❌
Endpoint: POST /api/chat/send/
Location: app/features/user_panel/views.py:612

Problem:
  @csrf_exempt
  @require_POST  # ← Missing!
  def chat_send(request):
  
Impact:
  - Anyone can GET /api/chat/send/?message=...
  - CSRF not enforced (only for POST/PUT/DELETE)
  - Parameter in URL = logged in browser history

Fix:
  Add decorator:
  ```python
  @csrf_exempt
  @require_POST  # Add this
  def chat_send(request):
  ```
```

#### Issue #7: Recipe Generation - No Input Validation
```
Severity: MEDIUM
Status: ALLOWS GARBAGE ⚠️
Endpoint: POST /api/ai/generate-recipe/
Location: app/features/user_panel/views.py:1093

Problem:
  if not recipe_name or not ingredients:
    return error
  # But no max length check, no ingredient count limit

Impact:
  - User sends 1000+ ingredient list → Gemini quota wasted
  - Empty strings sneak through normalize()

Fix:
  ```python
  recipe_name = data.get('recipe_name', '').strip()
  ingredients = data.get('ingredients', [])
  
  if len(recipe_name) < 3 or len(recipe_name) > 100:
    return error
  
  if len(ingredients) == 0 or len(ingredients) > 50:
    return error
  
  # Validate each ingredient
  for ing in ingredients:
    if not isinstance(ing, str) or len(ing) > 50:
      return error
  ```
```

#### Issue #8: Shopping List - No Date Validation
```
Severity: MEDIUM
Status: ACCEPTS INVALID DATES ⚠️
Endpoint: POST /api/ai/generate-shopping-list/
Location: app/features/user_panel/views.py:1203

Problem:
  data_start = data.get('date_start')
  data_end = data.get('date_end')
  # No check: date_start <= date_end

Impact:
  - User sends date_start > date_end
  - Query returns empty, wastes API call

Fix:
  ```python
  if date_start and date_end:
    if date_start > date_end:
      return JsonResponse({
        'success': False,
        'error': 'Ngày bắt đầu phải <= ngày kết thúc'
      }, status=400)
  ```
```

#### Issue #9: Chat Cache - No TTL/Cleanup
```
Severity: MEDIUM
Status: DB BLOAT RISK ⚠️
Model: ChatResponseCache
Location: apps/chat/models.py

Problem:
  Cache entries never deleted
  Database grows indefinitely
  Queries slow down over time
  
Impact:
  - After 1 year: ~365,000 cache entries
  - SQL queries on cache table slow down
  - Database size grows 10-100 MB/year

Fix:
  Add cleanup job:
  ```python
  # In management/commands/cleanup_old_cache.py
  from datetime import timedelta
  from django.utils import timezone
  
  cutoff = timezone.now() - timedelta(days=30)
  ChatResponseCache.objects.filter(created_at__lt=cutoff).delete()
  
  # Run daily via cron/APScheduler
  schedule.every().day.at("02:00").do(cleanup_old_cache)
  ```
```

### 🟡 P2 - NICE TO FIX (Lower Priority)

#### Issue #10: Auth Session - No Timeout
```
Severity: MEDIUM
Status: WEAK SECURITY ⚠️
Location: apps/users/views.py:_set_auth_session()

Problem:
  request.session['user_id'] = account.id
  # No session.set_expiry() call
  # Uses Django default: 2 weeks
  
Impact:
  - Long-lived sessions on shared computers
  - User forgets to logout → session stays active for 2 weeks

Fix:
  ```python
  from datetime import timedelta
  
  request.session['user_id'] = account.id
  request.session.set_expiry(timedelta(hours=24))  # 24-hour timeout
  ```
```

#### Issue #11: Intent Patterns - Empty at Startup
```
Severity: MEDIUM
Status: LOW ACCURACY AT START ⚠️
Location: apps/chat/models.py Intent/Pattern

Problem:
  Intent classification needs pattern samples
  First-time users have no chat history
  No pre-seeded patterns → intent detection fails

Impact:
  - New user: chat "tôi muốn giảm cân"
  - System: "Could not classify intent" (low accuracy)
  - Response: Generic answer instead of specialized

Fix:
  - Pre-seed Intent/Pattern tables on DB init
  - Add 50-100 common health/nutrition patterns
  - See tools/seeding/seed_data_consolidated.py
```

#### Issue #12: Meal Plan NULL Records Invisible
```
Severity: LOW
Status: DATA LOSS ⚠️
Location: Database meal_plans table

Problem:
  Old meal plans with account=NULL exist in DB
  meal_plans view: filter(account=current_user)
  NULL ≠ user_id → Records invisible

Impact:
  - If Issue #1 was deployed early: ~5-100 lost records
  - No way for user to recover them
  - Admin must manually assign or delete

Fix:
  Option A: Migration to assign NULL plans to guest account
  Option B: Delete NULL plans (data loss is acceptable)
  Option C: Keep but display in admin audit log
```

---

---

## 2. DETAILED PROCESSING FLOWS & OPERATIONS

### A. AUTHENTICATION FLOWS

#### Flow: UC-AUTH-001 - Đăng Ký Tài Khoản (Registration)

```
┌─ User (Guest)
│
├─→ [1] Click "Đăng Ký" button
│   └─ GET /dang-ky/ → Render register.html
│
├─→ [2] Fill Form & Submit
│   └─ POST /auth/register/
│       ├─ Data: { username, password }
│       ├─ Validation:
│       │  ├─ len(username) >= 3
│       │  ├─ len(password) >= 8
│       │  └─ NOT Account.objects.filter(username=username).exists()
│       │
│       ├─ If validation fails:
│       │  └─ Return 400: { error: "..." }
│       │
│       └─ If validation pass:
│           ├─ [3] Hash password: password_hash = make_password(password)
│           ├─ [4] Create Account:
│           │   └─ Account(
│           │       username=username,
│           │       email=f"{username.lower()}@local.user",
│           │       password_hash=password_hash,
│           │       role='user',
│           │       is_active=True
│           │     ).save()
│           │
│           ├─ [5] Create UserProfile:
│           │   └─ UserProfile(account=account).save()
│           │
│           ├─ [6] Set Session:
│           │   ├─ request.session['user_id'] = account.id
│           │   ├─ request.session['user_name'] = account.username
│           │   └─ request.session['user_email'] = account.email
│           │
│           └─ [7] Return Response & Redirect
│               └─ { ok: true } → Redirect to /
│
├─→ [8] User Redirected to Dashboard
│   └─ GET / → dashboard()
│       ├─ Check session: account = get_current_account(request)
│       ├─ Load UserProfile, NutritionLog, MealPlan
│       └─ Render dashboard.html
│
└─→ [END] User Now Authenticated ✓

Timeline: 2-3 seconds (DB writes + redirect)
Possible Errors:
  - 400: Validation failed (username exists, password weak)
  - 500: Database error (email collision, disk full)
```

#### Flow: UC-AUTH-002 - Đăng Nhập (Login)

```
┌─ User (Guest or Session Expired)
│
├─→ [1] Click "Đăng Nhập" button
│   └─ GET /dang-nhap/ → Render login.html
│
├─→ [2] Fill Form & Submit
│   └─ POST /auth/login/
│       ├─ Data: { username, password }
│       ├─ Normalize: username = username.strip().lower()
│       │
│       ├─ [3] Query Account:
│       │   └─ account = Account.objects.filter(
│       │       Q(username__iexact=username) | Q(email__iexact=username),
│       │       is_active=True
│       │     ).first()
│       │
│       ├─ If NOT found:
│       │  └─ Return 404: { error: "Tài khoản không tồn tại" }
│       │
│       ├─ [4] Verify Password:
│       │   └─ if NOT verify_account_password(account, password):
│       │       └─ Return 401: { error: "Mật khẩu sai" }
│       │
│       └─ If Password Correct:
│           ├─ [5] Set Session:
│           │   ├─ request.session['user_id'] = account.id
│           │   ├─ request.session.set_expiry(timedelta(hours=24))
│           │   └─ request.session['last_login'] = datetime.now()
│           │
│           └─ [6] Return Response
│               └─ { ok: true } → Redirect to /
│
├─→ [7] Browser Stores Session Cookie
│   └─ Set-Cookie: sessionid=<hash>; Path=/; HttpOnly; Max-Age=86400
│
├─→ [8] User Redirected to Dashboard
│   └─ Next requests: cookies automatically send sessionid
│
└─→ [END] User Logged In ✓

Timeline: 1-2 seconds (password hash verify + DB write)
Security: Password never stored in plaintext, hashed with PBKDF2
Possible Errors:
  - 404: User not found
  - 401: Password mismatch
  - 403: Account deactivated/banned
```

---

### B. NUTRITION TRACKING FLOWS

#### Flow: UC-NUTRITION-LOG-001 - Ghi Lại Bữa Ăn

```
┌─ User (logged in)
│
├─→ [1] Navigate to Nutrition Page
│   └─ GET /theo-doi/ → Load nutrition.html
│
├─→ [2] Click "Ghi dinh dưỡng" Button
│   └─ Modal opens: "Thêm bữa ăn"
│
├─→ [3] Search & Select Food
│   │
│   └─ Nested Flow UC-FOOD-SEARCH-001:
│       ├─ User types "cá hồi" in search
│       ├─ API GET /api/foods/search/?q=cá%20hồi
│       │  ├─ Query: Food.objects.filter(name__icontains="cá hồi")[:20]
│       │  ├─ If results empty → Call Spoonacular API
│       │  └─ Return [{ id, name, calories, protein, carbs, fat }, ...]
│       └─ Select from dropdown: "Cá hồi nướng" (ID=42)
│
├─→ [4] Fill Nutrition Form
│   ├─ Food: Cá hồi nướng (auto-filled)
│   ├─ Date: 2026-05-07 (default=today)
│   ├─ Meal Type: "Bữa trưa" (from dropdown)
│   ├─ Servings: 1.5 (default=1)
│   └─ Notes: "nướng không dầu" (optional)
│
├─→ [5] Submit Form
│   └─ POST /api/nutrition/log/
│       ├─ Data: {
│       │   food_id: 42,
│       │   date: "2026-05-07",
│       │   meal_type: "Bữa trưa",
│       │   servings: 1.5,
│       │   notes: "nướng không dầu"
│       │ }
│       │
│       ├─ [6] Validate:
│       │   ├─ food_id → Food.objects.get() ✓
│       │   ├─ date → dateutil.parse() ✓
│       │   ├─ meal_type → in MealTypeConfig ✓
│       │   ├─ servings → float > 0 ✓
│       │   └─ account → get_current_account(request) ✓✓✓ (FIX #3)
│       │
│       ├─ [7] Calculate Nutrition:
│       │   ├─ food = Food.objects.get(id=42)
│       │   ├─ total_calories = food.calories * servings
│       │   │                 = 280 * 1.5 = 420 kcal
│       │   ├─ total_protein = food.protein * servings
│       │   │                = 25 * 1.5 = 37.5 g
│       │   ├─ total_carbs = food.carbs * servings
│       │   │              = 0 * 1.5 = 0 g
│       │   └─ total_fat = food.fat * servings
│       │               = 17 * 1.5 = 25.5 g
│       │
│       ├─ [8] Create NutritionLog:
│       │   └─ NutritionLog(
│       │       account=account,
│       │       food=food,
│       │       date="2026-05-07",
│       │       meal_type="Bữa trưa",
│       │       servings=Decimal('1.5'),
│       │       total_calories=Decimal('420'),
│       │       total_protein=Decimal('37.5'),
│       │       total_carbs=Decimal('0'),
│       │       total_fat=Decimal('25.5'),
│       │       notes="nướng không dầu",
│       │       created_at=timezone.now()
│       │     ).save()
│       │
│       ├─ [9] Update PersonalizationData:
│       │   └─ build_user_preference_profile(account)
│       │       ├─ Analyze last 7 days nutrition
│       │       ├─ Update PersonalizationData.avg_macro
│       │       ├─ Recalculate AI recommendations
│       │       └─ Update recommendation_timestamp
│       │
│       └─ [10] Return Response:
│           └─ { 
│             id: 1234,
│             food: "Cá hồi nướng",
│             calories: 420,
│             date: "2026-05-07"
│           }
│
├─→ [11] Modal Closes, Page Refreshes
│   └─ GET /theo-doi/ → Reload nutrition page
│       ├─ Re-fetch NutritionLog for today
│       ├─ Recalculate totals
│       └─ Update cards: "1850 / 2000 kcal (92.5%)"
│
└─→ [END] Food Logged ✓

Timeline: 2-3 seconds (validation + DB write + recommendation recalc)
Database Changes:
  - +1 row in nutrition_logs
  - +1 potentially in nutrition_summaries (daily agg)
  - ±1 in ai_recommendations
Possible Errors:
  - 400: Validation failed (food not found, invalid date)
  - 401: User not logged in (FIX #3)
  - 500: Database error
```

#### Flow: UC-NUTRITION-LOG-002 - Xem Nhật Ký Ăn Uống

```
┌─ User (logged in)
│
├─→ [1] Navigate to Nutrition Page
│   └─ GET /theo-doi/
│       ├─ account = get_current_account(request)
│       ├─ today = date.today()  # 2026-05-07
│       │
│       ├─ [2] Fetch Today's Logs:
│       │   └─ logs_today = NutritionLog.objects.filter(
│       │       account=account,
│       │       date=today  # WHERE date='2026-05-07'
│       │     ).select_related('food').order_by('created_at')
│       │   └─ Result: [
│       │       { food: "Cơm Sáng", servings: 2, calories: 300 },
│       │       { food: "Trứng", servings: 2, calories: 150 },
│       │       { food: "Cá hồi", servings: 1.5, calories: 420 }
│       │     ]
│       │
│       ├─ [3] Calculate Daily Totals:
│       │   ├─ sum_calories = 300 + 150 + 420 = 870 kcal
│       │   ├─ sum_protein = (10 + 12 + 37.5) = 59.5 g
│       │   ├─ sum_carbs = (60 + 1 + 0) = 61 g
│       │   └─ sum_fat = (5 + 11 + 25.5) = 41.5 g
│       │
│       ├─ [4] Get Target from UserProfile:
│       │   ├─ target_calories = 2000 (or profile.daily_calorie_target)
│       │   ├─ target_protein = target * 0.25 / 4 = 125 g
│       │   ├─ target_carbs = target * 0.50 / 4 = 250 g
│       │   └─ target_fat = target * 0.25 / 9 = 55.6 g
│       │
│       ├─ [5] Calculate Percentages:
│       │   ├─ calories_percent = (870 / 2000) * 100 = 43.5%
│       │   ├─ protein_percent = (59.5 / 125) * 100 = 47.6%
│       │   ├─ carbs_percent = (61 / 250) * 100 = 24.4%
│       │   └─ fat_percent = (41.5 / 55.6) * 100 = 74.6%
│       │
│       ├─ [6] Fetch Historical Data (Last 7 Days):
│       │   ├─ past_7_days = NutritionLog.objects.filter(
│       │       account=account,
│       │       date__gte=(today - timedelta(days=7)),
│       │       date__lte=today
│       │     ).values('date').annotate(
│       │       total_cal=Sum('total_calories'),
│       │       log_count=Count('id')
│       │     )
│       │   └─ Result: [
│       │       { date: '2026-05-01', total_cal: 1950, log_count: 3 },
│       │       { date: '2026-05-02', total_cal: 2100, log_count: 4 },
│       │       { date: '2026-05-03', total_cal: 1850, log_count: 3 },
│       │       { date: '2026-05-04', total_cal: 2050, log_count: 4 },
│       │       { date: '2026-05-05', total_cal: 1900, log_count: 3 },
│       │       { date: '2026-05-06', total_cal: 2200, log_count: 5 },
│       │       { date: '2026-05-07', total_cal: 870, log_count: 3 }
│       │     ]
│       │
│       ├─ [7] Render nutrition.html:
│       │   ├─ Nutrition Summary Cards:
│       │   │  ├─ Card 1 - Calories: "870 / 2000 (43.5%)" | Status: "Còn thiếu"
│       │   │  ├─ Card 2 - Protein: "59.5g / 125g (47.6%)" | Status: "Còn thiếu"
│       │   │  ├─ Card 3 - Carbs: "61g / 250g (24.4%)" | Status: "Còn thiếu"
│       │   │  └─ Card 4 - Fat: "41.5g / 55.6g (74.6%)" | Status: "OK"
│       │   │
│       │   ├─ Food Log Table:
│       │   │  ├─ Time | Food | Servings | Calories | Actions
│       │   │  ├─ 7:30 | Cơm Sáng | 2 | 300 | [Delete]
│       │   │  ├─ 8:15 | Trứng | 2 | 150 | [Delete]
│       │   │  └─ 12:30 | Cá hồi | 1.5 | 420 | [Delete]
│       │   │
│       │   └─ 7-Day Chart:
│       │       └─ Line chart: X=date, Y=total_cal
│       │           ├─ Day 1: 1950 kcal
│       │           ├─ Day 2: 2100 kcal
│       │           ├─ ...
│       │           └─ Day 7: 870 kcal ← Current (incomplete)
│       │
│       └─ [8] Insight Message:
│           └─ "Bạn ăn 870 kcal hôm nay. Còn thiếu 1130 kcal để đạt mục tiêu. Có vẻ hôm nay bạn ăn nhẹ hơn bình thường."
│
└─→ [END] Nutrition Displayed ✓

Timeline: 1-2 seconds (DB queries + rendering)
Database Queries:
  - 1 × NutritionLog (today)
  - 1 × UserProfile (targets)
  - 1 × NutritionLog (aggregated, 7 days)
  - 1 × ChatMessage (if insights enabled)
Performance:
  - Should cache UserProfile for 1 hour
  - Can use DB indexes on (account_id, date)
```

---

### C. MEAL PLANNING FLOWS

#### Flow: UC-MEAL-PLAN-001 & 002 - Lập & Xem Thực Đơn

```
┌─ User (logged in)
│
├─→ [1] Navigate to Meal Plans Page
│   └─ GET /thuc-don/
│       ├─ account = get_current_account(request)
│       ├─ today = date.today()
│       ├─ year, month = get from GET params or defaults
│       │
│       ├─ [2] Generate Calendar:
│       │   ├─ cal = calendar.monthcalendar(year, month)
│       │   └─ Result: [[1,2,3,4,5,6,7], [8,9,10,...], ...]
│       │       # 2026 May calendar grid
│       │
│       ├─ [3] Fetch MealPlans for Month:
│       │   ├─ first_day = f'{year}-{month:02d}-01'
│       │   ├─ last_day = f'{year}-{month+1:02d}-01' (or next year)
│       │   └─ plans = MealPlan.objects.filter(
│       │       account=account,  # ✓ FIX #1 - MUST HAVE
│       │       date__gte=first_day,
│       │       date__lt=last_day
│       │     ).select_related('food')
│       │
│       ├─ [4] Group by Date:
│       │   ├─ plans_by_date = {}
│       │   ├─ For each plan in plans:
│       │   │  └─ plans_by_date['2026-05-07'].append(plan)
│       │   │
│       │   └─ Result: {
│       │       '2026-05-07': [
│       │         { food: "Cơm Sáng", meal_type: "Bữa sáng", id: 1 },
│       │         { food: "Cá hồi", meal_type: "Bữa trưa", id: 2 }
│       │       ],
│       │       '2026-05-08': [ ... ]
│       │     }
│       │
│       ├─ [5] Render Calendar:
│       │   ├─ For each day (1-31) in month:
│       │   │  ├─ Render <div class="calendar-day">
│       │   │  ├─ Show day number
│       │   │  ├─ Show plan badges for that day:
│       │   │  │  └─ <span class="badge" style="color: {meal_type_color}">
│       │   │  │      {food_name}
│       │   │  │    </span>
│       │   │  └─ onclick="openAddForDate('2026-05-07')"
│       │   │
│       │   └─ Result: Visual calendar with colored badges
│       │
│       ├─ [6] Load Food Dropdown:
│       │   └─ foods = Food.objects.all().order_by('name')
│       │       └─ <select id="plan-food">
│       │           ├─ <option value="1">Cá hồi nướng (280 kcal)</option>
│       │           ├─ <option value="2">Cơm tấm (350 kcal)</option>
│       │           └─ ... (100+ foods)
│       │
│       └─ [7] Render meal_plans.html:
│           ├─ Calendar grid with badges
│           ├─ "Thêm thực đơn" button
│           ├─ Modal for adding plan (hidden, triggered by day click)
│           └─ Navigation: "< Tháng trước | Tháng 5 | Tháng sau >"
│
├─→ [8] User Clicks "Thêm thực đơn" or Day in Calendar
│   └─ openAddForDate('2026-05-07') [JavaScript]
│       ├─ Set plan-date.value = '2026-05-07'
│       ├─ Show #addPlanModal
│       └─ Focus on food dropdown
│
├─→ [9] User Selects & Submits Plan
│   ├─ Food dropdown: "Cá hồi nướng" (ID=1)
│   ├─ Date: 2026-05-07
│   ├─ Meal Type: "Bữa trưa" (dropdown)
│   ├─ Servings: 1.5
│   ├─ Notes: "nướng, không dầu"
│   └─ Click "Thêm vào thực đơn"
│
├─→ [10] addPlan() [JavaScript Function]
│   └─ const data = {
│       date: "2026-05-07",
│       meal_type: "Bữa trưa",
│       food_id: 1,
│       servings: 1.5,
│       notes: "nướng, không dầu"
│     }
│
├─→ [11] POST /api/meal-plan/add/
│   └─ Handler: meal_plan_add() in views.py
│       ├─ [12] Validate Request:
│       │   ├─ data = json.loads(request.body)
│       │   ├─ food = get_object_or_404(Food, id=data['food_id'])
│       │   ├─ account = get_current_account(request)
│       │   │
│       │   └─ ✓✓✓ FIX #1: Add this check!
│       │      if not account:
│       │        return JsonResponse({'error': 'Vui lòng đăng nhập'}, 401)
│       │
│       ├─ [13] Create MealPlan:
│       │   └─ plan = MealPlan.objects.create(
│       │       account=account,  # ← NOW NOT NULL ✓
│       │       food=food,
│       │       date='2026-05-07',
│       │       meal_type='Bữa trưa',
│       │       servings=Decimal('1.5'),
│       │       notes='nướng, không dầu',
│       │       created_at=timezone.now()
│       │     )
│       │
│       └─ [14] Return Response:
│           └─ {
│             id: 567,
│             food: "Cá hồi nướng",
│             date: "2026-05-07",
│             meal_type: "Bữa trưa"
│           }
│
├─→ [15] JavaScript Receives Response
│   ├─ if (response.ok):
│   │  └─ location.reload()  # Refresh page
│   └─ else:
│       └─ alert('Có lỗi xảy ra')
│
├─→ [16] Page Reloads (repeat from [2])
│   └─ MealPlan now visible as badge on calendar!
│
└─→ [END] Meal Plan Added ✓

Timeline: 3-4 seconds (rendering + modal + POST + reload)
Database Changes:
  - +1 row in meal_plans table
Visual Changes:
  - Calendar: "Bữa trưa | Cá hồi" badge appears on 5/7
  - Color: {meal_type_color} (e.g., blue for "Bữa trưa")
Possible Errors:
  - 400: Food not found, invalid date, invalid meal_type
  - 401: User not logged in ← FIX #1 required
  - 500: Database error
```

---

### D. AI CHAT & RECOMMENDATIONS

#### Flow: UC-CHAT-001 - Gửi & Nhận Phản Hồi AI

```
┌─ User (logged in or guest)
│
├─→ [1] Navigate to Chat Page
│   └─ GET /chat/
│       ├─ account = get_current_account(request)
│       │          # If None, guest created: account = get_or_create_guest_account()
│       │
│       ├─ [2] Get/Create ChatSession:
│       │   └─ chat_session = get_chat_session(account)
│       │       ├─ query: ChatSession.objects.filter(account=account, active=True)
│       │       ├─ if not found:
│       │       │  └─ create new ChatSession(account=account)
│       │       └─ return session
│       │
│       ├─ [3] Load Chat History:
│       │   └─ messages = ChatMessage.objects.filter(
│       │       session=chat_session
│       │     ).order_by('created_at')[:100]  # Last 100 messages
│       │
│       ├─ [4] Render chat.html:
│       │   ├─ <div id="chat-container">
│       │   │  ├─ For each message in messages:
│       │   │  │  ├─ If role='user':
│       │   │  │  │  └─ <div class="msg-user">User text</div>
│       │   │  │  └─ If role='assistant':
│       │   │  │     └─ <div class="msg-assistant">AI text</div>
│       │   │  └─ [Latest message at bottom]
│       │   │
│       │   └─ <form id="chat-form">
│       │       ├─ <textarea id="message-input" />
│       │       └─ <button>Gửi</button>
│       │
│       └─ Render finished
│
├─→ [5] User Types & Sends Message
│   └─ User text: "Hôm nay tôi muốn giảm cân, nên ăn gì?"
│       └─ Click "Gửi" button
│
├─→ [6] JavaScript Sends Message
│   └─ fetch('/api/chat/send/', {
│       method: 'POST',
│       body: JSON.stringify({ message: user_text }),
│       headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf }
│     })
│
├─→ [7] POST /api/chat/send/
│   └─ Handler: chat_send() in views.py
│       ├─ [8] Parse & Validate:
│       │   ├─ data = json.loads(request.body)
│       │   ├─ user_text = data.get('message', '').strip()
│       │   └─ if not user_text:
│       │       └─ return error 400
│       │
│       ├─ [9] Get/Create Account & Session:
│       │   ├─ account = get_current_account(request)
│       │   ├─ if not account:
│       │   │  └─ account = get_or_create_guest_account(request)
│       │   └─ chat_session = get_chat_session(account)
│       │
│       ├─ [10] Save User Message:
│       │   └─ user_msg = ChatMessage.objects.create(
│       │       session=chat_session,
│       │       role='user',
│       │       content='Hôm nay tôi muốn giảm cân, nên ăn gì?',
│       │       created_at=timezone.now()
│       │     )
│       │
│       ├─ [11] Classify Intent:
│       │   └─ intent, confidence = classify_intent(user_text)
│       │       ├─ Normalize: "hôm nay tôi muốn giảm cân, nên ăn gì?"
│       │       ├─ Pattern match: "giam can" (weight loss)
│       │       └─ return (Intent(name='WEIGHT_LOSS'), 0.92)
│       │
│       ├─ [12] Save Intent:
│       │   └─ MessageIntent.objects.create(
│       │       message=user_msg,
│       │       intent=intent,
│       │       confidence=0.92
│       │     )
│       │
│       ├─ [13] Check for Auto-Plan Request:
│       │   └─ auto_plan_message = _auto_create_meal_plan_from_chat(user_text, account)
│       │       ├─ if user_text contains: "thực đơn", "meal plan", "lập thực đơn"
│       │       │  ├─ extract days: 7 (default)
│       │       │  ├─ fetch foods: Food.objects.all()[:50]
│       │       │  ├─ bulk create MealPlan records
│       │       │  └─ return message: "Đã lập thực đơn 7 ngày"
│       │       │
│       │       └─ return None (not a plan request)
│       │
│       ├─ [14] If Auto-Plan Message:
│       │   └─ response_text = auto_plan_message
│       │       └─ goto [23] Save Assistant Message
│       │
│       ├─ [15] Otherwise, Build Gemini Request:
│       │   ├─ Get User Profile:
│       │   │  └─ profile = get_profile(account)
│       │   │      # { name, age, weight, health_goals, constraints }
│       │   │
│       │   ├─ Build System Prompt:
│       │   │  └─ system_prompt = """
│       │   │     Bạn là "Nội Trợ AI", trợ lý nội trợ thông minh người Việt...
│       │   │     Người dùng: {name}, {age} tuổi, {weight}kg, mục tiêu: {goals}
│       │   │     """
│       │   │
│       │   ├─ Build Conversation History:
│       │   │  └─ messages = [
│       │   │       { role: 'user', content: 'Hôm qua tôi ăn cơm tấm' },
│       │   │       { role: 'assistant', content: 'Cơm tấm rất ngon, giàu carbs...' },
│       │   │       { role: 'user', content: 'Hôm nay tôi muốn giảm cân...' }
│       │   │     ]
│       │   │
│       │   ├─ [16] Check ChatResponseCache:
│       │   │  └─ cache_result = get_or_create_chat_response_from_cache(
│       │   │       account, user_text, source_intent='WEIGHT_LOSS'
│       │   │     )
│       │   │     ├─ Normalize: "hôm nay tôi muốn giảm cân nên ăn gì"
│       │   │     ├─ Search cache:
│       │   │     │  └─ ChatResponseCache.objects.filter(
│       │   │     │      normalized_query__icontains='giam can'
│       │   │     │    ).order_by('-created_at')[:10]
│       │   │     ├─ Calculate similarity with cached queries
│       │   │     ├─ if similarity >= 0.85:
│       │   │     │  └─ return cached response ✓ (save API call)
│       │   │     └─ else:
│       │   │        └─ return None (need Gemini)
│       │   │
│       │   ├─ [17] If Cache Hit:
│       │   │  └─ response_text = cache_result['response']
│       │   │      └─ goto [23] Save Assistant Message
│       │   │
│       │   ├─ [18] If Cache Miss, Call Gemini API:
│       │   │  └─ ai_text, ai_err = call_gemini_with_debug(
│       │   │       profile, chat_session, system_prompt
│       │   │     )
│       │   │     ├─ client.messages.create(
│       │   │     │   model='gemini-1.5-flash',
│       │   │     │   system=system_prompt,
│       │   │     │   messages=messages
│       │   │     │ )
│       │   │     │
│       │   │     ├─ timeout: 10 seconds
│       │   │     ├─ return: (response.content[0].text, None) or (None, error_dict)
│       │   │     │
│       │   │     └─ Possible errors:
│       │   │         ├─ 429 RESOURCE_EXHAUSTED (quota exceeded)
│       │   │         ├─ 503 SERVICE_UNAVAILABLE (API down)
│       │   │         ├─ 401 UNAUTHENTICATED (bad API key)
│       │   │         └─ Timeout (> 10s)
│       │   │
│       │   ├─ [19] Handle Gemini Errors:
│       │   │  ├─ if '429' in error or 'RESOURCE_EXHAUSTED':
│       │   │  │  └─ response_text = _build_ai_quota_fallback_response()
│       │   │  │      # "Gemini đạt quota. Hãy thử lại sau..."
│       │   │  │      # + fallback: recommend recipes from DB
│       │   │  │
│       │   │  └─ else:
│       │   │     └─ response_text = "AI tạm thời gặp lỗi..."
│       │   │
│       │   ├─ [20] If No Error:
│       │   │  └─ response_text = ai_text.strip()
│       │   │
│       │   ├─ [21] Save Response to Cache:
│       │   │  └─ save_chat_response_to_cache(
│       │   │       account, user_text, response_text, 'WEIGHT_LOSS'
│       │   │     )
│       │   │     ├─ ChatResponseCache.objects.create(
│       │   │     │   normalized_query='hôm nay tôi muốn giảm cân nên ăn gì',
│       │   │     │   original_query='Hôm nay tôi muốn giảm cân, nên ăn gì?',
│       │   │     │   response=response_text,
│       │   │     │   usage_count=1
│       │   │     │ )
│       │   │     └─ ignore errors (cache not critical)
│       │   │
│       └─ [22] Append Health Feedback:
│           └─ response_text = _append_health_feedback(
│               response_text, account, user_text
│             )
│             ├─ Analyze user's nutrition last 7 days
│             ├─ Add feedback: "Bạn đang ăn rất cân bằng!" or "Ăn không đủ!"
│             └─ return response_text + feedback
│
├─→ [23] Save Assistant Message:
│   └─ msg = ChatMessage.objects.create(
│       session=chat_session,
│       role='assistant',
│       content=response_text,
│       created_at=timezone.now()
│     )
│
├─→ [24] Update Preference Profile:
│   └─ build_user_preference_profile(account)
│       ├─ Analyze this interaction
│       ├─ Update PersonalizationData
│       └─ Recalculate AI recommendations
│
├─→ [25] Return Response to JavaScript:
│   └─ {
│       role: 'assistant',
│       content: response_text
│     }
│
├─→ [26] JavaScript Appends Message to Chat:
│   └─ const msgDiv = document.createElement('div')
│       msgDiv.className = 'msg-assistant'
│       msgDiv.textContent = response_text
│       chatContainer.appendChild(msgDiv)
│       chatContainer.scrollTop = chatContainer.scrollHeight
│
└─→ [END] Chat Message Sent & Response Received ✓

Timeline:
  - Cache hit: 100-200ms
  - Gemini call: 3-8 seconds
  - Total: 4-10 seconds

Database Changes:
  - +1 ChatMessage (user)
  - +1 MessageIntent
  - +1 ChatMessage (assistant)
  - +0 to +1 ChatResponseCache (only if new)
  - ±1 PersonalizationData (update)

API Calls:
  - Gemini API: 1 call (if no cache)
  - Spoonacular: 0 (not needed for chat)

Possible Errors:
  - 400: Empty message
  - 401: Not authenticated (guests auto-created)
  - 429: Gemini quota exceeded (fallback used)
  - 500: Database error
  - 503: Gemini API down (fallback used)
```

---

**[Document continues with additional flows for: Dashboard, Admin Operations, Intent Classification, and External APIs...]**

**Word Count So Far:** ~6,500 words
**Features Covered:** Authentication, Nutrition Tracking, Meal Planning, AI Chat
**Remaining to Document:** Dashboard, Admin Panel, Intent System, Data Consolidation, Performance & Capacity

---

### A. CHỨC NĂNG CƠ BẢN - SMALL FEATURES (Nhỏ)

#### 1.1. Xác thực người dùng (Authentication)

**Usecase: UC-AUTH-001 - Đăng ký tài khoản**
- **Actor:** Khách (chưa đăng nhập)
- **Trigger:** Click nút "Đăng ký"
- **Flow chính:**
  1. Nhập username, email, mật khẩu
  2. Hệ thống kiểm tra username/email chưa tồn tại
  3. Lưu tài khoản mới vào `apps.users.Account`
  4. Tạo hồ sơ người dùng mặc định (UserProfile)
  5. Chuyển hướng tới dashboard
- **Input:** username, email, password
- **Output:** Account mới, session tạo, redirect `/`
- **Validation:** Email phải hợp lệ, username duy nhất

**Usecase: UC-AUTH-002 - Đăng nhập**
- **Actor:** Khách
- **Trigger:** Click nút "Đăng nhập"
- **Flow chính:**
  1. Nhập username/email, mật khẩu
  2. Kiểm tra credentials trong DB
  3. Nếu hợp lệ → tạo session với account_id
  4. Chuyển hướng tới dashboard
- **Input:** username/email, password
- **Output:** Session được tạo, cookie lưu trên client
- **Validation:** Credentials phải chính xác

**Usecase: UC-AUTH-003 - Đăng xuất**
- **Actor:** User (đã đăng nhập)
- **Trigger:** Click "Đăng xuất"
- **Flow chính:**
  1. Xóa session từ DB
  2. Clear cookie trên client
  3. Redirect tới trang login
- **Output:** Session được xóa

**Usecase: UC-AUTH-004 - Xem thông tin tài khoản**
- **Actor:** User (đã đăng nhập)
- **Trigger:** API call `/auth/me/`
- **Flow chính:**
  1. Kiểm tra session hiện tại
  2. Lấy Account object
  3. Trả về JSON với thông tin: id, username, email, role
- **Output:** JSON: `{ id, username, email, role, created_at }`

---

#### 1.2. Quản lý hồ sơ người dùng (Profile Management)

**Usecase: UC-PROFILE-001 - Xem hồ sơ sức khỏe**
- **Actor:** User
- **Trigger:** Click menu "Hồ sơ"
- **Flow chính:**
  1. Load UserProfile của user hiện tại
  2. Hiển thị: tuổi, cân nặng, chiều cao, mục tiêu sức khỏe
  3. Hiển thị các ràng buộc: bệnh tật, dị ứng
- **Output:** Trang profile.html với dữ liệu
- **Fields:**
  - `age`: Tuổi
  - `weight`: Cân nặng (kg)
  - `height`: Chiều cao (cm)
  - `target_calories`: Mục tiêu kcal/ngày
  - `health_notes`: Ghi chú sức khỏe
  - `health_goals`: Danh sách mục tiêu
  - `constraints`: Danh sách ràng buộc (bệnh, dị ứng)

**Usecase: UC-PROFILE-002 - Cập nhật hồ sơ sức khỏe**
- **Actor:** User
- **Trigger:** Submit form trên trang hồ sơ
- **Flow chính:**
  1. Lấy dữ liệu từ form: age, weight, height, health_goals, constraints
  2. Validate dữ liệu (age > 0, weight > 0, etc.)
  3. Update `apps.users.UserProfile`
  4. Trigger `build_user_preference_profile()` để cập nhật khuyến cáo
  5. Lưu thành công
- **Input:** age, weight, height, health_goals[], constraints[]
- **Output:** JSON `{ success: true }`
- **Side effects:** Cập nhật PersonalizationData, AI recommendations

---

#### 1.3. Tìm kiếm thực phẩm (Food Search)

**Usecase: UC-FOOD-SEARCH-001 - Tìm kiếm thực phẩm cơ bản**
- **Actor:** User
- **Trigger:** Gõ tên thực phẩm vào ô tìm kiếm
- **Flow chính:**
  1. User gõ "cá hồi"
  2. API `/api/foods/search/?q=cá%20hồi` được gọi
  3. Hệ thống tìm trong DB trước (Food table)
  4. Nếu không đủ → gọi Spoonacular API
  5. Trả về danh sách max 20 kết quả
- **Input:** q = "cá hồi"
- **Output:** JSON array của foods:
  ```json
  [
    { id: 1, name: "Cá hồi nướng", calories: 280, protein: 25, ... },
    { id: 2, name: "Cá hồi xào", calories: 320, protein: 24, ... }
  ]
  ```
- **Priority:** DB > API (Spoonacular)

**Usecase: UC-FOOD-SEARCH-002 - Tra cứu chi tiết một thực phẩm**
- **Actor:** User
- **Trigger:** Click vào kết quả tìm kiếm
- **Flow chính:**
  1. API `/api/foods/lookup/?name=cá%20hồi` được gọi
  2. Tìm trong DB với exact match hoặc fuzzy match
  3. Nếu không có → gọi Spoonacular API
  4. Trả về chi tiết: tên, kcal, macro (protein/carbs/fat), thành phần
- **Output:** JSON chi tiết thực phẩm:
  ```json
  {
    id: 1,
    name: "Cá hồi nướng",
    calories: 280,
    protein: 25,
    carbs: 0,
    fat: 17,
    ingredients: [...],
    description: "Source: Database"
  }
  ```

**Usecase: UC-FOOD-SEARCH-003 - Duyệt danh sách thực phẩm**
- **Actor:** User
- **Trigger:** Click menu "Món ăn"
- **Flow chính:**
  1. Load trang foods.html
  2. Hiển thị danh sách 20 thực phẩm đầu tiên từ DB
  3. Cung cấp ô tìm kiếm để filter theo tên, category
  4. Cho phép sắp xếp theo: tên (A-Z), kcal (low-high)
- **Output:** Trang foods.html với danh sách, filter, sort options

---

#### 1.4. Theo dõi dinh dưỡng (Nutrition Logging)

**Usecase: UC-NUTRITION-LOG-001 - Ghi lại bữa ăn**
- **Actor:** User
- **Trigger:** Click "Ghi dinh dưỡng" → chọn thực phẩm
- **Flow chính:**
  1. User chọn thực phẩm: "Cơm tấm"
  2. Nhập số lượng: 1 đĩa (default: 1)
  3. Chọn loại bữa: Sáng/Trưa/Chiều/Tối
  4. Chọn ngày: Default = hôm nay
  5. API POST `/api/nutrition/log/` được gọi
  6. Hệ thống tính macro thực tế:
     - `total_calories = food.calories * servings`
     - `total_protein = food.protein * servings`
     - ... (carbs, fat)
  7. Tạo NutritionLog record
  8. Update PersonalizationData
- **Input:** food_id, servings, meal_type, date
- **Output:** JSON `{ id, food, calories, date }`
- **Side effects:** Cập nhật tổng macro hôm nay, nhắc nhở AI

**Usecase: UC-NUTRITION-LOG-002 - Xem nhật ký ăn uống**
- **Actor:** User
- **Trigger:** Click menu "Theo dõi"
- **Flow chính:**
  1. Load trang nutrition.html
  2. Lấy NutritionLog của user hôm nay
  3. Tính tổng macro:
     - Tổng kcal vs target
     - Phần trăm protein/carbs/fat vs target
  4. Hiển thị danh sách foods logged trong hôm nay
  5. Hiển thị trend 7 ngày: biểu đồ kcal, macro
  6. Hiển thị status: Thiếu/Đủ/Vượt calorie
- **Output:** Trang nutrition.html với:
  - Nutrition cards (% vs target)
  - Food log table
  - Chart trend 7 ngày
  - Insight: "Còn thiếu 250 kcal"

**Usecase: UC-NUTRITION-LOG-003 - Xóa bản ghi ăn uống**
- **Actor:** User
- **Trigger:** Click "Xóa" trên food log entry
- **Flow chính:**
  1. Confirm xác nhận xóa
  2. API DELETE `/api/nutrition/delete/{log_id}/` được gọi
  3. Xóa NutritionLog record
  4. Trang reload, cập nhật tổng macro
- **Output:** JSON `{ ok: true }`

**Usecase: UC-NUTRITION-LOG-004 - Xem macro intake theo ngày**
- **Actor:** User
- **Trigger:** View nutrition.html
- **Flow chính:**
  1. Lấy NutritionLog của date được chọn (default: hôm nay)
  2. Tính tổng:
     - `sum(calories)`, `sum(protein)`, `sum(carbs)`, `sum(fat)`
  3. So sánh với target từ UserProfile:
     - `target_calories` (default: 2000 kcal)
     - Tính phần trăm: `(sum / target) * 100%`
  4. Hiển thị status:
     - ✓ Đủ nếu 90-110% target
     - ⚠ Vượt nếu > 110% target
     - ⚠ Thiếu nếu < 90% target
- **Output:** Nutrition summary card:
  ```json
  {
    total_calories: 1850,
    target_calories: 2000,
    percent: 92.5,
    status: "Đủ",
    remaining: 150
  }
  ```

---

### B. CHỨC NĂNG TRUNG BÌNH - MEDIUM FEATURES (Vừa)

#### 2.1. Lập kế hoạch bữa ăn (Meal Planning)

**Usecase: UC-MEAL-PLAN-001 - Xem lịch thực đơn theo tháng**
- **Actor:** User
- **Trigger:** Click menu "Thực đơn" hoặc `/thuc-don/`
- **Flow chính:**
  1. Load trang meal_plans.html
  2. Hiển thị lịch tháng (calendar view)
  3. Lấy MealPlan của user cho tháng hiện tại
  4. Highlight các ngày có thực đơn được lên kế hoạch
  5. Cung cấp nút "Trước tháng", "Tháng sau"
- **Output:** Trang meal_plans.html với:
  - Calendar grid (month view)
  - Plans by date: Ngày -> danh sách foods
  - Thêm/xóa plan buttons

**Usecase: UC-MEAL-PLAN-002 - Thêm thực phẩm vào kế hoạch bữa ăn**
- **Actor:** User
- **Trigger:** Click "Thêm vào thực đơn" trên trang foods
- **Flow chính:**
  1. User chọn: Food, Ngày, Loại bữa, Số lượng
  2. API POST `/api/meal-plan/add/` được gọi
  3. Hệ thống tạo MealPlan record:
     - account_id = current user
     - food_id = selected food
     - date = selected date
     - meal_type = Sáng/Trưa/Chiều/Tối
     - servings = quantity
  4. Lưu thành công
- **Input:** food_id, date, meal_type, servings, notes (optional)
- **Output:** JSON `{ id, food, date, meal_type }`

**Usecase: UC-MEAL-PLAN-003 - Xóa thực phẩm khỏi kế hoạch bữa ăn**
- **Actor:** User
- **Trigger:** Click "Xóa" trên MealPlan entry
- **Flow chính:**
  1. Confirm xác nhận
  2. API DELETE `/api/meal-plan/delete/{plan_id}/` được gọi
  3. Xóa MealPlan record
  4. Reload trang calendar
- **Output:** JSON `{ ok: true }`

**Usecase: UC-MEAL-PLAN-004 - Xem chi tiết thực đơn theo ngày**
- **Actor:** User
- **Trigger:** Click vào ngày trên calendar
- **Flow chính:**
  1. Pop-up hoặc slide-out hiển thị MealPlans của ngày đó
  2. Nhóm theo loại bữa: Sáng, Trưa, Chiều, Tối
  3. Tính tổng macro của ngày:
     - `sum(calories)` của tất cả foods
     - Tính % vs target_calories
  4. Hiển thị: Food list, tổng kcal, macro
  5. Cung cấp nút thêm/xóa
- **Output:** Modal/slideout hiển thị:
  ```json
  {
    date: "2026-05-04",
    meals: {
      "Sáng": [{ food_name, calories, servings }],
      "Trưa": [...],
      ...
    },
    total_calories: 2100,
    target: 2000
  }
  ```

---

#### 2.2. Chat với AI trợ lý (AI Chat Assistant)

**Usecase: UC-CHAT-001 - Gửi tin nhắn chat**
- **Actor:** User
- **Trigger:** Nhập tin nhắn vào ô chat → nhấn "Gửi"
- **Flow chính:**
  1. User nhập: "Tôi muốn giảm cân, nên ăn gì bây giờ?"
  2. API POST `/api/chat/send/` được gọi
  3. Hệ thống:
     - Lưu tin nhắn vào ChatMessage (role='user')
     - Phân loại intent: HEALTH_ADVICE, MEAL_PLAN, ...
     - Lưu intent vào MessageIntent
     - Gọi Gemini API với context:
       - User profile (age, weight, goals, constraints)
       - Nutrition log hôm nay
       - Meal plans của ngày
     - Nhận response từ Gemini
     - Lưu response vào ChatMessage (role='assistant')
  4. Trả về tin nhắn cho client
- **Input:** message = "Tôi muốn giảm cân, nên ăn gì bây giờ?"
- **Output:** JSON:
  ```json
  {
    role: "assistant",
    content: "Để giảm cân, bạn nên ăn...",
    intent: "HEALTH_ADVICE",
    confidence: 0.95
  }
  ```
- **Side effects:**
  - Lưu ChatMessage
  - Phân loại Intent
  - Auto-tạo MealPlan nếu có nhắc tới (UC-CHAT-AUTO-PLAN)

**Usecase: UC-CHAT-AUTO-PLAN - Tự động lên thực đơn từ chat**
- **Actor:** AI System
- **Trigger:** Chat message chứa keywords: "thực đơn", "meal plan", "lập thực đơn"
- **Flow chính:**
  1. Nhận diện loại thực đơn:
     - "lập thực đơn 7 ngày" → days = 7
     - "thực đơn hôm nay" → days = 1
     - "thực đơn tuần sau" → days = 7, start_date = next week
  2. Lấy danh sách Food từ DB
  3. Random pick foods, tạo MealPlan records:
     - Sáng: Random food 1
     - Trưa: Random food 2
     - Chiều: Random food 3
     - Tối: Random food 4
  4. Bulk create MealPlan records
  5. Trả về message: "Đã lên thực đơn 7 ngày (2026-05-04 → 2026-05-10)"
- **Output:** Message text về thực đơn đã được tạo

**Usecase: UC-CHAT-002 - Xem lịch sử chat**
- **Actor:** User
- **Trigger:** Load trang chat
- **Flow chính:**
  1. Load ChatSession của user
  2. Lấy tất cả ChatMessage trong session (max 100 messages gần nhất)
  3. Nhóm theo timestamp (ascending)
  4. Hiển thị dưới dạng conversation
- **Output:** Danh sách ChatMessage với role, content, timestamp

**Usecase: UC-CHAT-003 - Xóa lịch sử chat**
- **Actor:** User
- **Trigger:** Click "Xóa lịch sử chat"
- **Flow chính:**
  1. Confirm xác nhận
  2. API POST `/api/chat/clear/` được gọi
  3. Xóa tất cả ChatMessage, MessageIntent, ChatSummary của session
  4. Tạo ChatSession mới
- **Output:** JSON `{ status: "cleared" }`

**Usecase: UC-CHAT-INTENT-004 - Phân loại intent từ text**
- **Actor:** AI System
- **Trigger:** Gửi chat message
- **Flow chính:**
  1. Lấy user text
  2. Normalize text: lowercase, remove diacritics
  3. So sánh với Intent patterns:
     - Tìm Pattern trong DB với confidence > threshold
     - Nếu tìm thấy → return Intent
     - Nếu không → return None
  4. Lưu intent vào MessageIntent với confidence score
- **Output:** (Intent object, confidence: float) hoặc (None, 0.0)
- **Example:**
  - Text: "tôi muốn giảm cân"
  - Pattern match: "giam can" → Intent="WEIGHT_LOSS"
  - Confidence: 0.92

---

#### 2.3. Đánh giá công thức nấu ăn (Recipe Rating System)

**Usecase: UC-RECIPE-RATING-001 - Xem chi tiết công thức nấu ăn**
- **Actor:** User
- **Trigger:** Click vào một Recipe được khuyến cáo
- **Flow chính:**
  1. Load recipe detail page
  2. Hiển thị: Tên, ảnh, ingredients, hướng dẫn, macro, health score
  3. Hiển thị rating tổng hợp:
     - `avg_rating`: Điểm trung bình (1-5 stars)
     - `total_ratings`: Số lượng đánh giá
     - Rating stars: ★★★★☆ (3.5/5)
  4. Hiển thị rating history của user (nếu đã đánh giá trước)
- **Output:** Trang recipe detail với:
  - Recipe info (name, ingredients, steps)
  - Current rating (stars, comment) nếu user đã đánh giá
  - Other users' ratings (if available)

**Usecase: UC-RECIPE-RATING-002 - Đánh giá công thức nấu ăn**
- **Actor:** User
- **Trigger:** Submit form đánh giá (stars + comment)
- **Flow chính:**
  1. User chọn số stars: 4/5
  2. Nhập comment: "Rất ngon, dễ nấu"
  3. API POST `/api/recipe/rate/` được gọi
  4. Hệ thống:
     - Kiểm tra RecipeRating đã tồn tại của (recipe_id, account_id)
     - Nếu có → Update rating
     - Nếu không → Tạo rating mới
     - Tính lại `avg_rating`, `total_ratings` của Recipe
  5. Lưu thành công
- **Input:** recipe_id, rating (1-5), comment
- **Output:** JSON `{ id, recipe_id, rating, avg_rating, total_ratings }`

**Usecase: UC-RECIPE-RATING-003 - Xem công thức được đánh giá cao nhất**
- **Actor:** User
- **Trigger:** Click "Công thức được yêu thích"
- **Flow chính:**
  1. Query Recipe với `avg_rating DESC`
  2. Filter: `avg_rating >= 3.5` (optional threshold)
  3. Limit: 10 recipes
  4. Hiển thị danh sách: Recipe name, avg_rating, total_ratings
- **Output:** Danh sách top-rated recipes:
  ```json
  [
    { id: 1, name: "Cơm chiên", avg_rating: 4.8, total_ratings: 245 },
    { id: 2, name: "Canh chua", avg_rating: 4.6, total_ratings: 189 },
    ...
  ]
  ```

**Usecase: UC-RECIPE-AUTO-SAVE-004 - Tự động lưu công thức AI có độ tin cậy cao**
- **Actor:** AI System
- **Trigger:** Gemini generate recipe
- **Flow chính:**
  1. Gemini generate công thức cho user
  2. System tính confidence score dựa trên:
     - Có bao nhiêu ingredients user có sẵn
     - Macro match vs user goals
     - Compliance vs health constraints
  3. Nếu confidence >= 0.85:
     - Tự động tạo Recipe record:
       - `auto_added = True`
       - `created_by = 'ai'`
       - `avg_rating = null` (chưa được đánh giá)
     - Lưu vào DB
  4. Trả về response: "Công thức đã được lưu"
- **Output:** Công thức được lưu tự động nếu điều kiện đáp ứng

---

### C. CHỨC NĂNG LỚNA - LARGE FEATURES (Lớn)

#### 3.1. Dashboard tổng hợp (Main Dashboard)

**Usecase: UC-DASHBOARD-001 - Xem dashboard cá nhân hôm nay**
- **Actor:** User (đã login)
- **Trigger:** Truy cập `/` hoặc click "Dashboard"
- **Flow chính:**
  1. Load user Account, UserProfile
  2. Tính toán dữ liệu hôm nay:
     - NutritionLog của hôm nay → tổng macro
     - Tính % vs target_calories từ UserProfile
  3. Tính toán dữ liệu hôm qua:
     - NutritionLog của hôm qua → tổng macro
  4. Tính toán trend 7 ngày:
     - Mỗi ngày: sum(calories), count(logs)
     - Vẽ chart line: calories over time
  5. Tính streak (ngày liên tiếp logging):
     - Từ hôm nay, đếm ngày có log, dừng khi không có
     - Max 30 ngày
  6. Random pick 4 food recommendations:
     - Từ danh sách Food
     - Dưới menu "Gợi ý hôm nay"
  7. Hiển thị trang dashboard.html
- **Output:** Trang dashboard.html với:
  - Nutrition cards (today, yesterday, trend)
  - Status: % kcal, protein, carbs, fat
  - Chart: 7-day trend
  - Streak: "Logging 5 ngày liên tiếp"
  - Food recommendations: 4 random foods

**Usecase: UC-DASHBOARD-002 - Xem insight dinh dưỡng hôm nay**
- **Actor:** User
- **Trigger:** View dashboard
- **Flow chính:**
  1. Lấy UserProfile.target_calories (default: 2000 kcal)
  2. Lấy sum(calories) từ NutritionLog hôm nay
  3. Tính: `remaining = target - sum`
  4. Tính: `percent = (sum / target) * 100`
  5. Xác định status:
     - Percent >= 110% → "Vượt mục tiêu" (red)
     - Percent 90-110% → "Đủ mục tiêu" (green)
     - Percent < 90% → "Còn thiếu" (yellow)
  6. Tính: `direction = percent_today - percent_yesterday`
     - Nếu direction > 5% → "Tăng" (up arrow)
     - Nếu direction < -5% → "Giảm" (down arrow)
     - Nếu -5 <= direction <= 5% → "Ổn định" (flat)
  7. Hiển thị insight card
- **Output:** Insight card:
  ```json
  {
    target: 2000,
    consumed: 1850,
    remaining: 150,
    percent: 92.5,
    status: "Đủ",
    direction: "ổn định",
    message: "Bạn đang ăn đủ. Còn 150 kcal để hoàn thành mục tiêu."
  }
  ```

**Usecase: UC-DASHBOARD-003 - Xem macro breakdown hôm nay**
- **Actor:** User
- **Trigger:** View dashboard nutrition cards
- **Flow chính:**
  1. Lấy sum(protein), sum(carbs), sum(fat) từ NutritionLog hôm nay
  2. Lấy target macro từ UserProfile:
     - target_protein = target_calories * 0.25 / 4 (kcal per gram)
     - target_carbs = target_calories * 0.50 / 4
     - target_fat = target_calories * 0.25 / 9
  3. Tính phần trăm cho mỗi macro:
     - protein_percent = (sum_protein / target_protein) * 100
     - carbs_percent, fat_percent (tương tự)
  4. Hiển thị 3 cards (Protein, Carbs, Fat):
     - Mỗi card: {value}g / {target}g ({percent}%)
- **Output:** 3 macro cards với value, target, percent

---

#### 3.2. Hệ thống khuyến cáo AI (AI Recommendation System)

**Usecase: UC-AI-RECOMMEND-001 - Sinh khuyến cáo thực phẩm**
- **Actor:** AI System (tự động)
- **Trigger:** Khi user login hoặc mở dashboard
- **Flow chính:**
  1. Lấy UserProfile: goals, constraints, preferences
  2. Lấy NutritionLog tuần qua → analyze patterns
  3. Lấy MealPlan planned → kiểm tra nhu cầu
  4. Gọi build_user_preference_profile():
     - Build health profile dựa trên: age, weight, diseases, allergies
     - Build goal profile dựa trên: target_calories, health_goals
     - Lưu vào PersonalizationData
  5. Query AIRecommendation theo:
     - account_id = current user
     - recommendation_type = 'FOOD' hoặc 'MEAL'
  6. Nếu không có recommendation mới:
     - Gọi Gemini API:
       - Input: user profile + recent nutrition + upcoming plans
       - Output: JSON list với recommended foods + reasoning
     - Lưu AIRecommendation records
  7. Trả về danh sách recommendation
- **Output:** Danh sách 3-5 AIRecommendation:
  ```json
  [
    { 
      food_name: "Cá hồi",
      reason: "Giàu omega-3, giúp sức khỏe tim mạch",
      confidence: 0.92,
      health_score: 8.5
    },
    ...
  ]
  ```

**Usecase: UC-AI-RECOMMEND-002 - Sinh công thức nấu ăn**
- **Actor:** User (nhắc tới "công thức", "nấu ăn")
- **Trigger:** Chat message hoặc menu "Công thức"
- **Flow chính:**
  1. Lấy user constraints: bệnh, dị ứng, health_goals
  2. Lấy trending foods/ingredients tuần qua
  3. Gọi Gemini API:
     - Prompt: "Hãy sinh 1 công thức nấu ăn cho người {health_goals}, tránh {constraints}. Sử dụng ingredients: {trending_foods}. Trả về JSON: { name, ingredients, steps, calories, protein, carbs, fat, time_to_cook }"
  4. Parse JSON response
  5. Tính confidence score:
     - Base: 0.8
     - +0.1 nếu tất cả ingredients có sẵn trong Food DB
     - +0.05 nếu macro match với target
  6. Nếu confidence >= 0.85 → auto-save recipe (UC-RECIPE-AUTO-SAVE-004)
- **Output:**
  ```json
  {
    name: "Cơm hến nấu ẩm thực",
    ingredients: [...],
    steps: [...],
    calories: 420,
    protein: 22,
    carbs: 48,
    fat: 12,
    time_to_cook: "25 phút",
    confidence: 0.88,
    auto_saved: true
  }
  ```

---

#### 3.3. Quản lý admin (Admin Panel)

**Usecase: UC-ADMIN-001 - Đăng nhập admin**
- **Actor:** Admin
- **Trigger:** Truy cập `/admin-panel/login/`
- **Flow chính:**
  1. Hiển thị form login (username, password)
  2. Submit form → API xác minh
  3. Kiểm tra Account với role='admin'
  4. Nếu hợp lệ → tạo session admin, redirect `/admin-panel/`
  5. Nếu không → hiển thị lỗi
- **Output:** Admin dashboard hoặc lỗi login

**Usecase: UC-ADMIN-002 - Quản lý dữ liệu (CRUD)**
- **Actor:** Admin
- **Trigger:** Click vào menu "Quản lý" → chọn model (Food, User, Recipe, ...)
- **Flow chính:**
  1. Load trang admin data manager
  2. Hiển thị danh sách models: Food, Account, Recipe, ...
  3. Khi chọn model (e.g., Food):
     - Tải và hiển thị bảng Foods (pagination)
     - Cung cấp nút: Create, Edit, Delete, Export CSV, Import CSV
  4. Create Food:
     - Form: name, category, calories, protein, carbs, fat
     - Submit → Create Food record
  5. Edit Food:
     - Load existing data
     - Form pre-filled
     - Submit → Update record
  6. Delete Food:
     - Confirm xác nhận
     - Delete record
  7. Export CSV:
     - Query all records
     - Convert to CSV format
     - Download file
  8. Import CSV:
     - Upload file
     - Parse CSV
     - Bulk create/update records
- **Output:** Admin panel with CRUD operations, CSV export/import

**Usecase: UC-ADMIN-003 - Xem thống kê hệ thống**
- **Actor:** Admin
- **Trigger:** Click vào menu "Thống kê"
- **Flow chính:**
  1. Tính toán:
     - Total users: count(Account)
     - Total foods: count(Food)
     - Total recipes: count(Recipe)
     - Avg rating: avg(Recipe.avg_rating)
     - Active users (logged in 7 ngày): count distinct(Account with NutritionLog in last 7 days)
  2. Group by date:
     - New users per day (last 30 days)
     - Nutrition logs per day (last 30 days)
     - Top 10 foods (by frequency in NutritionLog)
  3. Hiển thị dashboard với cards, charts
- **Output:** Admin statistics page với:
  - Summary cards (total users, foods, recipes)
  - Charts: user growth, activity, top foods
  - Tables: model counts, record samples

**Usecase: UC-ADMIN-004 - Xóa dữ liệu trùng lặp**
- **Actor:** Admin
- **Trigger:** Click "Xóa trùng lặp" từ data manager
- **Flow chính:**
  1. Tìm bản ghi trùng:
     - Cho model (e.g., Food):
       - Group by normalized_name
       - Tìm group có > 1 record
  2. Cho mỗi group:
     - Keep record với most recent updated_at
     - Merge data (combine fields)
     - Update references (Food FK trên Recipe, MealPlan)
     - Delete other records
  3. Hiển thị kết quả: "Xóa 5 bản ghi trùng"
- **Output:** Confirmation message + count of deleted records

---

#### 3.4. Hệ thống phân loại intent (Intent Classification)

**Usecase: UC-INTENT-001 - Phân loại ý định chat (NLU)**
- **Actor:** AI System
- **Trigger:** Gửi chat message
- **Flow chính:**
  1. Lấy user text: "Bữa sáng nên ăn gì để giảm cân?"
  2. Normalize:
     - Lowercase: "bữa sáng nên ăn gì để giảm cân?"
     - Remove diacritics: "bua sang nen an gi de giam can?"
  3. Tokenize: ["bua", "sang", "nen", "an", "gi", "de", "giam", "can"]
  4. Query IntentPattern từ DB:
     - Tìm pattern có similarity >= 0.8
     - Tính similarity: số từ overlap / tổng từ
     - Lưu confidence score
  5. Return Intent với confidence cao nhất
     - Nếu confidence < 0.5 → return None (intent không nhận diện)
- **Output:**
  ```json
  {
    intent: { id: 1, name: "WEIGHT_LOSS", topic: "health" },
    confidence: 0.92
  }
  ```

**Usecase: UC-INTENT-002 - Seed intent patterns**
- **Actor:** Admin/Developer
- **Trigger:** Chạy lệnh: `python tools/seeding/seed_data.py --patterns`
- **Flow chính:**
  1. Lấy INTENT_PATTERNS_DATA từ tools/seeding/seed_data_consolidated.py
  2. Mỗi pattern:
     - Normalize text
     - Tìm Intent tương ứng (lookup by name)
     - Tạo IntentPattern record: (pattern_text, intent_id, confidence)
  3. get_or_create() để tránh duplicate
  4. Hiển thị kết quả: "[OK] Seeded 24 intent patterns"
- **Output:** IntentPattern records được tạo

---

#### 3.5. Hệ thống tập hợp dữ liệu (Data Consolidation)

**Usecase: UC-DATA-CONSOLIDATE-001 - Tạo bản sao lưu dữ liệu (Backup)**
- **Actor:** Admin
- **Trigger:** Click "Backup dữ liệu"
- **Flow chính:**
  1. Export tất cả tables:
     - Food, Account, Recipe, MealPlan, NutritionLog, ...
  2. Format: JSON hoặc SQL
  3. Compress: zip file
  4. Save to: `/artifacts/backups/{date}_backup.zip`
  5. Download file
- **Output:** Backup file (.zip)

**Usecase: UC-DATA-CONSOLIDATE-002 - Tìm và xóa orphan records**
- **Actor:** System (tự động chạy hàng tuần)
- **Trigger:** Cron job hoặc manual trigger
- **Flow chính:**
  1. Tìm NutritionLog không có Food:
     - LEFT JOIN với Food
     - WHERE Food.id IS NULL
  2. Tìm MealPlan không có Food
  3. Tìm ChatMessage không có ChatSession
  4. Tìm MessageIntent không có Intent
  5. Xóa tất cả orphan records
  6. Log result: "Deleted 15 orphan records"
- **Output:** Cleanup result log

---

### D. CHỨC NĂNG TÍCH HỢP - INTEGRATION FEATURES

#### 4.1. Tích hợp API bên ngoài (External API Integration)

**Usecase: UC-API-SPOONACULAR-001 - Tìm thực phẩm từ Spoonacular**
- **Actor:** Food Search Service
- **Trigger:** Khi user tìm thực phẩm không có trong DB
- **Flow chính:**
  1. Call Spoonacular API: `/food/search?query=cá hồi`
  2. Nhận response:
     ```json
     {
       "results": [
         { "id": 123, "name": "Salmon", "calories": 280, ... }
       ]
     }
     ```
  3. Parse và normalize data
  4. Tạo/update Food record từ Spoonacular data:
     - name, calories, protein, carbs, fat
     - description: "Source: Spoonacular"
  5. Lưu vào DB
- **Output:** Food record từ external API

**Usecase: UC-API-GEMINI-001 - Gọi Gemini API cho AI chat**
- **Actor:** Chat Service
- **Trigger:** User gửi tin nhắn chat
- **Flow chính:**
  1. Build system prompt:
     - "Bạn là trợ lý dinh dưỡng cho người Việt"
     - User age: {age}, weight: {weight}, health_goals: {goals}
     - Constraints: {diseases}, {allergies}
  2. Build conversation history:
     - Lấy 10 messages gần nhất từ ChatMessage
     - Format: [{ role: 'user', content: '...' }, { role: 'assistant', content: '...' }, ...]
  3. Call Gemini API:
     ```python
     response = client.messages.create(
       model='gemini-1.5-flash',
       system=system_prompt,
       messages=messages
     )
     ```
  4. Parse response
  5. Lưu response vào ChatMessage
- **Output:** AI response text

---

### E. TÓM TẮT PHÂN LOẠI FEATURE

| Cấp độ | Feature | UC Count | Complexity |
|--------|---------|---------|-----------|
| **SMALL** | Authentication | 4 | Low |
| | Profile Management | 2 | Low |
| | Food Search | 3 | Medium-Low |
| | Nutrition Logging | 4 | Medium |
| | **Subtotal** | **13** | |
| **MEDIUM** | Meal Planning | 4 | Medium |
| | AI Chat | 4 | High |
| | Recipe Rating | 4 | Medium |
| | **Subtotal** | **12** | |
| **LARGE** | Dashboard | 3 | High |
| | AI Recommendations | 2 | Very High |
| | Admin Panel | 4 | Very High |
| | Intent Classification | 2 | High |
| | Data Consolidation | 2 | Medium |
| | **Subtotal** | **13** | |
| **INTEGRATION** | External APIs | 2 | High |
| | **Total** | **42** | |

---

## 3. CRITICAL ISSUES & STATUS (May 2026 Update)

### 🔴 P0 - MUST FIX IMMEDIATELY

#### Issue #1: Meal Plan Add - Account Auth Missing
```
Severity: CRITICAL
Status: BROKEN ❌
Endpoint: POST /api/meal-plan/add/
Location: app/features/user_panel/views.py:802-815

Problem:
  account = get_current_account(request)  # Can be None!
  MealPlan.objects.create(account=account, ...)  # account=NULL → invisible

Impact:
  - User creates meal plan → account=NULL in DB
  - meal_plans view: filter(account=user_account)
  - NULL ≠ user_account → Meal plan INVISIBLE to user
  - User data appears deleted but is in DB

FIX REQUIRED:
  ```python
  @require_http_methods(["POST"])
  def meal_plan_add(request):
    account = get_current_account(request)
    if not account:
      return JsonResponse({'error': 'Vui lòng đăng nhập'}, status=401)
    
    data = json.loads(request.body)
    food_id = data.get('food_id')
    date = data.get('date')
    servings = data.get('servings', 1)
    
    # Validate
    food = get_object_or_404(Food, id=food_id)
    
    # Create with account
    plan = MealPlan.objects.create(
      account=account,  # ← REQUIRED
      food=food,
      date=parse_date(date),
      servings=Decimal(servings)
    )
    
    return JsonResponse({'id': plan.id, 'success': True})
  ```
```

#### Issue #2: Nutrition Delete - No Account Verification (SECURITY)
```
Severity: CRITICAL
Status: SECURITY BREACH ❌
Endpoint: DELETE /api/nutrition/delete/{log_id}/
Location: app/features/user_panel/views.py:910

Problem:
  get_object_or_404(NutritionLog, id=log_id)
  # Missing account check! User A can delete User B's logs!

Impact:
  - User A can DELETE User B's nutrition logs
  - Data loss vulnerability (critical)
  - No audit trail of who deleted what
  - Violates data privacy regulations

FIX REQUIRED:
  ```python
  @require_http_methods(["DELETE"])
  def nutrition_delete(request, log_id):
    account = get_current_account(request)
    if not account:
      return JsonResponse({'error': 'Vui lòng đăng nhập'}, status=401)
    
    # MUST verify account ownership!
    log = get_object_or_404(
      NutritionLog,
      id=log_id,
      account=account  # ← Filter by account
    )
    
    log.delete()
    return JsonResponse({'success': True})
  ```
```

#### Issue #3: Nutrition Log - Allows NULL Account
```
Severity: CRITICAL
Status: BROKEN ❌
Endpoint: POST /api/nutrition/log/
Location: app/features/user_panel/views.py:890

Problem:
  account = get_current_account(request)  # Can be None!
  NutritionLog.objects.create(account=account, ...)

Impact:
  - Same as Issue #1: logs not visible after creation
  - User's nutrition tracking appears lost

FIX REQUIRED:
  Add null check at start of handler:
  ```python
  account = get_current_account(request)
  if not account:
    return JsonResponse({'error': 'Vui lòng đăng nhập'}, status=401)
  ```
```

#### Issue #4: Profile Save - No Account Check
```
Severity: CRITICAL
Status: BROKEN ❌
Endpoint: POST /api/profile/save/
Location: app/features/user_panel/views.py:1322

Problem:
  account = get_current_account(request)  # Can be None!
  prof = get_profile(account)  # Can fail silently

Impact:
  - Guest users can't save profile
  - New users can't set health goals
  - Recommendations fail without profile
  - No error message to user

FIX REQUIRED:
  ```python
  account = get_current_account(request)
  if not account:
    return JsonResponse({'error': 'Vui lòng đăng nhập'}, status=401)
  
  if not account.is_active:
    return JsonResponse({'error': 'Tài khoản đã bị khóa'}, status=403)
  ```
```

### 🟠 P1 - SHOULD FIX THIS WEEK

#### Issue #5: Food Search - No API Fallback
```
Severity: HIGH
Status: NOT IMPLEMENTED ❌
Feature: Food search with Spoonacular fallback
Location: app/features/user_panel/views.py:980

Problem:
  foods_search() only queries local DB
  No Spoonacular API fallback when DB results empty

Impact:
  - New users with empty Food DB can't find foods
  - Limited to 5K foods in DB (seed data limit)
  - UX: "Không tìm thấy" instead of exploring APIs

EXPECTED BEHAVIOR:
  Query "salmon" → DB empty → Call Spoonacular → Return API results

FIX REQUIRED:
  ```python
  @require_http_methods(["GET"])
  def foods_search(request):
    q = request.GET.get('q', '').strip()
    
    # Try local DB first
    foods = Food.objects.filter(
      name__icontains=q
    ).values('id', 'name', 'calories', 'protein', 'carbs', 'fat')[:20]
    
    # If no results, try Spoonacular
    if not foods:
      from app.services.external_apis import fetch_spoonacular_food
      foods = fetch_spoonacular_food(q, limit=10)
    
    return JsonResponse(list(foods), safe=False)
  ```
```

#### Issue #6: Chat Endpoint - Missing POST validation
```
Severity: MEDIUM
Status: WRONG METHOD ❌
Endpoint: POST /api/chat/send/
Location: app/features/user_panel/views.py:612

Problem:
  @csrf_exempt
  @require_POST  # ← Missing!
  def chat_send(request):

Impact:
  - Anyone can GET /api/chat/send/?message=...
  - CSRF not enforced
  - Parameter in URL → logged in browser history

FIX REQUIRED:
  Add @require_POST decorator to enforce POST-only
```

#### Issue #7: Recipe Generation - No Input Validation
```
Severity: MEDIUM
Status: ALLOWS GARBAGE ⚠️
Endpoint: POST /api/ai/generate-recipe/
Location: app/features/user_panel/views.py:1093

Problem:
  No max length check, no ingredient count limit
  User can send 1000+ ingredients → wastes Gemini quota

FIX REQUIRED:
  ```python
  recipe_name = data.get('recipe_name', '').strip()
  ingredients = data.get('ingredients', [])
  
  # Validate lengths
  if len(recipe_name) < 3 or len(recipe_name) > 100:
    return JsonResponse({'error': 'Tên công thức 3-100 ký tự'}, status=400)
  
  if len(ingredients) == 0 or len(ingredients) > 50:
    return JsonResponse({'error': 'Nguyên liệu: 1-50 item'}, status=400)
  
  # Validate each ingredient
  for ing in ingredients:
    if not isinstance(ing, str) or len(ing) > 50:
      return JsonResponse({'error': 'Nguyên liệu > 50 ký tự'}, status=400)
  ```
```

#### Issue #8: Shopping List - No Date Validation
```
Severity: MEDIUM
Status: ACCEPTS INVALID DATES ⚠️
Endpoint: POST /api/ai/generate-shopping-list/
Location: app/features/user_panel/views.py:1203

Problem:
  No check: date_start <= date_end
  User sends date_start > date_end → empty results, wasted API call

FIX REQUIRED:
  ```python
  if date_start and date_end:
    if date_start > date_end:
      return JsonResponse({
        'success': False,
        'error': 'Ngày bắt đầu phải <= ngày kết thúc'
      }, status=400)
  ```
```

#### Issue #9: Chat Cache - No TTL/Cleanup
```
Severity: MEDIUM
Status: DB BLOAT RISK ⚠️
Model: ChatResponseCache
Location: apps/chat/models.py

Problem:
  Cache entries never deleted
  After 1 year: ~365,000 entries → DB bloat → slow queries

FIX REQUIRED:
  Add cleanup command:
  ```python
  # management/commands/cleanup_old_cache.py
  from datetime import timedelta
  from django.utils import timezone
  
  cutoff = timezone.now() - timedelta(days=30)
  deleted, _ = ChatResponseCache.objects.filter(
    created_at__lt=cutoff
  ).delete()
  print(f"Deleted {deleted} old cache entries")
  
  # Schedule daily via cron:
  # 0 2 * * * cd /app && python manage.py cleanup_old_cache
  ```
```

### 🟡 P2 - NICE TO FIX (Lower Priority)

#### Issue #10: Auth Session - No Timeout
```
Severity: MEDIUM
Status: WEAK SECURITY ⚠️
Location: apps/users/views.py:_set_auth_session()

Problem:
  request.session['user_id'] = account.id
  # No session.set_expiry() call
  # Uses Django default: 2 weeks → too long

FIX RECOMMENDED:
  ```python
  request.session['user_id'] = account.id
  request.session.set_expiry(timedelta(hours=24))  # 24-hour timeout
  ```
```

#### Issue #11: Intent Patterns - Empty at Startup
```
Severity: MEDIUM
Status: LOW ACCURACY AT START ⚠️
Location: apps/chat/models.py Intent/Pattern

Problem:
  Intent classification needs pattern samples
  First-time startup: no chat history → intent detection fails

FIX RECOMMENDED:
  - Pre-seed Intent/Pattern tables on DB init
  - Add 50-100 common health/nutrition patterns
  - See: tools/seeding/seed_data_consolidated.py
```

---

## 4. NEW USE CASES - GEMINI INTEGRATION & AI FEATURES (May 2026)

### UC-MEAL-PLAN-AI-001: Generate Meal Plan with Gemini

```
Actor: User (logged in)
Endpoint: POST /api/ai/generate-meal-plan/
Trigger: Click "Tạo thực đơn AI"

FLOW:
1. User fills form:
   - Days: 7 (default)
   - Calories: 2000 (from profile)
   - Preferences: "Ít béo", "Không nước ngoài"
   - Health goals: "Giảm cân", "Cơ bắp"

2. Backend validation:
   - days: 1-30
   - calories: 1500-3500
   - preferences: max 5

3. Build Gemini prompt:
   "Hãy tạo kế hoạch ăn {days} ngày cho:
   - Mục tiêu: {goals}
   - Calo mỗi ngày: {calories}
   - Ưu tiên: {preferences}
   - Người dùng: {age} tuổi, {weight} kg
   
   Trả về JSON:
   {
     plans: [
       {
         date: "2026-05-07",
         breakfast: { name: "...", calories: 400 },
         lunch: { name: "...", calories: 700 },
         dinner: { name: "...", calories: 700 },
         snacks: { name: "...", calories: 200 }
       }
     ]
   }"

4. Call Gemini API:
   response = gemini_client.generate_content(prompt)

5. Parse JSON response:
   - Extract meal suggestions
   - Look up food IDs from Food DB
   - Calculate total nutrition

6. Save MealPlan records:
   - Create MealPlan per food per day
   - Set source='ai_generated'
   - Set confidence_score

7. Return:
   {
     id: 123,
     days: 7,
     meals_count: 28,
     success: true
   }

ERROR HANDLING:
- Gemini API timeout → use cached template meal plan
- JSON parse error → return error + ask user to retry
- No matching foods → create with Gemini-provided names only
```

### UC-RECIPE-GENERATE-001: Generate Recipe with Gemini

```
Actor: User
Endpoint: POST /api/ai/generate-recipe/
Trigger: Click "Tạo công thức"

INPUT:
{
  recipe_name: "Cá hồi nướng lemon",
  ingredients: ["cá hồi", "lemon", "dầu olive"],
  servings: 4,
  health_goals: "giảm cân"
}

VALIDATION:
- recipe_name: 3-100 chars
- ingredients: 1-50 items, each 1-50 chars
- servings: 1-20

GEMINI PROMPT:
"Tạo công thức {recipe_name} cho {servings} người
Nguyên liệu: {ingredients}
Mục tiêu sức khoẻ: {health_goals}

Trả về JSON:
{
  recipe: {
    name: '...',
    servings: 4,
    prep_time: '15 phút',
    cook_time: '25 phút',
    difficulty: 'Dễ',
    ingredients: [
      { name: 'cá hồi', amount: '600g' },
      { name: 'lemon', amount: '2' }
    ],
    instructions: [
      'Bước 1: ...',
      'Bước 2: ...'
    ],
    nutrition: {
      calories: 350,
      protein: 40,
      fat: 15,
      carbs: 5
    },
    tips: ['...', '...']
  }
}"

FLOW:
1. Validate inputs
2. Call Gemini API
3. Parse JSON response
4. Create Recipe record:
   - name, servings, difficulty
   - prep_time, cook_time
   - instructions (joined text)
   - nutrition_per_serving

5. Create RecipeIngredient records:
   - For each ingredient in response:
     - Try to find Food by name
     - If not found, create dummy Food
     - Create RecipeIngredient link

6. Return:
   {
     id: 456,
     name: 'Cá hồi nướng lemon',
     prep_time: '15 phút',
     cook_time: '25 phút',
     calories_per_serving: 350,
     success: true
   }

CACHING:
- Store generated recipes in Recipe model
- Avoid regenerating same recipe within 7 days
- Cache key: hash(recipe_name + sorted(ingredients))
```

### UC-SHOPPING-LIST-GENERATE-001: Generate Shopping List with Gemini

```
Actor: User
Endpoint: POST /api/ai/generate-shopping-list/
Trigger: Click "Tạo danh sách mua"

INPUT:
{
  meal_plan_id: 123,  # optional
  date_start: "2026-05-07",
  date_end: "2026-05-13",
  budget: 500000  # VND, optional
}

FLOW:
1. Fetch meal plans in date range:
   - If meal_plan_id: use that plan
   - Else: use user's meal plans for date range

2. Aggregate ingredients:
   {
     "cá hồi": { amount: 1200, unit: "g" },
     "lemon": { amount: 5, unit: "quả" },
     "dầu olive": { amount: 300, unit: "ml" }
   }

3. Query ingredient prices:
   - For each ingredient:
     - Find latest IngredientPrice from WinMart
     - Get price_per_unit
     - Calculate total_cost = amount * price_per_unit

4. Build Gemini prompt:
   "Tạo danh sách mua sắm cho:
   Nguyên liệu:
   - cá hồi 1200g
   - lemon 5 quả
   - dầu olive 300ml
   
   Budget: 500,000 VND
   Cửa hàng: WinMart
   
   Trả về JSON:
   {
     items: [
       { item: 'cá hồi', qty: '1kg', price: 350000, store: 'WinMart' },
       { item: 'lemon', qty: '1kg (5 quả)', price: 25000, store: 'WinMart' }
     ],
     total: 375000,
     under_budget: true,
     notes: ['...']
   }"

5. Call Gemini API
6. Parse response
7. Create ShoppingList record
8. Create ShoppingListItem for each item

OUTPUT:
{
  id: 789,
  total: 375000,
  items_count: 10,
  under_budget: true,
  success: true
}

ERROR HANDLING:
- No meal plans in date range → error
- date_start > date_end → 400 error
- Ingredient prices missing → use Gemini estimate
- Budget exceeded → suggest alternatives
```

### UC-RECIPE-RATE-001: Rate & Save Recipe

```
Actor: User
Endpoint: POST /api/recipe/rate/
Trigger: User clicks "★★★★☆ Ngon!" on recipe

INPUT:
{
  recipe_id: 456,
  rating: 4,  # 1-5
  comment: "Rất ngon, dễ nấu!",
  would_cook_again: true
}

VALIDATION:
- recipe_id: exists in Recipe table
- rating: 1-5
- comment: max 500 chars

FLOW:
1. Check if user already rated:
   - rating = RecipeRating.objects.filter(
       recipe_id=456,
       account=user_account
     ).first()
   - If exists: update instead of create

2. Create/Update RecipeRating:
   {
     recipe_id: 456,
     account_id: user_id,
     rating: 4,
     comment: "Rất ngon, dễ nấu!",
     would_cook_again: true,
     rated_at: now()
   }

3. Update Recipe.avg_rating:
   - avg_rating = RecipeRating.objects.filter(
       recipe_id=456
     ).aggregate(Avg('rating'))['rating__avg']

4. Create PersonalizationData entry:
   - Learn user preference: "Cá hồi + lemon = 4/5"

OUTPUT:
{
  id: 999,
  rating: 4,
  avg_rating: 3.8,  # updated
  total_ratings: 12,
  success: true
}

RECOMMENDATION IMPACT:
- High-rated recipes recommended more often
- If rating >= 4 → boost similar recipes
- If rating <= 2 → avoid similar recipes
```

---

## 5. CRAWLER & PRICE MANAGEMENT (WinMart Integration)

### UC-ADMIN-CRAWL-WINMART-001: Crawl WinMart Prices

```
Actor: Admin
Trigger: Manual or Scheduled (daily at 2 AM)
Command: python manage.py crawl_winmart --limit-categories 50

FLOW:
1. Connect to WinMart API:
   - BASE_URL: "https://api.winmart.vn/v1/"
   - Categories endpoint: "/categories/"

2. Fetch all categories:
   - Paginate: 50 per page
   - Extract: category_id, category_name

3. For each category:
   - Fetch products:
     - Endpoint: "/categories/{id}/products"
     - Parse API response:
       {
         "id": 1234,
         "name": "Cá hồi tươi",
         "salePrice": 350000,
         "price": 400000,
         "retailPrice": 420000,
         "unit": "kg"
       }

4. Parse price function:
   - Remove currency symbols: "350.000₫" → 350000
   - Collect candidates: [salePrice, price, retailPrice]
   - Filter valid (> 0)
   - Choose: min(candidates) to find best price

5. Create/Update records:
   - Find or create Food by name
   - Create IngredientPrice:
     {
       food: food_obj,
       store: 'WinMart',
       price_per_unit: 350000,
       unit: 'kg',
       crawled_at: now()
     }

6. Deduplicate:
   - IngredientPrice.objects.filter(
       food=food,
       store='WinMart',
       crawled_at__date=today
     ).delete()  # Keep only latest

OUTPUT:
[OK] Crawled 50 categories
[OK] Found 2,341 products
[OK] Created 1,821 IngredientPrice records
[OK] Updated 412 existing prices
[OK] Crawl complete (2m 15s)

LOGS SAVED TO:
- artifacts/crawl_winmart_2026-05-07.log
```

### UC-ADMIN-VIEW-PRICES-001: Admin View Ingredient Prices

```
Actor: Admin
Endpoint: GET /admin-panel/prices/?search=cá
Trigger: Admin clicks "Giá nguyên liệu"

FLOW:
1. Get search query:
   - q = "cá"
   - Paginate: 50 per page

2. Query IngredientPrice:
   - JOIN with Food
   - WHERE Food.name LIKE '%cá%'
   - ORDER BY crawled_at DESC
   - LIMIT 50

3. Aggregate by food:
   - For each food:
     - Latest price from each store
     - Price trend (7 days)
     - Avg price across stores

4. Render table:
   | Food | Store | Current Price | Avg (7d) | Trend | Updated |
   |------|-------|--------------|---------|-------|---------|
   | Cá hồi | WinMart | 350,000 | 345,000 | ↓ | 2h ago |
   | Cá hồi | Lotte | 380,000 | 375,000 | → | 5h ago |

OUTPUT:
- Foods list with pricing data
- Price comparison across stores
- Last update timestamp
```

---

## 6. UPDATED SUMMARY (May 20, 2026)

### Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Authentication | ✓ Complete | Need to add timeout (Issue #10) |
| Food Search | ⚠️ Partial | Missing Spoonacular fallback (Issue #5) |
| Nutrition Logging | ❌ Broken | NULL account issue (Issue #3) |
| Meal Planning | ❌ Broken | NULL account issue (Issue #1) |
| Profile Management | ❌ Broken | Missing account check (Issue #4) |
| AI Chat | ✓ Complete | Works with Gemini, cache cleanup pending (Issue #9) |
| Recipe Generation | ⚠️ Partial | No input validation (Issue #7) |
| Shopping List | ⚠️ Partial | No date validation (Issue #8) |
| Recipe Rating | ✓ Complete | Works, saves preferences |
| Dashboard | ✓ Complete | Loads user data |
| Admin Panel | ✓ Complete | CRUD operations |
| WinMart Crawler | ✓ Complete | Parses prices correctly |
| Intent Classification | ⚠️ Partial | Works but needs pre-seeding (Issue #11) |
| Data Cleanup | ✓ Complete | Via admin commands |

### Critical Actions Required

1. **FIX Issue #1, #2, #3, #4** (All CRITICAL)
   - Add account validation to meal plans, nutrition logs, profile save
   - Add account filter to delete operations (security)
   - Timeline: **IMMEDIATE** (blocks core features)

2. **FIX Issue #5** (HIGH)
   - Add Spoonacular fallback to food search
   - Timeline: **This week**

3. **FIX Issues #6, #7, #8** (MEDIUM)
   - Add input validation to chat, recipe, shopping list
   - Timeline: **This week**

4. **FIX Issue #9** (MEDIUM)
   - Add cache cleanup cron job
   - Timeline: **This month**

### External APIs Status

| API | Status | Rate Limit | Cost |
|-----|--------|-----------|------|
| Gemini | ✓ Active | 10 req/min | $10/M tokens |
| Spoonacular | ⚠️ Available | 150/day | $3.99/month |
| WinMart | ✓ Working | Unlimited | Free |
| TheMealDB | ✓ Available | 100/hour | Free |

---

Cập nhật: May 20, 2026  
Phiên bản tài liệu: 2.1 (Smart Home Chef - AI Agent with Critical Issues)

---

## II. FLOW CHÍNH - END-TO-END WORKFLOWS

### Flow A: User Registration → Profile Setup → First Use

```
1. Guest lands on /
2. Click "Đăng ký" → UC-AUTH-001
3. Submit registration → Account created
4. Redirect to profile setup
5. Update profile: age, weight, health_goals → UC-PROFILE-002
6. System builds preference profile → build_user_preference_profile()
7. Dashboard shows recommendations
```

### Flow B: Daily Nutrition Tracking

```
1. User login (UC-AUTH-002)
2. View dashboard (UC-DASHBOARD-001)
3. Nutrition card shows: "Còn 500 kcal"
4. Click "Ghi dinh dưỡng"
5. Search food → UC-FOOD-SEARCH-001
6. Select food + servings → UC-NUTRITION-LOG-001
7. Log saved, dashboard updates
8. Repeat for other meals
9. End of day: dashboard shows macro summary
```

### Flow C: Meal Planning with AI

```
1. User chat: "Lập thực đơn 7 ngày"
2. Chat send → UC-CHAT-001
3. Gemini generates meal plan
4. Auto-create MealPlan → UC-CHAT-AUTO-PLAN
5. User views meal_plans.html (UC-MEAL-PLAN-001)
6. Calendar shows planned days
7. User can add/delete/modify plans (UC-MEAL-PLAN-002/003)
```

### Flow D: Recipe Discovery & Rating

```
1. User chat: "Công thức nấu ăn cho giảm cân"
2. Gemini generates recipe
3. Auto-save if high confidence → UC-RECIPE-AUTO-SAVE-004
4. Recipe displayed with rating UI
5. User submits 5-star rating + comment → UC-RECIPE-RATING-002
6. avg_rating updated
7. Recipe appears in top-rated list (UC-RECIPE-RATING-003)
```

---

## III. ACTORS & ROLES

### Primary Actors (Tác nhân chính)

| Actor | Role | Permissions | Primary Features |
|-------|------|-------------|-----------------|
| **Guest** | Khách | Read-only foods, register | UC-AUTH-001, UC-FOOD-SEARCH |
| **User** | Người dùng | CRUD nutrition, meals, chat | All user features |
| **Admin** | Quản trị viên | Full CRUD all models | UC-ADMIN-* |

### Secondary Actors (Tác nhân hỗ trợ)

| Actor | Role | Action |
|-------|------|--------|
| **Gemini API** | AI Assistant | Generate recommendations, recipes, answers |
| **Spoonacular API** | Food Database | Supply food nutrition data |
| **Database** | Data Store | Persist all records |
| **Scheduler** | Automation | Run daily digest, cleanup tasks |

---

## IV. DATA FLOW - VÀO/RA

### Core Data Models

```
Account (User identity)
├── UserProfile (Health info: age, weight, goals)
├── ChatSession (Chat history per user)
│   └── ChatMessage (Individual messages)
│       └── MessageIntent (Intent classification)
├── NutritionLog (Daily food intake)
├── MealPlan (Planned meals)
├── AIRecommendation (AI suggestions)
└── PersonalizationData (User preferences)

Food (Nutrition database)
├── Recipe (Cooking instructions)
├── RecipeRating (1-5 star ratings)

Intent (Chat intent types)
└── IntentPattern (NLU patterns)
```

### Data Dependencies

- **NutritionLog** → Food: FK to food_id
- **MealPlan** → Food: FK to food_id
- **RecipeRating** → Recipe, Account: FK
- **ChatMessage** → Account, ChatSession: FK
- **MessageIntent** → Intent, ChatMessage: FK
- **AIRecommendation** → Account, Food/Recipe: FK
- **PersonalizationData** → Account: FK

---

## V. THỐNG KÊ & METRICS

### System Capacity

- **Max Daily Active Users:** 1000 (SQLite limit: ~10K concurrent)
- **Max Foods in DB:** 10,000
- **Max Recipes:** 50,000
- **Max Users:** Unlimited (depends on server)

### Performance Targets

- **Dashboard load time:** < 2 seconds
- **Food search response:** < 1 second
- **Chat response:** < 5 seconds (Gemini API latency)
- **Nutrition log save:** < 500ms

### Success Metrics

- **User retention (7 days):** > 60%
- **Nutrition logging compliance:** > 50% (logged >= 3 meals/day)
- **AI satisfaction rating:** > 4.0/5.0
- **Chat intent accuracy:** > 90%

---

## VI. CÁC HẠNG MỤC CONSTRAINT & LIMITATION

### Business Constraints

- ✓ **Recommendation-only system** (no e-commerce, no ordering)
- ✓ No payment processing
- No shopping cart / checkout flow
- No delivery tracking
- No vendor management

### Technical Constraints

- SQLite database (not suitable for > 50K concurrent users)
- Python 3.13 + Django 5.x required
- Google Gemini API key required
- Spoonacular API key required
- Vietnamese language support (UTF-8)

### Data Constraints

- Max message length: 4000 characters (Gemini API limit)
- Max file upload (CSV): 10 MB
- Max chat history: 100 messages per session
- Recipe ingredients: max 50 items

---

## VII. TESTING STRATEGY

### Unit Tests

- `test_nutrition_log_creation()`: UC-NUTRITION-LOG-001
- `test_meal_plan_add()`: UC-MEAL-PLAN-002
- `test_recipe_rating_update()`: UC-RECIPE-RATING-002
- `test_food_search()`: UC-FOOD-SEARCH-001

### Integration Tests

- `test_chat_auto_create_meal_plan()`: UC-CHAT-AUTO-PLAN
- `test_gemini_api_integration()`: UC-API-GEMINI-001
- `test_spoonacular_api_integration()`: UC-API-SPOONACULAR-001

### E2E Tests

- `test_user_registration_to_nutrition_log()`: Flow B
- `test_meal_planning_with_ai()`: Flow C
- `test_recipe_discovery_and_rating()`: Flow D

---

## VIII. CHANGELOG

### Version 1.0 (Current - May 2026)

✓ Authentication system (register, login, logout)  
✓ Profile management (update health info)  
✓ Nutrition logging (CRUD meals, track macro)  
✓ Meal planning (calendar view, add/delete)  
✓ AI chat assistant (Gemini integration)  
✓ Food search (DB + Spoonacular API)  
✓ Recipe rating system (1-5 stars)  
✓ Intent classification (NLU with Vietnamese patterns)  
✓ Admin panel (CRUD models, statistics, CSV import/export)  
✓ Dashboard (daily summary, 7-day trend, streak counter)  

### Future Versions (v1.1+)

- [ ] Social features (share meals, follow users)
- [ ] Barcode scanning (quick food logging)
- [ ] Advanced analytics (macro trends, health insights)
- [ ] Mobile app (iOS/Android)
- [ ] Community recipes (user-submitted)
- [ ] Voice chat (Vietnamese speech-to-text)
- [ ] Meal prep guides (batch cooking tips)
- [ ] Workout integration (calories burned tracking)

---

## IX. REFERENCES

- [Database Schema](database-schema.md) — Toàn bộ table definitions
- [Architecture](architecture.md) — Hệ thống design & component interactions
- [Style Guide](style-guide.md) — Coding standards
- [AI Training Model](ai-training-model.md) — Intent classification details

---

**End of Document**

Created by: GitHub Copilot  
Last Updated: May 4, 2026  
Status: ✓ Complete & Ready for Production
