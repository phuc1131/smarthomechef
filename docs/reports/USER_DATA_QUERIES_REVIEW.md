# Kiểm Tra Mã Query Dữ Liệu Người Dùng

## 📊 Tóm tắt
Các hàm và đoạn mã phụ trách query/truy xuất dữ liệu từ bảng người dùng (Account, UserProfile, UserGoal, UserFeedback, v.v.) được phân bố trong nhiều file:

---

## 🔐 **1. MODELS & CƠ SỬ DỮ LIỆU**

### Vị trí: `apps/users/models.py`

#### **Account Model** (Tài khoản người dùng)
```python
class Account(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(max_length=255, unique=False)
    password_hash = models.TextField()
    role = models.CharField(max_length=20, default='user')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'users'
```
- **Vai trò**: Lưu thông tin xác thực cơ bản, role quyền hạn
- **Unique constraints**: `username`, `email`
- **Important**: Mật khẩu được hash (không plaintext)

#### **UserProfile Model** (Hồ sơ chi tiết)
```python
class UserProfile(models.Model):
    account = models.OneToOneField(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    activity_level = models.CharField(max_length=50, null=True, blank=True)
    bmi = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    daily_calorie_target = models.IntegerField(null=True, blank=True)
    health_goal = models.TextField(null=True, blank=True)
    medical_conditions = models.TextField(null=True, blank=True)
    dietary_preferences = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
```
- **Relationship**: 1-1 với Account (OneToOneField)
- **Lưu trữ**: Thông tin sức khỏe, mục tiêu, chỉ số tính toán

#### **UserGoal Model** (Mục tiêu người dùng)
```python
class UserGoal(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    goal_type = models.CharField(max_length=100, default='maintain')
    target_weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    daily_calorie_target = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'user_goals'
        unique_together = ('account', 'goal_type')
```
- **Relationship**: M-1 với Account (ForeignKey)
- **Constraint**: Một account không thể có 2 goal cùng loại
- **Dùng cho**: Tính toán khuyến nghị thực phẩm

#### **UserFeedback Model** (Phản hồi người dùng)
```python
class UserFeedback(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    food = models.ForeignKey('nutrition.Food', on_delete=models.CASCADE)
    rating = models.IntegerField(null=True, blank=True)
    liked = models.BooleanField(null=True, blank=True)
    feedback_type = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_feedback'
```
- **Relationship**: M-1 với Account và Food
- **Lưu trữ**: Đánh giá, like/dislike, feedback type
- **Dùng cho**: Cải thiện khuyến nghị (collaborative filtering)

#### **UserPreferenceProfile Model** (Sở thích cá nhân)
```python
class UserPreferenceProfile(models.Model):
    account = models.OneToOneField(Account, on_delete=models.CASCADE, primary_key=True)
    preferred_macros = models.JSONField(null=True, blank=True)
    preferred_categories = models.JSONField(null=True, blank=True)
    preferred_keywords = models.JSONField(null=True, blank=True)
    avoided_keywords = models.JSONField(null=True, blank=True)
    healthy_score = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unhealthy_score = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_preference_profiles'
```
- **Relationship**: 1-1 với Account
- **Format**: JSON fields để store complex preferences
- **Dùng cho**: Personalized recommendations

#### **UserBehaviorLog Model** (Lịch sử hành động)
```python
class UserBehaviorLog(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=50)
    target_type = models.CharField(max_length=50, null=True, blank=True)
    target_id = models.BigIntegerField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_behavior_log'
```
- **Lưu trữ**: Hành động người dùng (search, click, view, v.v.)
- **Flexible**: Có thể lưu metadata tuỳ ý

---

## 🔍 **2. QUERY FUNCTIONS - AUTHENTICATION**

### Vị trí: `app/views.py` và `apps/users/views.py`

#### **get_current_account(request)** ⭐ (CHÍNH)
```python
def get_current_account(request):
    """
    Lấy Account hiện tại từ session.
    - Query: Account.objects.get(id=user_id, is_active=True)
    - Return: Account object hoặc None
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        account = Account.objects.get(id=user_id, is_active=True)
        return account
    except Account.DoesNotExist:
        return None
```
- **Tác dụng**: Lấy user hiện tại từ session
- **Security**: Chỉ lấy account nếu is_active=True
- **Sử dụng**: Gần như mọi view đều cần

#### **auth_login(request)** - Query login
```python
# Query 1: Tìm account từ username hoặc email
account = Account.objects.filter(
    Q(username__iexact=username) | Q(email__iexact=username),
).first()

# Validation
if not account:
    return JsonResponse({'error': 'Account chưa tồn tại'}, status=404)
if not account.is_active:
    return JsonResponse({'error': 'Tài khoản bị khóa'}, status=403)
if not verify_account_password(account, password):
    return JsonResponse({'error': 'Mật khẩu sai'}, status=401)

# Sau khi thành công, set session
request.session['user_id'] = account.id
```
- **Query pattern**: Case-insensitive filter + Q object
- **Security**: Verify password hash, check is_active

#### **auth_register(request)** - Query register
```python
# Check username đã tồn tại?
if Account.objects.filter(username__iexact=username).exists():
    return JsonResponse({'error': 'Tên tài khoản đã tồn tại'}, status=400)

# Generate email duy nhất
email = f"{username.lower()}@local.smartchef"
suffix = 1
while Account.objects.filter(email=email).exists():
    suffix += 1
    email = f"{username.lower()}{suffix}@local.smartchef"

# Create account
account = Account.objects.create(
    username=username,
    email=email,
    password_hash=make_password(password),
    role='user',
    is_active=True,
)
```
- **Query pattern**: Check exists() trước create
- **Email handling**: Auto-generate email nếu conflict

#### **get_or_create_guest_account(request)**
```python
client_ip = get_client_ip(request)
guest_username = f"guest_{client_ip.replace('.', '_')}"

account, created = Account.objects.get_or_create(
    username=guest_username,
    defaults={
        'email': f"{guest_username}@local.smartchef",
        'password_hash': make_password('guest'),
        'role': 'guest',
        'is_active': True,
    }
)
return account
```
- **Tác dụng**: Tạo guest account dựa trên IP
- **Advantage**: Cho phép guest dùng mà không cần login

---

## 📋 **3. QUERY FUNCTIONS - USER PROFILE**

### Vị trí: `app/views.py`, `apps/users/views.py`

#### **get_profile(request_or_account)** ⭐
```python
def get_profile(request_or_account=None):
    if request_or_account is None:
        return None
    if hasattr(request_or_account, 'session'):
        account = get_current_account(request_or_account)
    else:
        account = request_or_account
    if not account:
        return None
    
    profile, _ = UserProfile.objects.get_or_create(
        account=account,
        defaults={'name': account.username},
    )
    return profile
```
- **Tác dụng**: Lấy hoặc tạo UserProfile cho account
- **Query**: OneToOne relationship query + get_or_create
- **Auto-create**: Nếu profile chưa tồn tại, auto tạo

#### **Admin Query - UserProfileAdmin** 
```python
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'account', 'age', 'gender', 'daily_calorie_target', 'updated_at')
    list_filter = ('gender', 'activity_level', 'updated_at')
    search_fields = ('name', 'account__username', 'account__email')
    # Query: UserProfile.objects.select_related('account').filter(...)
```
- **Search**: Có thể search qua account__username, account__email
- **Relationships**: select_related('account') để optimize

---

## 🍽️ **4. NUTRITION TRACKING - RELATED USER QUERIES**

### Vị trí: `app/views.py`, `app/features/user_panel/views.py`

#### **dashboard(request)** - Lấy dữ liệu hôm nay
```python
today = date.today().isoformat()

# Query: Tất cả nutrition log hôm nay
today_logs = NutritionLog.objects.filter(date=today)
today_calories = sum(float(l.total_calories or 0) for l in today_logs)
today_protein = sum(float(l.total_protein or 0) for l in today_logs)

# Query: Kiểm tra streak
streak = 0
check_date = date.today()
for _ in range(30):
    if NutritionLog.objects.filter(date=check_date.isoformat()).exists():
        streak += 1
        check_date -= timedelta(days=1)
    else:
        break

# Query: Random food suggestions
foods = list(Food.objects.all())
suggestions = random.sample(foods, min(4, len(foods)))

# Query: Profile để lấy calorie target
profile = get_profile(request)
calorie_target = profile.daily_calorie_target if profile else 2000
```
- **Pattern**: Filter by date, aggregation, random sampling
- **Performance concern**: Load ALL foods có thể heavy nếu DB lớn
- **Suggestion**: Cache random suggestions hoặc limit query

---

## 🎯 **5. RELATED DATA QUERIES**

### **UserGoal Queries**
```python
# Admin panel
@admin.register(UserGoal)
class UserGoalAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'goal_type', 'target_weight', 'daily_calorie_target', 'created_at')
    list_filter = ('goal_type', 'created_at')
    search_fields = ('account__username',)
    # Query: UserGoal.objects.select_related('account').filter(...)

# Get goal for a user
# goal = UserGoal.objects.filter(account=account, goal_type='weight_loss').first()
```

### **UserFeedback Queries**
```python
@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'food', 'rating', 'liked', 'created_at')
    list_filter = ('liked', 'created_at')
    search_fields = ('account__username', 'food__name')
    # Query: UserFeedback.objects.select_related('account', 'food').filter(...)

# Recommendation engine
# liked_foods = UserFeedback.objects.filter(account=account, liked=True).select_related('food')
```

### **UserBehaviorLog Queries**
```python
# Log user action
UserBehaviorLog.objects.create(
    account=account,
    action_type='search_food',
    target_type='food',
    target_id=food_id,
    metadata={'query': search_text}
)

# Query user actions
# logs = UserBehaviorLog.objects.filter(account=account, action_type='search_food')
```

---

## ⚠️ **6. POTENTIAL ISSUES & RECOMMENDATIONS**

### 🔴 **Issue 1: N+1 Query Problem**
```python
# BAD: N+1 query
foods = Food.objects.all()  # 1 query
for food in foods:
    print(food.category)  # N queries if category is ForeignKey

# GOOD: Use select_related/prefetch_related
foods = Food.objects.select_related('category').all()  # 1-2 queries
```

### 🔴 **Issue 2: Loading All Data**
```python
# BAD: Load tất cả foods
foods = list(Food.objects.all())

# GOOD: Limit và cache
foods = Food.objects.all()[:20]
# Hoặc cache trong Redis
```

### 🔴 **Issue 3: Missing Indexes**
```python
# Nên có index trên fields được filter thường xuyên:
# - Account.username, Account.email
# - UserProfile.account_id
# - NutritionLog.date, NutritionLog.account_id
# - UserBehaviorLog.account_id, UserBehaviorLog.created_at
```

### 🔴 **Issue 4: Case-Sensitive Query**
```python
# Case-insensitive query (GOOD)
account = Account.objects.filter(
    Q(username__iexact=username) | Q(email__iexact=username)
).first()

# Case-sensitive query (BAD - không khớp "User" vs "user")
account = Account.objects.filter(username=username).first()
```

---

## 📊 **7. SUMMARY TABLE**

| Query Function | Model | Pattern | Location | Used For |
|---|---|---|---|---|
| `get_current_account()` | Account | `.get(id=user_id, is_active=True)` | apps/users/views.py | Get logged-in user |
| `auth_login()` | Account | `.filter(Q(username) \| Q(email)).first()` | app/views.py | Login authentication |
| `auth_register()` | Account | `.filter().exists()`, `.create()` | app/views.py | Registration |
| `get_or_create_guest_account()` | Account | `.get_or_create(username=guest_*)` | app/views.py | Guest account |
| `get_profile()` | UserProfile | `.get_or_create(account=account)` | app/views.py | Get user profile |
| Dashboard nutrition | NutritionLog | `.filter(date=today)` | app/views.py | Daily nutrition |
| Admin Account | Account | `.filter().search_fields()` | app/admin.py | Admin panel |
| Admin UserProfile | UserProfile | `.select_related('account')` | app/admin.py | Admin panel |
| Admin UserGoal | UserGoal | `.filter(account=account)` | app/admin.py | Admin panel |

---

## ✅ **8. BEST PRACTICES CHECKLIST**

- [x] Sử dụng `.get_or_create()` để tránh race condition
- [x] Sử dụng case-insensitive `.iexact` cho username/email
- [x] Check `is_active` trước khi return Account
- [x] Verify password hash, không bao giờ plaintext
- [x] Sử dụng session để lưu user_id
- [x] Sử dụng `.select_related()` cho OneToOne/ForeignKey
- [ ] **TODO**: Thêm indexes trên frequently-queried fields
- [ ] **TODO**: Implement caching cho frequently-accessed data
- [ ] **TODO**: Optimize Food.objects.all() queries với limit/pagination
- [ ] **TODO**: Add logging để track user queries

---

## 📚 **References**

- Models: `apps/users/models.py`
- Auth Functions: `app/views.py`, `apps/users/views.py`
- Admin Config: `app/admin.py`
- Related Models: `app/models.py`

