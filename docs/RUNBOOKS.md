# Operational Runbooks

## 1. High API Latency Alert

### Detection
Prometheus alert: `django_http_request_duration_seconds > 2.0`

### Investigation Steps

```bash
# 1. Check application logs
docker-compose logs web --tail=100

# 2. Check slow database queries
python manage.py shell
>>> from django.db import connection
>>> from django.test.utils import CaptureQueriesContext
>>> with CaptureQueriesContext(connection) as context:
>>>     # Run suspected slow operation
>>>     pass
>>> for query in context.captured_queries:
>>>     print(f"{query['time']}s: {query['sql'][:100]}")

# 3. Check memory usage
docker stats web

# 4. Check database connections
docker-compose exec db sqlite3 :memory: ".connections"

# 5. Check Prometheus metrics
# Navigate to http://localhost:9090
# Query: rate(django_http_requests_total[5m])
```

### Resolution Steps

1. **If database is slow:**
   ```bash
   # Analyze database performance
   python manage.py dbshell
   sqlite> ANALYZE;
   sqlite> VACUUM;
   ```

2. **If memory is high:**
   ```bash
   # Restart application
   docker-compose restart web
   
   # Or if using Kubernetes:
   kubectl rollout restart deployment/smart-chef -n smart-chef
   ```

3. **If too many requests:**
   ```bash
   # Enable rate limiting (adjust in settings.py)
   # Restart application
   docker-compose restart web
   ```

4. **Scale up:**
   ```bash
   # For Kubernetes
   kubectl scale deployment smart-chef --replicas=3 -n smart-chef
   ```

### Post-Incident

- [ ] Check application performance metrics
- [ ] Analyze slow query logs
- [ ] Update cache settings if needed
- [ ] Document root cause

---

## 2. Database Connection Issues

### Detection
- Errors: "too many connections" or "connection refused"
- Prometheus metric: `django_db_new_connections_total` spike

### Investigation Steps

```bash
# 1. Check database status
docker-compose ps db

# 2. Check active connections
docker-compose exec db sqlite3 < connections.sql

# 3. Check application logs for connection errors
docker-compose logs web | grep -i "connection\|database"

# 4. Check Django settings
python manage.py shell
>>> from django.conf import settings
>>> print(settings.DATABASES)
```

### Resolution Steps

1. **Restart database:**
   ```bash
   docker-compose restart db
   ```

2. **Clear stale connections:**
   ```bash
   python manage.py dbshell
   sqlite> .quit
   ```

3. **Increase connection limit (if using PostgreSQL):**
   ```bash
   # Update docker-compose.yml or database config
   # max_connections = 500
   # Restart database
   ```

4. **Implement connection pooling:**
   ```bash
   # Add PgBouncer or similar
   # See deployment guide for details
   ```

### Post-Incident

- [ ] Check database connection pool settings
- [ ] Review application connection handling
- [ ] Update monitoring thresholds if needed

---

## 3. API Quota Exceeded (Gemini)

### Detection
- Error: `RESOURCE_EXHAUSTED` from Gemini API
- Users see fallback responses

### Investigation Steps

```bash
# 1. Check logs for quota errors
docker-compose logs web | grep -i "quota\|exhausted"

# 2. Check current usage
# Login to Google Cloud Console
# Navigate to: APIs & Services > Quotas > Gemini API

# 3. Check application request rate
python manage.py shell
>>> from apps.core_models.models import SearchEvent
>>> from django.utils import timezone
>>> from datetime import timedelta
>>> recent = SearchEvent.objects.filter(
>>>     created_at__gte=timezone.now() - timedelta(hours=1)
>>> ).count()
>>> print(f"Queries in last hour: {recent}")
```

### Resolution Steps

1. **Immediate:**
   - API automatically falls back to local recommendations
   - Monitor error rate

2. **Short-term:**
   ```bash
   # Reduce request rate temporarily
   # Update orchestrator.py to increase fallback threshold
   # CONFIDENCE_THRESHOLD = 0.7  # Increase from 0.6
   
   docker-compose restart web
   ```

3. **Long-term:**
   - Request quota increase from Google
   - Implement request caching
   - Batch requests when possible
   - Consider alternative LLM provider

### Post-Incident

- [ ] Analyze peak usage patterns
- [ ] Implement rate limiting
- [ ] Review quota increase request status
- [ ] Document usage metrics

---

## 4. Model Training Failure

### Detection
- Admin interface shows stale model
- Intent classifier returns low confidence
- Logs: "Failed to train model"

### Investigation Steps

```bash
# 1. Check model metadata
python manage.py shell
>>> from apps.core_models.models import ModelMetadata
>>> from apps.chat.models import Intent, Pattern
>>> latest_model = ModelMetadata.objects.latest('created_at')
>>> print(f"Model age: {latest_model.created_at}")
>>> print(f"Available intents: {Intent.objects.count()}")
>>> print(f"Patterns: {Pattern.objects.count()}")

# 2. Check training logs
docker-compose logs web | grep -i "train\|model"

# 3. Check artifact directory
ls -la artifacts/ai_models/
```

### Resolution Steps

1. **Manual retraining:**
   ```bash
   python manage.py shell
   >>> from app.services.model_training_service import train_intent_classifier
   >>> result = train_intent_classifier(force=True)
   >>> print(result)
   ```

2. **If pattern data is corrupted:**
   ```bash
   # Restore from backup
   cp db.sqlite3.backup db.sqlite3
   
   # Or rebuild patterns from database
   python manage.py shell
   >>> from apps.chat.models import MessageIntent, Intent
   >>> # Re-analyze MessageIntent records
   >>> messages = MessageIntent.objects.all()
   ```

3. **Check training code:**
   - Ensure `app/services/model_training_service.py` hasn't changed
   - Verify dependencies installed

### Post-Incident

- [ ] Verify model performance improved
- [ ] Check training schedule is running
- [ ] Review pattern database quality

---

## 5. A/B Test Statistical Anomaly

### Detection
- One variant shows unexpected behavior
- Click-through rate differs significantly
- Admin alert: "Unusual variant performance"

### Investigation Steps

```bash
# 1. Get experiment summary
python manage.py shell
>>> from app.services.ab_testing_service import ABTestingService
>>> experiment_id = 1  # Replace with actual ID
>>> summary = ABTestingService.get_experiment_summary(experiment_id)
>>> print(summary)

# 2. Check variant distribution
>>> stats = ABTestingService.get_variant_stats(experiment_id)
>>> for variant, data in stats.items():
>>>     print(f"{variant}: {data}")

# 3. Check raw events
>>> from apps.core_models.models import ExperimentEvent
>>> from datetime import timedelta
>>> from django.utils import timezone
>>> recent_events = ExperimentEvent.objects.filter(
>>>     experiment_id=experiment_id,
>>>     created_at__gte=timezone.now() - timedelta(hours=24)
>>> )
>>> print(f"Events in last 24h: {recent_events.count()}")
```

### Resolution Steps

1. **Check for issues:**
   - Ensure users properly assigned
   - Verify no duplicate assignments
   - Check for race conditions

2. **Pause experiment if needed:**
   ```bash
   python manage.py shell
   >>> from apps.core_models.models import Experiment
   >>> exp = Experiment.objects.get(id=1)
   >>> exp.status = 'paused'
   >>> exp.save()
   ```

3. **Analyze variant code:**
   - Verify variant implementation
   - Check for code changes affecting one variant

4. **Re-run significance test:**
   ```bash
   >>> winner = ABTestingService.is_variant_winner(experiment_id)
   >>> print(f"Statistical winner: {winner}")
   ```

### Post-Incident

- [ ] Document findings
- [ ] Review variant implementation
- [ ] Update test parameters if needed
- [ ] Continue monitoring

---

## 6. Disk Space Critical

### Detection
- Alert: "Disk usage > 90%"
- Application can't write to database

### Investigation Steps

```bash
# 1. Check disk usage
docker system df

# 2. Check container sizes
docker ps -s

# 3. Find large files
du -sh /* | sort -rh | head -20

# 4. Check database size
ls -lah db.sqlite3

# 5. Check logs directory
du -sh logs/
```

### Resolution Steps

1. **Immediate - Clean up:**
   ```bash
   # Remove old logs
   find logs/ -name "*.log" -mtime +30 -delete
   
   # Remove old Docker images
   docker image prune -a --force
   
   # Remove unused Docker volumes
   docker volume prune --force
   ```

2. **Database optimization:**
   ```bash
   # Vacuum database
   python manage.py dbshell
   sqlite> VACUUM;
   
   # Archive old data
   python manage.py delete_old_search_events --days=90
   ```

3. **Expand storage:**
   - Add volume to docker-compose
   - Mount external storage
   - Upgrade server disk

### Post-Incident

- [ ] Set up log rotation
- [ ] Implement data archival policy
- [ ] Add disk usage monitoring alert

---

## 7. Cascading Failure - Multiple Systems Down

### Detection
- Multiple services not responding
- Cascading error messages in logs

### Emergency Response

1. **Assess impact (2 min):**
   ```bash
   docker-compose ps
   docker-compose logs --tail=50
   ```

2. **Isolate the issue (3 min):**
   - Is database responding?
   - Is application running?
   - Is external API working?

3. **Execute recovery (5-10 min):**
   ```bash
   # Option 1: Rolling restart
   docker-compose restart web
   sleep 10
   docker-compose restart db
   
   # Option 2: Full restart
   docker-compose down
   docker-compose up -d
   
   # Option 3: Kubernetes rollback
   kubectl rollout undo deployment/smart-chef -n smart-chef
   ```

4. **Verify recovery (5 min):**
   ```bash
   curl http://localhost:8000/health/all/
   ```

### Post-Incident

- [ ] Root cause analysis
- [ ] Implement preventive measures
- [ ] Update monitoring/alerting
- [ ] Document incident
- [ ] Hold postmortem meeting

---

## General Troubleshooting Commands

```bash
# View logs with filtering
docker-compose logs -f --tail=100 web | grep ERROR

# Access application shell
docker-compose exec web python manage.py shell

# Run management command
docker-compose exec web python manage.py check

# Monitor real-time stats
docker stats

# Health check endpoints
curl http://localhost:8000/health/
curl http://localhost:8000/health/db/
curl http://localhost:8000/health/cache/
```

## Escalation Path

1. **Level 1** (Application Developer)
   - Check logs and metrics
   - Execute troubleshooting steps
   - Document findings

2. **Level 2** (DevOps/Infrastructure)
   - Infrastructure scaling
   - Database issues
   - Deployment issues

3. **Level 3** (Architect/Leadership)
   - Major outage decisions
   - Vendor communication
   - Communications to stakeholders

## Communication Template

When incident occurs:
```
🚨 INCIDENT ALERT 🚨
Service: [SERVICE_NAME]
Severity: [CRITICAL/HIGH/MEDIUM/LOW]
Start Time: [TIME]
Status: [Investigating/In Progress/Resolved]
Impact: [AFFECTED_USERS/SYSTEMS]

Current Actions:
- [ACTION 1]
- [ACTION 2]

ETA for Resolution: [TIME]
```
