import uuid
from django.contrib.auth.hashers import make_password

from apps.users.models import Account, UserProfile


def get_client_ip(request):
    """Lấy IP của client từ request, hỗ trợ proxy headers"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    return ip


def get_or_create_guest_account(request):
    """Tạo hoặc lấy guest account.

    Chiến lược:
    - Nếu client có cookie `guest_uuid`, dùng đó làm định danh guest (guest_<uuid8>). 
    - Nếu không có cookie, tạo UUID mới và gán vào `request._guest_uuid_to_set` để caller
      có thể set cookie trong Response. Fallback tên user theo IP nếu UUID không khả dụng.
    """
    client_ip = get_client_ip(request)

    guest_uuid = request.COOKIES.get('guest_uuid')
    if guest_uuid:
        guest_username = f'guest_{guest_uuid}'
    else:
        # tạo UUID và đánh dấu để set cookie khi trả response
        new_uuid = uuid.uuid4().hex
        request._guest_uuid_to_set = new_uuid
        # dùng 8 ký tự đầu để giữ tên ngắn
        guest_username = f'guest_{new_uuid[:8]}'

    account, created = Account.objects.get_or_create(
        username=guest_username,
        defaults={
            'email': f'{guest_username}@local.smartchef',
            'password_hash': make_password('guest'),
            'role': 'guest',
            'is_active': True,
        }
    )
    return account


def get_account_from_request(request):
    """Lấy account từ session hoặc tạo guest account dựa trên IP"""
    user_id = request.session.get('user_id')

    # Nếu user đã đăng nhập, lấy account từ DB
    if user_id:
        account = Account.objects.filter(id=user_id, is_active=True).first()
        if account:
            return account

    # Nếu chưa đăng nhập, tạo/lấy guest account dựa trên IP
    return get_or_create_guest_account(request)


def get_profile(request):
    """Lấy UserProfile của user hiện tại"""
    account = get_account_from_request(request)
    if not account:
        return None

    profile, _ = UserProfile.objects.get_or_create(
        account=account,
        defaults={'name': account.username}  # Cung cấp giá trị mặc định cho name
    )
    return profile