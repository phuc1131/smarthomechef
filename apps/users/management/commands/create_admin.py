from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.hashers import make_password
from apps.users.models import Account


class Command(BaseCommand):
    help = 'Tạo tài khoản admin mới'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Tên đăng nhập cho admin')
        parser.add_argument('--email', type=str, help='Email cho admin (tùy chọn)')
        parser.add_argument('--password', type=str, help='Mật khẩu cho admin (tùy chọn, sẽ prompt nếu không cung cấp)')

    def handle(self, *args, **options):
        username = options['username'].strip()

        if Account.objects.filter(username__iexact=username).exists():
            raise CommandError(f'Tài khoản "{username}" đã tồn tại.')

        email = options.get('email', '').strip()
        if not email:
            email = f'{username.lower()}@admin.smartchef'

        password = options.get('password')
        if not password:
            import getpass
            password = getpass.getpass('Nhập mật khẩu cho admin: ')
            if not password:
                raise CommandError('Mật khẩu không được để trống.')

        if len(password) < 8:
            raise CommandError('Mật khẩu phải có ít nhất 8 ký tự.')

        # Tạo admin account
        admin = Account.objects.create(
            username=username,
            email=email,
            password_hash=make_password(password),
            role='admin',
            is_active=True,
        )

        self.stdout.write(
            self.style.SUCCESS(f'Đã tạo tài khoản admin: {admin.username} ({admin.email})')
        )