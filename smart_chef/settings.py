import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def load_env_file(env_path):
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ[key] = value


load_env_file(BASE_DIR / '.env')


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default):
    value = os.environ.get(name, '')
    if not value.strip():
        return default
    return [item.strip() for item in value.split(',') if item.strip()]


SECRET_KEY = os.environ.get('SECRET_KEY', os.environ.get('SESSION_SECRET', 'django-insecure-noi-tro-ai-secret-key'))

DEBUG = env_bool('DEBUG', True)

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', ['*'])
if DEBUG:
    for host in ['testserver', 'localhost', '127.0.0.1']:
        if host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)

CSRF_TRUSTED_ORIGINS = [
    'https://*.replit.dev',
    'https://*.replit.co',
    'https://*.replit.app',
    'https://*.trycloudflare.com',
    'http://localhost:5173',
    'http://0.0.0.0:5173',
]

CSRF_TRUSTED_ORIGINS += env_list('CSRF_TRUSTED_EXTRA_ORIGINS', [])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'django.contrib.sites',
    # Django-allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    # Feature-based apps
    'apps.users.apps.UsersConfig',
    'apps.chat.apps.ChatConfig',
    'apps.nutrition.apps.NutritionConfig',
    'apps.meal_plans.apps.MealPlansConfig',
    'apps.admin_panel.apps.AdminPanelConfig',
    'apps.core_models.apps.CoreModelsConfig',
    'app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
REQUIRE_AUTH = env_bool('REQUIRE_AUTH', False)

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

ROOT_URLCONF = 'smart_chef.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'smart_chef' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'app.context_processors.auth_context',  # Legacy app processor
            ],
        },
    },
]

WSGI_APPLICATION = 'smart_chef.wsgi.application'


def build_database_config():
    database_url = os.environ.get('DATABASE_URL', '').strip()
    if database_url:
        return {
            'default': dj_database_url.parse(database_url, conn_max_age=600),
        }

    db_engine = os.environ.get('DB_ENGINE', '').strip() or 'django.db.backends.sqlite3'
    db_name = os.environ.get('DB_NAME', '').strip() or str(BASE_DIR / 'db.sqlite3')
    db_user = os.environ.get('DB_USER', '').strip()
    db_password = os.environ.get('DB_PASSWORD', '').strip()
    db_host = os.environ.get('DB_HOST', '').strip()
    db_port = os.environ.get('DB_PORT', '').strip()

    if db_engine == 'django.db.backends.sqlite3':
        if not db_name or db_name == 'smart-home-chef':
            preferred_sqlite_path = BASE_DIR / 'db.sqlite3'
            if preferred_sqlite_path.exists():
                db_name = str(preferred_sqlite_path)

    database_config = {
        'ENGINE': db_engine,
        'NAME': db_name,
    }

    if db_engine != 'django.db.backends.sqlite3':
        database_config.update({
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': db_host,
            'PORT': db_port,
        })

    return {'default': database_config}


DATABASES = build_database_config()

LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = False

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'smart_chef' / 'templates',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================================
# DJANGO-ALLAUTH CONFIGURATION
# ============================================================================
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    }
}

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS['google']['APP'] = {
        'name': 'Google',
        'client_id': GOOGLE_CLIENT_ID,
        'secret': GOOGLE_CLIENT_SECRET,
        'settings': {
            'hidden': True,
        },
    }

# Allauth settings
ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'optional'
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'optional'
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_QUERY_EMAIL = True
ACCOUNT_ADAPTER = 'allauth.account.adapter.DefaultAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'apps.users.allauth_adapter.CustomSocialAccountAdapter'

LOGIN_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
# Support legacy env names used in .env: MY_EMAIL / MAIL_PASSWORD
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', os.environ.get('MY_EMAIL', ''))
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', os.environ.get('MAIL_PASSWORD', ''))
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@smarthomechef.com')

# ============================================================================
# LOCAL LLM CSV IMPORT
# ============================================================================
LOCAL_LLM_IMPORT_ENABLED = env_bool('LOCAL_LLM_IMPORT_ENABLED', True)
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_IMPORT_MODEL = os.environ.get('OLLAMA_IMPORT_MODEL', 'qwen2.5:7b')
IMPORT_QWEN_MIN_CONFIDENCE = float(os.environ.get('IMPORT_QWEN_MIN_CONFIDENCE', '0.65'))
IMPORT_QWEN_TIMEOUT = int(os.environ.get('IMPORT_QWEN_TIMEOUT', '120'))
