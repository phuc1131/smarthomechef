"""
Custom authentication backend for Smart Chef
Bridges django.contrib.auth.User with Account model
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from apps.users.models import Account, UserProfile

User = get_user_model()


class AccountBackend(ModelBackend):
    """
    Authenticate against Account model (legacy)
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # This is handled by our custom auth views
        return None

    def get_user(self, user_id):
        """Get User by id"""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class AllAuthAccountBridge:
    """
    Helper to sync User and Account models after allauth login
    """
    @staticmethod
    def sync_account_from_user(user):
        """
        Create or update Account from django User after allauth signup/login
        """
        # Check if Account exists
        account = Account.objects.filter(email=user.email).first()
        
        if account:
            # Update existing account
            account.username = user.username
            account.is_active = user.is_active
            account.save()
        else:
            # Create new account
            username = user.username
            # Make sure username is unique
            counter = 1
            while Account.objects.filter(username=username).exists():
                username = f"{user.username}_{counter}"
                counter += 1
            
            account = Account.objects.create(
                username=username,
                email=user.email,
                password_hash='',  # OAuth users don't have password
                role='user',
                is_active=True,
            )
        
        # Create UserProfile if it doesn't exist
        if not hasattr(account, 'userprofile'):
            UserProfile.objects.get_or_create(
                account=account,
                defaults={
                    'name': user.first_name or user.username,
                }
            )
        
        return account

    @staticmethod
    def get_or_create_user(email, username=None, first_name=None, **extra_fields):
        """
        Get or create django User from email
        """
        user = User.objects.filter(email=email).first()
        
        if not user:
            # Create new user
            if not username:
                username = email.split('@')[0]
            
            # Make username unique
            counter = 1
            original_username = username
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name or '',
                **extra_fields
            )
        else:
            # Update existing user
            if first_name:
                user.first_name = first_name
                user.save()
        
        return user
