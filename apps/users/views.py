import json
import random
import csv
import re
import string
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from datetime import date, datetime, timedelta
from uuid import uuid4
from urllib.parse import urlencode
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.db import DatabaseError, transaction, connection
from django.forms import modelform_factory
from django.core.paginator import Paginator
from django.urls import reverse
from django.core.exceptions import ValidationError

from apps.users.auth_backend import AllAuthAccountBridge
from apps.users.auth_utils import verify_account_password
from apps.users.forms import PasswordChangeForm, PasswordResetForm
from apps.users.models import (
    Account,
    UserGoal,
    UserFeedback,
    UserProfile,
    UserPreferenceProfile,
    Disease,
)
from apps.nutrition.models import (
    Food,
    FoodIngredient,
    Ingredient,
    NutritionLog,
    DailyNutritionSummary,
)
from apps.meal_plans.models import MealPlan
from apps.chat.models import (
    ChatMessage,
    ChatSession,
    Intent,
    IntentEmbedding,
    MessageIntent,
    Pattern,
    ChatSummary,
)
from apps.core_models.models import AIRecommendation
from apps.meal_plans.constants import (
    get_meal_type_configs,
    get_meal_type_choices,
    get_meal_type_color_map,
)
from services.external_apis import (
    AI_AVAILABLE,
    call_gemini_with_debug,
    get_spoonacular_last_error,
    parse_and_save_spoonacular_food,
)
from services.chat_text_service import (
    normalize_chat_text as service_normalize_chat_text,
    tokenize_chat_text as service_tokenize_chat_text,
)
from services.health_feedback_service import (
    append_health_feedback as service_append_health_feedback,
    build_health_feedback as service_build_health_feedback,
)
from services.food_data_service import (
    get_or_fetch_food as service_get_or_fetch_food,
    get_or_fetch_ingredient as service_get_or_fetch_ingredient,
)


def get_meal_type_configs(active_only=True):
    """Get meal type configurations - uses constants instead of database"""
    from apps.meal_plans.constants import get_meal_type_configs as _get_configs
    return _get_configs(active_only=active_only)


def get_default_meal_type(active_only=True):
    choices = get_meal_type_choices(active_only=active_only)
    return choices[0][0] if choices else ''


def get_current_account(request):
    """
    Lấy Account hiện tại từ session.
    """
    user_id = request.session.get('user_id')
    if not user_id:
        if getattr(request, 'user', None) and request.user.is_authenticated:
            try:
                account = AllAuthAccountBridge.sync_account_from_user(request.user)
                request.session['user_id'] = account.id
                request.session['user_name'] = account.username
                request.session['user_email'] = account.email
                request.session.setdefault('user_avatar', '')
                return account
            except Exception:
                return None
        return None
    try:
        account = Account.objects.get(id=user_id, is_active=True)
        return account
    except Account.DoesNotExist:
        if getattr(request, 'user', None) and request.user.is_authenticated:
            try:
                account = AllAuthAccountBridge.sync_account_from_user(request.user)
                request.session['user_id'] = account.id
                request.session['user_name'] = account.username
                request.session['user_email'] = account.email
                request.session.setdefault('user_avatar', '')
                return account
            except Exception:
                return None
        return None


def get_profile(request):
    """Lấy hoặc tạo UserProfile cho account hiện tại."""
    account = get_current_account(request)
    if not account:
        return None
    profile, _ = UserProfile.objects.get_or_create(
        account=account,
        defaults={'name': account.username},
    )
    return profile


def is_admin_actor(request):
    """
    Kiểm tra xem user hiện tại có phải admin không.
    """
    account = get_current_account(request)
    if not account:
        return False
    role = (account.role or '').strip().lower()
    return role == 'admin' and account.is_active


def _set_auth_session(request, user_id, name, email, avatar=''):
    """
    Lưu thông tin xác thực vào session sau khi đăng nhập thành công.
    
    Tham số:
    - request: Django request object
    - user_id: ID của Account vừa đăng nhập
    - name: Tên hiển thị
    - email: Email
    - avatar: URL avatar (tùy chọn)
    
    GHI NHỚ:
    - Gọi này sau khi verify password + check is_active
    - Session cookie sẽ tồn tại trên client cho đến khi logout
    - user_id dùng để tra cứu Account ở mỗi request
    - avatar có thể để '' nếu user chưa có
    """
    request.session['user_id'] = user_id
    request.session['user_name'] = name
    request.session['user_email'] = email
    request.session['user_avatar'] = avatar


def login_page(request):
    """
    Hiển thị trang đăng nhập.
    
    Logic:
    - Nếu đã logged in (có session['user_id']), redirect sang dashboard
    - Nếu chưa, render login.html template
    """
    if request.session.get('user_id') or request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'user/login.html', {'active': 'auth'})


def register_page(request):
    """
    Hiển thị trang đăng ký.
    
    Logic:
    - Nếu đã logged in, redirect sang dashboard
    - Nếu chưa, render register.html template
    """
    if request.session.get('user_id') or request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'user/register.html', {'active': 'auth'})


@csrf_exempt
@require_POST
def auth_register(request):
    data = json.loads(request.body or '{}')
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if len(username) < 3:
        return JsonResponse({'ok': False, 'error': 'Tên tài khoản tối thiểu 3 ký tự.'}, status=400)
    if len(password) < 8:
        return JsonResponse({'ok': False, 'error': 'Mật khẩu tối thiểu 8 ký tự.'}, status=400)
    if Account.objects.filter(username__iexact=username).exists():
        return JsonResponse({'ok': False, 'error': 'Tên tài khoản đã tồn tại.'}, status=400)

    email = f"{username.lower()}@local.smartchef"
    suffix = 1
    while Account.objects.filter(email=email).exists():
        suffix += 1
        email = f"{username.lower()}{suffix}@local.smartchef"

    account = Account.objects.create(
        username=username,
        email=email,
        password_hash=make_password(password),
        role='user',
        is_active=True,
    )
    request.session['user_id'] = account.id
    request.session['user_name'] = account.username
    request.session['user_email'] = account.email
    return JsonResponse({'ok': True})


@csrf_exempt
@require_POST
def auth_login(request):
    data = json.loads(request.body or '{}')
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return JsonResponse({'ok': False, 'error': 'Thiếu tên tài khoản hoặc mật khẩu.'}, status=400)

    account = Account.objects.filter(
        Q(username__iexact=username) | Q(email__iexact=username),
    ).first()
    if not account:
        return JsonResponse({'ok': False, 'error': 'Tài khoản chưa tồn tại. Hãy đăng ký trước.'}, status=404)
    if not account.is_active:
        return JsonResponse({'ok': False, 'error': 'Tài khoản đã bị khóa hoặc chưa được kích hoạt.'}, status=403)
    if not verify_account_password(account, password):
        return JsonResponse({'ok': False, 'error': 'Mật khẩu không đúng.'}, status=401)

    role = (account.role or '').strip().lower()
    if role == 'admin':
        return JsonResponse({'ok': False, 'error': 'Tài khoản admin vui lòng đăng nhập tại /admin-panel/login/'}, status=403)

    request.session['user_id'] = account.id
    request.session['user_name'] = account.username
    request.session['user_email'] = account.email
    return JsonResponse({'ok': True})


@csrf_exempt
@require_POST
def auth_logout(request):
    try:
        django_logout(request)
    except Exception:
        pass
    request.session.flush()
    return JsonResponse({'ok': True})


@csrf_exempt
def auth_me(request):
    """Trả về trạng thái đăng nhập hiện tại từ session hoặc allauth."""
    account = get_current_account(request)
    if account:
        auth_method = 'oauth' if getattr(request, 'user', None) and request.user.is_authenticated and not request.session.get('user_id') else 'session'
        return JsonResponse({
            'logged_in': True,
            'name': request.session.get('user_name', account.username),
            'email': request.session.get('user_email', account.email),
            'avatar': request.session.get('user_avatar', ''),
            'auth_method': auth_method,
        })
    return JsonResponse({'logged_in': False})


@csrf_exempt
def accounts_list(request):
    """API để admin xem danh sách tất cả tài khoản."""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

    try:
        current_account = Account.objects.get(id=user_id)
        if current_account.role != 'admin':
            return JsonResponse({'error': 'Không có quyền truy cập'}, status=403)
    except Account.DoesNotExist:
        return JsonResponse({'error': 'Tài khoản không tồn tại'}, status=404)

    accounts = Account.objects.all().order_by('id')
    accounts_data = []

    for account in accounts:
        accounts_data.append({
            'id': account.id,
            'username': account.username,
            'email': account.email,
            'role': account.role,
            'is_active': account.is_active,
            'created_at': account.created_at.isoformat() if account.created_at else None,
        })

    return JsonResponse({'ok': True, 'total': len(accounts_data), 'accounts': accounts_data})


@csrf_exempt
def account_detail(request, account_id):
    """API để xem chi tiết một tài khoản cụ thể."""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

    try:
        current_account = Account.objects.get(id=user_id)
        if current_account.role != 'admin' and current_account.id != account_id:
            return JsonResponse({'error': 'Không có quyền truy cập'}, status=403)
    except Account.DoesNotExist:
        return JsonResponse({'error': 'Tài khoản không tồn tại'}, status=404)

    try:
        account = Account.objects.get(id=account_id)
    except Account.DoesNotExist:
        return JsonResponse({'error': 'Tài khoản không tồn tại'}, status=404)

    return JsonResponse({
        'ok': True,
        'account': {
            'id': account.id,
            'username': account.username,
            'email': account.email,
            'role': account.role,
            'is_active': account.is_active,
            'created_at': account.created_at.isoformat() if account.created_at else None,
        }
    })


def profile(request):
    account = get_current_account(request)
    prof = get_profile(request)
    # Allow logged-in users (including OAuth/allauth users) to delete their account.
    # If we have an Account object, respect guest_* usernames. If not, but the
    # request.user is authenticated (allauth), allow deletion UI so the user can
    # confirm via the modal and the server-side will sync/delete accordingly.
    if account:
        can_delete_account = not str(account.username or '').strip().lower().startswith('guest_')
    else:
        # If django user is authenticated (allauth flow), allow delete UI
        can_delete_account = bool(getattr(request, 'user', None) and request.user.is_authenticated)
    bmi_display = None
    weight_status = None
    if prof and prof.height and prof.weight and float(prof.height) > 0:
        height_m = float(prof.height) / 100.0
        bmi_val = float(prof.weight) / (height_m * height_m)
        bmi_display = round(bmi_val, 1)
        if bmi_val < 18.5:
            weight_status = 'Thiếu cân'
        elif bmi_val < 23:
            weight_status = 'Bình thường'
        elif bmi_val < 25:
            weight_status = 'Thừa cân'
        else:
            weight_status = 'Béo phì'

    # Require password confirmation for ALL users when deleting accounts.
    # If an Account does not yet have a password set (common for OAuth-only
    # signups), instruct the user to set a password first via the change
    # password flow before attempting deletion.
    delete_requires_password = True

    return render(request, 'user/profile.html', {
        'profile': prof,
        'profile_bmi_display': bmi_display,
        'profile_weight_status': weight_status,
        'account': account,
        'can_delete_account': can_delete_account,
        'delete_requires_password': delete_requires_password,
        'active': 'profile',
    })


@csrf_exempt
@require_POST
def account_delete(request):
    account = get_current_account(request)
    if not account:
        return JsonResponse({'ok': False, 'error': 'Bạn cần đăng nhập để xóa tài khoản.'}, status=401)
    if str(account.username or '').strip().lower().startswith('guest_'):
        return JsonResponse({'ok': False, 'error': 'Tài khoản khách không thể xóa.'}, status=403)

    data = json.loads(request.body or '{}')
    password = (data.get('password') or '').strip()

    # Always require password confirmation for deletion.
    # If the Account has no password (e.g. OAuth-only), instruct the user
    # to set a password first via the change-password flow.
    stored_pw = (getattr(account, 'password_hash', '') or '').strip()
    if not stored_pw:
        return JsonResponse({'ok': False, 'error': 'Tài khoản chưa có mật khẩu. Vui lòng đặt mật khẩu trước khi xóa tài khoản.'}, status=400)

    if not verify_account_password(account, password):
        return JsonResponse({'ok': False, 'error': 'Mật khẩu xác nhận không đúng.'}, status=400)

    try:
        with transaction.atomic():
            existing_tables = set(connection.introspection.table_names())

            def delete_related_rows(model, selector_sql, selector_params):
                table_name = model._meta.db_table
                pk_column = model._meta.pk.column

                for related in model._meta.related_objects:
                    related_model = related.related_model
                    related_table = related_model._meta.db_table
                    if related_table not in existing_tables:
                        continue
                    if related.on_delete.__name__ != 'CASCADE':
                        continue
                    fk_column = related.field.column
                    child_selector_sql = (
                        f'"{fk_column}" IN ('
                        f'SELECT "{pk_column}" FROM "{table_name}" WHERE {selector_sql}'
                        f')'
                    )
                    delete_related_rows(related_model, child_selector_sql, selector_params)

                if table_name in existing_tables:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            f'DELETE FROM "{table_name}" WHERE {selector_sql}',
                            selector_params,
                        )

            delete_related_rows(Account, '"id" = %s', [account.id])

            if getattr(request, 'user', None) and request.user.is_authenticated:
                try:
                    request.user.delete()
                except Exception:
                    pass

            django_logout(request)
            request.session.flush()
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': f'Không thể xóa tài khoản: {exc}'}, status=500)

    return JsonResponse({'ok': True})


@csrf_exempt
@require_POST
def profile_save(request):
    data = json.loads(request.body)
    prof = get_profile(request)
    fields = {
        'name': data.get('name', ''),
        'age': data.get('age') or None,
        'weight': data.get('weight') or None,
        'height': data.get('height') or None,
        'gender': data.get('gender', ''),
        'health_goal': data.get('health_goal', ''),
        'medical_conditions': data.get('medical_conditions', ''),
        'dietary_preferences': data.get('dietary_preferences', ''),
        'activity_level': data.get('activity_level', ''),
        'daily_calorie_target': data.get('daily_calorie_target') or None,
    }
    if prof:
        for k, v in fields.items():
            setattr(prof, k, v)
        prof.save()
    else:
        prof = UserProfile.objects.create(**fields)
    return JsonResponse({'ok': True, 'name': prof.name})


@login_required
def oauth_callback(request):
    """
    Callback after successful OAuth login
    Syncs django User with Account model
    """
    try:
        account = AllAuthAccountBridge.sync_account_from_user(request.user)
        request.session['user_id'] = account.id
        request.session['user_name'] = account.username
        request.session['user_email'] = account.email
        return redirect('/')
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return redirect('/dang-nhap/?error=oauth_sync_failed')


@login_required
def oauth_google_success(request):
    """Handle Google OAuth success"""
    return oauth_callback(request)


def change_password(request):
    """Display password change form"""
    account = get_current_account(request)
    if not account or not account.password_hash:
        # Allow OAuth users (no password_hash) to set an initial password here.
        if not account:
            messages.error(request, 'Bạn cần đăng nhập để thay đổi mật khẩu.')
            return redirect('login')
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            old_password = form.cleaned_data.get('old_password')
            new_password = form.cleaned_data.get('new_password')

            # If account already has a password, require old_password match.
            if account.password_hash:
                if not verify_account_password(account, old_password):
                    messages.error(request, 'Mật khẩu cũ không chính xác.')
                    return render(request, 'user/change_password.html', {'form': form})

            # Validate new password length
            if not new_password or len(new_password) < 8:
                messages.error(request, 'Mật khẩu mới phải có ít nhất 8 ký tự.')
                return render(request, 'user/change_password.html', {'form': form})

            # Update Account password
            account.password_hash = make_password(new_password)
            account.save()

            # If there's a linked django User (allauth), also set its password
            try:
                if getattr(request, 'user', None) and request.user.is_authenticated:
                    try:
                        request.user.set_password(new_password)
                        request.user.save()
                    except Exception:
                        pass
            except Exception:
                pass

            messages.success(request, 'Mật khẩu đã được thay đổi/đặt thành công!')
            return redirect('profile')
    else:
        form = PasswordChangeForm()
    
    return render(request, 'user/change_password.html', {'form': form})


def password_reset(request):
    """Handle password reset via email"""
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            try:
                account = Account.objects.get(email=email)
                
                # Generate new random password with 8 characters
                new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                
                # Update password
                account.password_hash = make_password(new_password)
                account.save()
                
                # Send email with new password
                subject = 'Đặt lại mật khẩu - Smart Home Chef'
                message = f"""
Xin chào {account.username},

Bạn đã yêu cầu đặt lại mật khẩu. Mật khẩu mới của bạn là:

{new_password}

Vui lòng đăng nhập với mật khẩu này và thay đổi nó thành mật khẩu khác nếu bạn muốn.

Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.

Trân trọng,
Smart Home Chef Team
"""
                send_mail(
                    subject,
                    message,
                    'noreply@smarthomechef.com',
                    [email],
                    fail_silently=False,
                )
                
                messages.success(request, 'Mật khẩu mới đã được gửi đến email của bạn. Vui lòng kiểm tra inbox.')
                return redirect('login')
            
            except Account.DoesNotExist:
                # For security reasons, don't reveal if email exists
                messages.success(request, 'Nếu email tồn tại trong hệ thống, mật khẩu mới sẽ được gửi.')
                return redirect('login')
            except Exception as e:
                messages.error(request, f'Có lỗi xảy ra khi gửi email: {str(e)}')
    else:
        form = PasswordResetForm()
    
    return render(request, 'user/password_reset.html', {'form': form})


@csrf_exempt
@require_POST
def api_change_password(request):
    """API endpoint for changing password"""
    account = get_current_account(request)
    if not account:
        return JsonResponse({'ok': False, 'error': 'Bạn cần đăng nhập.'}, status=401)
    # Allow OAuth users (no password_hash) to set an initial password via API.
    
    try:
        data = json.loads(request.body or '{}')
        old_password = (data.get('old_password') or '').strip()
        new_password = (data.get('new_password') or '').strip()

        # If account already has a password, require old_password
        if account.password_hash:
            if not old_password:
                return JsonResponse({'ok': False, 'error': 'Vui lòng nhập mật khẩu cũ.'}, status=400)
            if not verify_account_password(account, old_password):
                return JsonResponse({'ok': False, 'error': 'Mật khẩu cũ không chính xác.'}, status=400)

        if not new_password or len(new_password) < 8:
            return JsonResponse({'ok': False, 'error': 'Mật khẩu mới phải có ít nhất 8 ký tự.'}, status=400)

        account.password_hash = make_password(new_password)
        account.save()

        # Sync to django User when present
        try:
            if getattr(request, 'user', None) and request.user.is_authenticated:
                try:
                    request.user.set_password(new_password)
                    request.user.save()
                except Exception:
                    pass
        except Exception:
            pass

        return JsonResponse({'ok': True, 'message': 'Mật khẩu đã được thay đổi/đặt thành công!'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def api_password_reset(request):
    """API endpoint for password reset"""
    try:
        data = json.loads(request.body or '{}')
        email = (data.get('email') or '').strip()
        
        if not email:
            return JsonResponse({'ok': False, 'error': 'Vui lòng nhập email.'}, status=400)
        
        try:
            account = Account.objects.get(email=email)
            
            # Generate new random password with 8 characters
            new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            
            # Update password
            account.password_hash = make_password(new_password)
            account.save()
            
            # Send email with new password
            subject = 'Đặt lại mật khẩu - Smart Home Chef'
            message = f"""
Xin chào {account.username},

Bạn đã yêu cầu đặt lại mật khẩu. Mật khẩu mới của bạn là:

{new_password}

Vui lòng đăng nhập với mật khẩu này và thay đổi nó thành mật khẩu khác nếu bạn muốn.

Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.

Trân trọng,
Smart Home Chef Team
"""
            send_mail(
                subject,
                message,
                'noreply@smarthomechef.com',
                [email],
                fail_silently=False,
            )
            
            # For security, always return success message
            return JsonResponse({'ok': True, 'message': 'Nếu email tồn tại trong hệ thống, mật khẩu mới sẽ được gửi.'})
        
        except Account.DoesNotExist:
            # For security reasons, don't reveal if email exists
            return JsonResponse({'ok': True, 'message': 'Nếu email tồn tại trong hệ thống, mật khẩu mới sẽ được gửi.'})
    
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def allauth_ready(request):
    """Check if user is authenticated via allauth and sync with Account model"""
    if request.user.is_authenticated:
        try:
            account = AllAuthAccountBridge.sync_account_from_user(request.user)
            return JsonResponse({
                'authenticated': True,
                'user_id': account.id,
                'username': account.username,
                'email': account.email,
            })
        except Exception as e:
            return JsonResponse({'authenticated': True, 'error': str(e)})
    return JsonResponse({'authenticated': False})


def dashboard(request):
    """
    Dashboard chính: hiển thị tổng quan dinh dưỡng và thống kê.
    
    Dữ liệu hiển thị:
    1. HÔMNAY (Today):
       - Tổng calories, protein, carbs, fat từ NutritionLog hôm nay
       - Số bữa đã ghi, progress to daily target
       - Visual indicators (pie chart, progress bar)
    
    2. TUẦN (7-day trend):
       - Calories trung bình 7 ngày gần nhất
       - Macro breakdown (protein/carb/fat ratio)
       - Chart để show trend up/down
    
    3. STREAK:
       - Số ngày liên tiếp ghi nutrition
    """
    account = get_current_account(request)
    if not account:
        return redirect('login')

    today = date.today()
    week_ago = today - timedelta(days=6)

    # Today's nutrition summary
    today_logs = NutritionLog.objects.filter(
        account=account,
        date=today
    ).select_related('food')

    total_calories = sum(log.calories or 0 for log in today_logs)
    total_protein = sum(log.protein or 0 for log in today_logs)
    total_carbs = sum(log.carbs or 0 for log in today_logs)
    total_fat = sum(log.fat or 0 for log in today_logs)
    meal_count = today_logs.count()

    # Daily targets (from UserGoal or defaults)
    user_goal = UserGoal.objects.filter(account=account).first()
    profile = get_profile(request) if 'get_profile' in globals() else None
    daily_cal = 2000
    if user_goal:
        try:
            daily_cal = int(getattr(user_goal, 'daily_calorie_target', 0) or 0)
        except Exception:
            daily_cal = 0
    if not daily_cal and profile:
        try:
            daily_cal = int(getattr(profile, 'daily_calorie_target', 0) or 0)
        except Exception:
            daily_cal = 2000
    daily_cal = daily_cal or 2000
    weight = 70
    if profile:
        try:
            weight = float(getattr(profile, 'weight', 0) or 70)
        except Exception:
            weight = 70
    target_protein = round(weight * 1.6, 1)
    target_carbs = round(daily_cal * 0.5 / 4, 1)
    target_fat = round(daily_cal * 0.3 / 9, 1)
    target_calories = daily_cal
    if user_goal:
        try:
            raw = getattr(user_goal, 'target_macros', None)
            if isinstance(raw, dict) and raw:
                if raw.get('protein'):
                    target_protein = round(daily_cal * (float(raw['protein']) / 100.0) / 4, 1)
                if raw.get('carbs'):
                    target_carbs = round(daily_cal * (float(raw['carbs']) / 100.0) / 4, 1)
                if raw.get('fat'):
                    target_fat = round(daily_cal * (float(raw['fat']) / 100.0) / 9, 1)
        except Exception:
            pass

    # Progress percentages
    calories_progress = min(100, (total_calories / target_calories * 100) if target_calories else 0)
    protein_progress = min(100, (total_protein / target_protein * 100) if target_protein else 0)
    carbs_progress = min(100, (total_carbs / target_carbs * 100) if target_carbs else 0)
    fat_progress = min(100, (total_fat / target_fat * 100) if target_fat else 0)

    # 7-day trend data
    week_logs = NutritionLog.objects.filter(
        account=account,
        date__gte=week_ago,
        date__lte=today
    ).values('date').annotate(
        daily_calories=Count('id') * 0  # Placeholder, will calculate properly
    ).order_by('date')

    # Calculate daily totals for the week
    daily_totals = {}
    for log in week_logs:
        day = log['date']
        if day not in daily_totals:
            daily_totals[day] = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0}
        daily_totals[day]['calories'] += log.get('calories', 0)
        daily_totals[day]['protein'] += log.get('protein', 0)
        daily_totals[day]['carbs'] += log.get('carbs', 0)
        daily_totals[day]['fat'] += log.get('fat', 0)

    # Prepare chart data
    chart_labels = []
    chart_calories = []
    chart_protein = []
    chart_carbs = []
    chart_fat = []

    for i in range(7):
        day = today - timedelta(days=6-i)
        chart_labels.append(day.strftime('%d/%m'))
        day_data = daily_totals.get(day, {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0})
        chart_calories.append(day_data['calories'])
        chart_protein.append(day_data['protein'])
        chart_carbs.append(day_data['carbs'])
        chart_fat.append(day_data['fat'])

    # Streak calculation
    streak = 0
    check_date = today
    while True:
        if NutritionLog.objects.filter(account=account, date=check_date).exists():
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    context = {
        'active': 'dashboard',
        'today': {
            'calories': total_calories,
            'protein': total_protein,
            'carbs': total_carbs,
            'fat': total_fat,
            'meal_count': meal_count,
            'calories_progress': calories_progress,
            'protein_progress': protein_progress,
            'carbs_progress': carbs_progress,
            'fat_progress': fat_progress,
        },
        'targets': {
            'calories': target_calories,
            'protein': target_protein,
            'carbs': target_carbs,
            'fat': target_fat,
        },
        'week_trend': {
            'labels': json.dumps(chart_labels),
            'calories': json.dumps(chart_calories),
            'protein': json.dumps(chart_protein),
            'carbs': json.dumps(chart_carbs),
            'fat': json.dumps(chart_fat),
        },
        'streak': streak,
    }
    return render(request, 'user/dashboard.html', context)
