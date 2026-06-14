import os
from pathlib import Path


def load_dotenv_from_repo():
    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / '.env'
    data = {}
    if not env_path.exists():
        return data
    for raw in env_path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, val = line.split('=', 1)
        data[key.strip()] = val.strip().strip('"').strip("'")
    return data


def main():
    env = load_dotenv_from_repo()
    keys = [
        'SECRET_KEY', 'DEBUG', 'ALLOWED_HOSTS', 'DATABASE_URL', 'DB_NAME', 'DB_USER',
        'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'GEMINI_API_KEY', 'GEMINI_MODEL',
        'SPOONACULAR_API_KEY', 'THEMEALDB_BASE_URL', 'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET',
        'MY_EMAIL', 'MAIL_PASSWORD', 'CSRF_TRUSTED_EXTRA_ORIGINS'
    ]
    for k in keys:
        v = env.get(k) or os.environ.get(k)
        status = 'SET' if v and str(v).strip() else 'MISSING'
        short = (v[:50] + '...') if v and len(str(v)) > 50 else (v or '')
        print(f"{k:30} {status:8} {short}")


if __name__ == '__main__':
    main()
