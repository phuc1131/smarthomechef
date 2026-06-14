# Smart Home Chef - Deployment Guide

## Prerequisites

- Docker & Docker Compose (for containerized deployment)
- Python 3.13 (for local development)
- pip and virtualenv
- PostgreSQL 14+ (for production, optional - SQLite works for development)

## Local Development Setup

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/smart-home-chef.git
cd smart-home-chef

# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create `.env` file:
```
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
```

### 3. Database Migrations

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run Development Server

```bash
python manage.py runserver
# Access at http://localhost:8000
# Admin panel at http://localhost:8000/admin
```

## Docker Deployment

### Local Docker Development

```bash
# Build and run with Docker Compose
docker-compose up -d

# Create superuser in container
docker-compose exec web python manage.py createsuperuser

# Run migrations
docker-compose exec web python manage.py migrate

# Access application
# Web: http://localhost:8000
# Grafana: http://localhost:3000
# Prometheus: http://localhost:9090
```

### Production Docker Build

```bash
# Build image
docker build -t smart-home-chef:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -e DEBUG=False \
  -e SECRET_KEY=your-secret-key \
  -e ALLOWED_HOSTS=your-domain.com \
  -e DATABASE_URL=postgresql://user:pass@db-host/dbname \
  -v ./data:/data \
  smart-home-chef:latest
```

## Kubernetes Deployment

### Prerequisites

- kubectl configured to access your cluster
- Helm 3.0+ (optional but recommended)

### Create Namespace

```bash
kubectl create namespace smart-chef
```

### Deploy with Helm (Recommended)

```bash
helm install smart-chef ./helm \
  -n smart-chef \
  -f values.yml \
  --set ingress.host=your-domain.com
```

### Manual kubectl Deployment

```bash
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/configmap.yml
kubectl apply -f k8s/secret.yml
kubectl apply -f k8s/deployment.yml
kubectl apply -f k8s/service.yml
kubectl apply -f k8s/ingress.yml
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| DEBUG | No | False | Enable debug mode |
| SECRET_KEY | Yes | - | Django secret key (min 50 chars) |
| ALLOWED_HOSTS | Yes | - | Comma-separated list of allowed hosts |
| DATABASE_URL | No | sqlite:///db.sqlite3 | Database connection string |
| GEMINI_API_KEY | Yes | - | Google Gemini API key |
| GEMINI_MODEL | No | gemini-2.5-flash | Gemini model version |
| REDIS_URL | No | redis://localhost | Redis cache URL |
| STATIC_ROOT | No | /app/staticfiles | Static files directory |
| MEDIA_ROOT | No | /app/media | Media files directory |

## Database Migrations

```bash
# Create new migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations

# Rollback specific migration
python manage.py migrate app_name 0001
```

## Static Files

```bash
# Collect static files for production
python manage.py collectstatic --noinput

# In production, serve static files via:
# - Django WhiteNoise middleware (already configured)
# - Nginx reverse proxy
# - AWS S3 or similar storage
```

## Backup & Restore

### Database Backup

```bash
# SQLite
cp db.sqlite3 db.sqlite3.backup

# PostgreSQL
pg_dump -U username -d dbname -h hostname > backup.sql

# MongoDB
mongodump --uri="mongodb://..." --out=backup/
```

### Database Restore

```bash
# SQLite
cp db.sqlite3.backup db.sqlite3

# PostgreSQL
psql -U username -d dbname -h hostname < backup.sql

# MongoDB
mongorestore --uri="mongodb://..." backup/
```

## Health Checks

The application provides health check endpoints:

```bash
# Django application health
curl http://localhost:8000/health/

# Database connection
curl http://localhost:8000/health/db/

# Cache system
curl http://localhost:8000/health/cache/

# All services
curl http://localhost:8000/health/all/
```

## Monitoring

### Prometheus Metrics

Metrics available at: `http://localhost:8000/metrics/`

Key metrics:
- `django_http_requests_total` - Total HTTP requests
- `django_http_request_duration_seconds` - Request duration
- `django_model_inserts_total` - Database inserts
- `django_model_queries_total` - Database queries
- `django_db_new_connections_total` - Database connections

### Grafana Dashboards

Default credentials: `admin / admin123`

Pre-configured dashboards:
- Django Application Overview
- Database Performance
- AI Model Metrics
- A/B Test Results
- User Activity

## Troubleshooting

### Application won't start

```bash
# Check logs
docker-compose logs web

# Run Django check
python manage.py check

# Test database connection
python manage.py dbshell
```

### Database migration errors

```bash
# Show current migration state
python manage.py showmigrations

# Mark migration as applied without running
python manage.py migrate --fake app_name 0001

# Show migration dependencies
python manage.py showmigrations --list
```

### Static files not loading

```bash
# Collect static files
python manage.py collectstatic --noinput --clear

# Check permissions
ls -la staticfiles/

# Verify web server configuration
```

### Memory issues

```bash
# Check container memory usage
docker stats

# Limit container memory
docker run --memory=2g ...

# Monitor Django memory
python manage.py shell
>>> from django.db import connection
>>> len(connection.queries)  # Check query count
```

## Security

### HTTPS/SSL Configuration

```bash
# Generate self-signed certificate (development only)
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# In production, use Let's Encrypt with Certbot
certbot certonly --standalone -d your-domain.com
```

### Django Security Settings

Required for production:
```python
DEBUG = False
SECRET_KEY = <strong-random-key>
ALLOWED_HOSTS = ['your-domain.com']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
```

## Scaling

### Horizontal Scaling with Kubernetes

```bash
# Scale deployment
kubectl scale deployment smart-chef --replicas=3 -n smart-chef

# Auto-scale based on CPU
kubectl autoscale deployment smart-chef --min=2 --max=10 --cpu-percent=80 -n smart-chef
```

### Database Scaling

```bash
# Add read replicas (PostgreSQL)
# See your database provider's documentation

# Connection pooling with PgBouncer
docker run -d -p 6432:6432 pgbouncer:latest
```

## CI/CD Pipeline

The project uses GitHub Actions for:
1. **Testing** - Run pytest on every push
2. **Linting** - Code quality checks with flake8
3. **Security** - Bandit security scanning
4. **Docker Build** - Build and push image on main branch
5. **Deployment** - Auto-deploy to production

See `.github/workflows/` for configuration.

## Maintenance

### Regular Tasks

Daily:
- Monitor error logs
- Check application health
- Verify backup completion

Weekly:
- Review performance metrics
- Check database size
- Analyze A/B test results

Monthly:
- Database optimization (VACUUM, ANALYZE)
- Update dependencies
- Security audit
- Backup verification

### Updates

```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Update Docker base image
docker pull python:3.13-slim

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

## Support & Documentation

- **Documentation**: See `/docs` directory
- **Issues**: Report on GitHub Issues
- **Wiki**: See Project Wiki for additional guides
- **API Docs**: Available at `/api/docs/` when running
