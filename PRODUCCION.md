# 🚀 Guía de Despliegue en Producción — TicketDesk Enterprise

Esta guía cubre los cambios aplicados para escalar a **8000 empleados + 100 técnicos**.

## ✅ Lo que se aplicó automáticamente

### 1. Gunicorn + eventlet (start_production.bat)

El servidor ahora puede correr con **Gunicorn** en lugar del dev server de Flask:

```bash
# Modo desarrollo (sigue funcionando como siempre):
python app.py

# Modo producción (recomendado para uso real):
start_production.bat
# o manualmente:
python -m gunicorn -c gunicorn.conf.py wsgi:app
```

**Configuración**: `gunicorn.conf.py`
- Workers: **N° de CPUs** del servidor (puede sobreescribirse con `GUNICORN_WORKERS=4`)
- Conexiones por worker: **2000** (websockets concurrentes)
- Recicla cada 1000 requests para evitar memory leaks
- Logs en `logs/access.log` y `logs/error.log`

### 4. Paginación en `/api/tickets/list`

```
GET /api/tickets/list?page=2&per_page=100
```
Response ahora incluye: `total`, `returned`, `page`, `per_page`, `total_pages`.
**Backward compatible** — sin params funciona como antes (500 más recientes).

### 5. Purga automática de AuditLog

Scheduler diario que borra logs > 365 días.
- Configurable via env: `AUDIT_LOG_RETENTION_DAYS=730`
- O vía BD: `Config(key='audit_retention_days', value='730')`
- `0` o negativo = deshabilitado

### 6. Cache en memoria con TTL

Cache simple (no requiere Redis). Cacheado:
- `get_company_theme()` — 5 min TTL
- `get_business_config()` — 5 min TTL
- Auto-invalidación al guardar cambios

### 8. Cache headers para assets estáticos

- `/static/*` → `Cache-Control: public, max-age=2592000, immutable` (30 días)
- `/api/*` → `Cache-Control: no-store` (siempre fresco)

## 🛠️ Lo que NO se activa automáticamente (requiere infraestructura)

### 7. Celery (cola distribuida) — OPCIONAL

**Cuándo activar**: cuando tengas >4 workers de Gunicorn y los schedulers
deban coordinarse para no duplicar trabajo.

**Setup**:
```bash
pip install celery redis
# Levantar Redis:
docker run -d -p 6379:6379 --name ticketdesk-redis redis
# Configurar:
SET CELERY_BROKER_URL=redis://localhost:6379/0
# Arrancar worker:
celery -A wsgi.celery worker --loglevel=info
```

**Migrar schedulers a Celery** (requiere editar `app.py`):
- `start_backup_scheduler` → `@celery.task` con `@periodic_task`
- `start_sla_alert_scheduler` → idem
- `start_mailbox_poller` → idem
- `start_audit_log_purge_scheduler` → idem

**Por qué no lo activé**: requiere Redis corriendo y testing.
Mientras Gunicorn use `preload_app=True` + el flag `_bootstrapped`, los threads
solo arrancan UNA VEZ por proceso master, así que **no se duplican** con multi-worker.

### 9. Réplica de lectura PostgreSQL — OPCIONAL

**Cuándo activar**: cuando tengas > 200 req/seg sostenidos y el master DB esté al 70% CPU.

**Setup**:
1. Crear réplica de PostgreSQL (Supabase Pro lo soporta nativo)
2. Configurar SQLAlchemy con `binds`:

```python
app.config['SQLALCHEMY_BINDS'] = {
    'read': os.getenv('DATABASE_READ_URL')  # réplica
}
# Usar para reads pesados:
Ticket.query.options(db.session.using_bind('read')).all()
```

**Por qué no lo activé**: requiere segundo PostgreSQL + cambios cuidadosos en queries
de read-only.

## 📊 Variables de entorno relevantes

```env
# Base de datos (recomendado: PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:5432/ticketdesk
# O SQLite para desarrollo:
# DATABASE_URL=sqlite:///ticketdesk_v2.db

# Gunicorn
GUNICORN_BIND=0.0.0.0:5050
GUNICORN_WORKERS=4
GUNICORN_LOG_LEVEL=info

# Retención de logs
AUDIT_LOG_RETENTION_DAYS=365

# SMTP (opcional)
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USER=user@empresa.com
SMTP_PASSWORD=app_password

# Anthropic (opcional, para Agent Orchestrator)
ANTHROPIC_API_KEY=sk-ant-...
```

## 🧪 Verificación post-deployment

```bash
# 1. Salud del servicio
curl http://localhost:5050/login

# 2. Verificar workers activos
curl http://localhost:5050/api/health
# (si no existe, usar la URL anterior)

# 3. Ver logs en vivo
tail -f logs/access.log logs/error.log

# 4. Verificar cache stats (desde admin sesión)
# El cache es interno, ver _cache_stats en la consola si hay log
```

## 🔁 Rollback

Si algo falla en producción, volver al dev server:

```bash
# Detener Gunicorn (Ctrl+C)
# Arrancar dev:
python app.py
```

El dev server **sigue funcionando exactamente igual que antes** — todos los
cambios son aditivos y no rompen retrocompatibilidad.
