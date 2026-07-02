"""Centralized configuration for all external services and sensitive data.

All environment variables should be defined in .env file or system environment.
This module loads and validates configuration at startup.
"""

import os
from pathlib import Path


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


def _get_env(key, default=None, required=False):
    """
    Get environment variable with validation.
    
    Args:
        key: Environment variable name
        default: Default value if not set
        required: Raise error if not set and no default provided
    """
    value = os.environ.get(key, '').strip()
    if not value:
        if required and default is None:
            raise ValueError(f"Missing required environment variable: {key}")
        return default
    return value


def _get_env_bool(key, default=False):
    """Get environment variable as boolean."""
    value = os.environ.get(key, '').strip().lower()
    if not value:
        return default
    return value in ('1', 'true', 'yes', 'on')


# ============================================================================
# DJANGO / APP CONFIG
# ============================================================================

SECRET_KEY = _get_env(
    'SECRET_KEY',
    default=_get_env('SESSION_SECRET', default='django-insecure-noi-tro-ai-secret-key')
)
DEBUG = _get_env_bool('DEBUG', default=True)


# ============================================================================
# GEMINI API CONFIG
# ============================================================================

GEMINI_API_KEY = _get_env('GEMINI_API_KEY', required=False)
GEMINI_MODEL = _get_env('GEMINI_MODEL', default='gemini-1.5-flash')
GEMINI_BASE_URL = _get_env('AI_INTEGRATIONS_GEMINI_BASE_URL', required=False)
GEMINI_KEY_NAME = _get_env('GEMINI_KEY_NAME', default='test')

# Flag to indicate if Gemini is properly configured
GEMINI_ENABLED = bool(GEMINI_API_KEY and GEMINI_API_KEY.strip() and GEMINI_API_KEY != 'dummy')

# Local Qwen model integration (uses Ollama with OpenAI-compatible API)
OLLAMA_BASE_URL = _get_env('OLLAMA_BASE_URL', default='http://localhost:11434/v1')
OLLAMA_MODEL = _get_env('OLLAMA_MODEL', default='qwen2.5:7b')
OLLAMA_API_KEY = _get_env('OLLAMA_API_KEY', default='ollama')
OLLAMA_ENABLED = _get_env_bool('OLLAMA_ENABLED', default=True)  # Enable by default if Ollama server is running

# Raw Ollama URL for direct /api/chat (non-OpenAI-compatible)
OLLAMA_URL = _get_env('OLLAMA_URL', default='http://localhost:11434')

# How many times to retry Gemini calls when rate limited or transient errors occur
GEMINI_RETRIES = int(_get_env('GEMINI_RETRIES', default='3'))
GEMINI_ESTIMATED_COST_USD = float(_get_env('GEMINI_ESTIMATED_COST_USD', default='0.0'))
LOCAL_LLM_ESTIMATED_COST_USD = float(_get_env('LOCAL_LLM_ESTIMATED_COST_USD', default='0.0'))


# ============================================================================
# SPOONACULAR API CONFIG
# ============================================================================

SPOONACULAR_API_KEY = _get_env('SPOONACULAR_API_KEY', required=False)
SPOONACULAR_BASE_URL = _get_env(
    'SPOONACULAR_BASE_URL',
    default='https://api.spoonacular.com'
).rstrip('/')

SPOONACULAR_SEARCH_URL = _get_env(
    'SPOONACULAR_SEARCH_URL',
    default=f'{SPOONACULAR_BASE_URL}/food/search'
)
SPOONACULAR_INGREDIENT_SEARCH_URL = _get_env(
    'SPOONACULAR_INGREDIENT_SEARCH_URL',
    default=f'{SPOONACULAR_BASE_URL}/food/ingredients/search'
)
SPOONACULAR_COMPLEX_SEARCH_URL = _get_env(
    'SPOONACULAR_COMPLEX_SEARCH_URL',
    default=f'{SPOONACULAR_BASE_URL}/recipes/complexSearch'
)
SPOONACULAR_RECIPE_INFO_URL_TEMPLATE = _get_env(
    'SPOONACULAR_RECIPE_INFO_URL_TEMPLATE',
    default=f'{SPOONACULAR_BASE_URL}/recipes/{{id}}/information'
)
SPOONACULAR_INGREDIENT_INFO_URL_TEMPLATE = _get_env(
    'SPOONACULAR_INGREDIENT_INFO_URL_TEMPLATE',
    default=f'{SPOONACULAR_BASE_URL}/food/ingredients/{{id}}/information'
)

SPOONACULAR_ENABLED = bool(SPOONACULAR_API_KEY and SPOONACULAR_API_KEY.strip() and SPOONACULAR_API_KEY != 'your-spoonacular-api-key')
SPOONACULAR_TIMEOUT = int(_get_env('SPOONACULAR_TIMEOUT', default='5'))
SPOONACULAR_RETRIES = int(_get_env('SPOONACULAR_RETRIES', default='3'))




# ============================================================================
# API-NINJAS CONFIG
# ============================================================================

API_NINJAS_API_KEY = _get_env('API_NINJAS_KEY', required=False)
API_NINJAS_BASE_URL = _get_env(
    'API_NINJAS_BASE_URL',
    default='https://api.api-ninjas.com',
).rstrip('/')
API_NINJAS_ENABLED = bool(
    API_NINJAS_API_KEY
    and API_NINJAS_API_KEY.strip()
    and API_NINJAS_API_KEY != 'dummy'
)

# ============================================================================
# WINMART (CRAWLER) CONFIG
# ============================================================================
# Timeout (seconds) for requests to the WinMart API
WINMART_TIMEOUT = int(_get_env('WINMART_TIMEOUT', default='10'))
# Number of retries when calling WinMart before giving up
WINMART_RETRIES = int(_get_env('WINMART_RETRIES', default='3'))


# ============================================================================
# THEMEALDB CONFIG
# ============================================================================

THEMEALDB_BASE_URL = _get_env(
    'THEMEALDB_BASE_URL',
    default='https://www.themealdb.com/api/json/v1/1'
).rstrip('/')

THEMEALDB_SEARCH_URL = _get_env(
    'THEMEALDB_SEARCH_URL',
    default=f'{THEMEALDB_BASE_URL}/search.php'
)
THEMEALDB_LOOKUP_URL = _get_env(
    'THEMEALDB_LOOKUP_URL',
    default=f'{THEMEALDB_BASE_URL}/lookup.php'
)
THEMEALDB_AUTO_TRANSLATE = _get_env_bool('THEMEALDB_AUTO_TRANSLATE', default=True)


# ============================================================================
# DATABASE CONFIG
# ============================================================================

DATABASE_URL = _get_env('DATABASE_URL', required=False)
DB_ENGINE = _get_env('DB_ENGINE', default='django.db.backends.sqlite3')
DB_NAME = _get_env('DB_NAME', default='smart-chef')
DB_USER = _get_env('DB_USER', default='')
DB_PASSWORD = _get_env('DB_PASSWORD', default='')
DB_HOST = _get_env('DB_HOST', default='')
DB_PORT = _get_env('DB_PORT', default='')


# ============================================================================
# GOOGLE OAUTH CONFIG
# ============================================================================

GOOGLE_CLIENT_ID = _get_env('GOOGLE_CLIENT_ID', required=False)
GOOGLE_CLIENT_SECRET = _get_env('GOOGLE_CLIENT_SECRET', required=False)
GOOGLE_OAUTH_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


# ============================================================================
# EMAIL CONFIG
# ============================================================================

MAIL_EMAIL = _get_env('MY_EMAIL', required=False)
MAIL_PASSWORD = _get_env('MAIL_PASSWORD', required=False)
MAIL_ENABLED = bool(MAIL_EMAIL and MAIL_PASSWORD)


# ============================================================================
# APP-SPECIFIC CONFIG
# ============================================================================

REQUIRE_AUTH = _get_env_bool('REQUIRE_AUTH', default=False)
CSRF_TRUSTED_EXTRA_ORIGINS_STR = _get_env('CSRF_TRUSTED_EXTRA_ORIGINS', default='')
CSRF_TRUSTED_EXTRA_ORIGINS = [x.strip() for x in CSRF_TRUSTED_EXTRA_ORIGINS_STR.split(',') if x.strip()]
ALLOWED_HOSTS_STR = _get_env('ALLOWED_HOSTS', default='*')
ALLOWED_HOSTS = [x.strip() for x in ALLOWED_HOSTS_STR.split(',') if x.strip()]
