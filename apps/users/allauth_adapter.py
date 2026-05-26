"""
Custom AllAuth adapters to fix OAuth signup issues
"""
from django.utils import timezone
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from apps.users.models import Account


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for Google OAuth that:
    1. Prevents IntegrityError by setting last_login before user creation
    2. Links OAuth users with existing Account (legacy model) if email matches
    3. Auto-creates account if email is new
    """
    def save_user(self, request, sociallogin, form=None):
        """
        Save user and ensure last_login is set to prevent IntegrityError.
        Also link with existing Account (legacy) model if email matches.
        
        IMPORTANT: Set last_login BEFORE calling super().save_user() because
        super() will immediately insert the user into the database. If last_login
        is None at that point, PostgreSQL will raise NOT NULL constraint violation.
        """
        # Set last_login on the user object BEFORE super().save_user() is called
        if sociallogin.user.last_login is None:
            sociallogin.user.last_login = timezone.now()
        
        # Now call super() which will save the user with last_login already set
        user = super().save_user(request, sociallogin, form=form)
        
        # Check if email matches existing Account (legacy) model
        email = user.email
        try:
            account = Account.objects.get(email=email)
            # Account exists - this is case 1: người dùng đã tạo tài khoản
            print(f"✓ Linked Google account {email} with existing Account ID {account.id}")
        except Account.DoesNotExist:
            # Account doesn't exist - create new one (case 2: người dùng mới)
            try:
                # Auto-create Account from django.contrib.auth.User
                username = user.username or email.split('@')[0]
                account = Account.objects.create(
                    email=email,
                    username=username,
                    is_active=True,
                )
                print(f"✓ Created new Account ID {account.id} for {email}")
            except Exception as e:
                print(f"⚠ Warning creating Account for {email}: {e}")
        
        return user
