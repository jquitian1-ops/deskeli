# DeskEli / TicketDesk Enterprise

Sistema web multi-tenant de gestión de incidencias de TI para **Manufacturas Eliot, Pash y Primatela** (8.000 empleados, 100 técnicos). Backend Flask + Socket.IO, tres portales (empleado / técnico / admin), asignación automática con perfiles de habilidades, SLA en tiempo real, aprobaciones multi-nivel, integración con Anthropic Claude y Microsoft Teams.

**Stack:** Python 3.11 · Flask 3.1 · Flask-SocketIO 5.6 (eventlet) · SQLAlchemy 2.0 · SQLite (dev) / PostgreSQL 14+ (prod) · Gunicorn · Docker · Coolify

---

## Índice

1. [Arquitectura](#arquitectura)
2. [Modelo de datos](#modelo-de-datos)
3. [Estructura del repositorio](#estructura-del-repositorio)
4. [Setup local (desarrollo)](#setup-local-desarrollo)
5. [Setup producción (Gunicorn + Docker)](#setup-producción-gunicorn--docker)
6. [Variables de entorno](#variables-de-entorno)
7. [Autenticación](#autenticación)
8. [Real-time (Socket.IO)](#real-time-socketio)
9. [Schedulers y jobs en background](#schedulers-y-jobs-en-background)
10. [Seguridad](#seguridad)
11. [Testing](#testing)
12. [Despliegue en Coolify](#despliegue-en-coolify)
13. [Troubleshooting](#troubleshooting)
14. [Roadmap](#roadmap)

---

## Arquitectura

```
┌──────────────────────────────────────────────────────────────────┐
│                     Cliente (Chrome/Edge 100+)                   │
│  Portal Empleado · Portal Técnico · Portal Admin (Jinja2 + JS)   │
│              Socket.IO client · session_guard.js                 │
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTPS + WSS
┌──────────────────────────┴───────────────────────────────────────┐
│               Coolify (Traefik proxy + healthcheck)              │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────────────┐
│         Contenedor app — python:3.11-slim + Gunicorn             │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │   Gunicorn (N workers · eventlet · preload_app=True)     │   │
│   │                                                          │   │
│   │   ┌────────────────────────────────────────────────┐     │   │
│   │   │  Flask app (app.py — 20k líneas)               │     │   │
│   │   │   · 230+ rutas HTTP                            │     │   │
│   │   │   · Flask-SocketIO (salas por company_id)      │     │   │
│   │   │   · SQLAlchemy 2.0 (32+ modelos)               │     │   │
│   │   │   · JWT + blacklist JTI + rate limiting        │     │   │
│   │   │   · Schedulers (auto-close, escalation, ping)  │     │   │
│   │   └────────────────────────────────────────────────┘     │   │
│   └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│   Volúmenes montados:                                            │
│     /app/instance    · SQLite DB (o pool PG externo)             │
│     /app/uploads     · Adjuntos de tickets/subtareas             │
│     /app/backups     · Snapshots cifrados (Fernet)               │
│     /app/logs        · access.log / error.log de Gunicorn        │
└──────────────────────────┬───────────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
   PostgreSQL 14+                    Servicios externos:
   (managed en Coolify)              · Anthropic Claude API (bot)
                                     · Microsoft Teams webhooks
                                     · Microsoft Entra ID (OAuth 2.0)
                                     · LDAP/AD por empresa (legacy)
                                     · SMTP + IMAP (correo)
```

### Segregación multi-tenant

**Regla de oro:** cada consulta filtra por `company_id` del usuario autenticado. Sin excepciones. Esto se aplica en:
- Endpoints HTTP (decorador de autorización lee `current_user.company_id`)
- Búsqueda FTS5 (índice respeta company)
- Salas Socket.IO (`join_room(f"company_{company_id}")`)
- Reportes, exports, dashboards y auditoría

### Patrones críticos

- **Optimistic locking:** cada `Ticket` tiene columna `version`. Los updates hacen `WHERE version = expected_version`; en conflicto devuelven HTTP 409 y el cliente reintenta con backoff exponencial (100/200/400/800 ms, máx 4 intentos).
- **JWT blacklist:** logout registra el `jti` en `token_blacklist`. Cada request autenticado verifica el JTI (lookup cacheado <5 ms). Auto-purga entradas expiradas cada hora.
- **Sesiones únicas por rol:** un usuario solo puede tener una sesión activa por portal (empleado/técnico/admin). Nuevo login invalida la anterior. Timeout de inactividad 15 min + aviso 60 s vía `session_guard.js`.

---

## Modelo de datos

**32+ modelos SQLAlchemy** en `app.py`. Los más importantes:

### Núcleo

| Modelo | Propósito |
|---|---|
| `Company` | Tenants: Manufacturas Eliot / Pash / Primatela |
| `User` | Usuarios con `role` ∈ {admin, technician, employee} + `company_id` |
| `Ticket` | Incidencia; `version` (optimistic lock), `resolution_note`, `resolved_by_id` |
| `Message` | Chat empleado↔técnico dentro del ticket |
| `Subtask` | Subtareas asignables independientemente; propio `resolution_note` |
| `TicketAttachment` / `SubtaskAttachment` | Adjuntos (con compresión opcional) |

### Auth & sesión

| Modelo | Propósito |
|---|---|
| `TokenBlacklist` | JTI revocados; auto-purge horario |
| `UserSession` | Registro de sesiones (last_login, is_active_session, was_kicked) |
| `ApiKey` | Tokens `dsk_t_*` para integraciones (rate-limited por token) |
| `AuditLog` | Todo evento sensible (login, backup, kick, config change) |

### Asignación automática

| Modelo | Propósito |
|---|---|
| `TechnicianProfile` | Habilidades, `skill_levels`, `max_tickets`, `is_available` |
| `Guion` / `GuionSubtask` / `UserGuion` | Plantillas de subtareas asignadas a un pool de técnicos (round-robin M:N) |
| `AgentAction` | Auditoría de decisiones del orquestador (agents.py) |

### Workflows

| Modelo | Propósito |
|---|---|
| `ApprovalWorkflow` | Reglas: match por categoría/prioridad/plantilla → cadena ordenada de aprobadores |
| `Approval` | Instancia de aprobación pendiente/aprobada/rechazada |
| `Template` | 8 plantillas pre-construidas + custom por empresa |
| `Tag` | Categorías de problema con color |

### Integraciones / infraestructura

| Modelo | Propósito |
|---|---|
| `MailboxConfig` / `MailboxEmail` | IMAP+SMTP+XOAUTH2 → crea tickets desde correo |
| `Webhook` | Endpoints Teams por evento configurables |
| `Server` / `ServerPingLog` | Monitoreo de servidores críticos (SAP, AD, mail...) |
| `BotKnowledge` / `KnowledgeArticle` | Base de conocimiento + FAQ del bot |
| `TimeEntry` | Time tracking manual y automático (start on `in_progress`) |
| `ReportRecipient` | Destinatarios de reportes periódicos |
| `Config` | Key-value store para settings admin-editables |

---

## Estructura del repositorio

```
proyecto_funcionando/
├── app.py                       # Aplicación Flask (~20k LOC · 32 modelos · 230+ rutas)
├── agents.py                    # AgentAssignor + orquestador de asignación IA
├── ldap_auth.py                 # Autenticación LDAP/AD por empresa (legacy)
├── microsoft_auth.py            # OAuth 2.0 con MSAL (Entra ID)
├── password_policy.py           # Validación de contraseñas
├── crypto_utils.py              # Cifrado Fernet para secretos y backups
├── file_compression.py          # Compresión gzip de adjuntos
├── reports_gen.py               # Generación de PDF (reportlab) + Excel (openpyxl)
│
├── wsgi.py                      # Entry point Gunicorn (monkey_patch + bootstrap)
├── gunicorn.conf.py             # Config workers/eventlet/timeouts/logs
├── requirements.txt             # Dependencias Linux (curadas)
├── Dockerfile                   # Multi-stage build (builder + runtime)
├── docker-compose.yml           # Stack local con PostgreSQL
├── docker-compose.localstack.yml# LocalStack para desarrollo AWS
│
├── start_dev.bat                # Windows: arranque desarrollo
├── start_production.bat         # Windows: arranque Gunicorn producción
├── start_server.sh              # Linux: arranque producción
├── install-systemd.sh           # Instala servicio systemd
├── ticketdesk.service           # Unit de systemd
├── ticketdesk-scheduler.service # Unit del scheduler separado (opcional)
│
├── templates/
│   ├── login.html · login_v2.html
│   ├── force_change_password.html
│   ├── admin/
│   │   ├── dashboard.html            # KPIs · Kanban · gráficas
│   │   ├── tickets.html · orchestrator.html
│   │   ├── config.html · config_new.html  # 13 secciones config
│   │   ├── approvals.html            # Workflow builder
│   │   ├── sessions.html             # Sesiones activas + kick
│   │   ├── time_tracking.html · csat.html · kb.html · themes.html
│   ├── technician/
│   │   ├── dashboard.html            # Cola · SLA · timer
│   │   ├── ticket.html · ticket_detail.html · subtask.html · create.html
│   └── employee/
│       ├── dashboard.html · create_ticket.html · ticket_detail.html
│
├── static/
│   ├── js/
│   │   ├── session_guard.js          # Timeout · fetch wrapper · retry · toast cooldown
│   │   └── devtools_blocker.js       # Anti-devtools básico
│   ├── realtime.js · i18n.js · timeout.js · chart.min.js
│   ├── img/ · manuales/ · marketing/ · ejemplos/
│
├── scripts/
│   ├── migrate_sqlite_to_postgres.py
│   ├── migrate_encrypt_secrets.py
│   ├── import_bot_templates.py · export_bot_templates.py
│   ├── restore_backup.py
│   ├── seed_role_procesos.py · seed_template_solicitud_usuario.py
│   └── postgres-init.sql
│
├── tests/                        # pytest · test_auth · test_sla · test_security · e2e
├── terraform/                    # IaC para AWS (documentado, no en uso activo)
├── docs/                         # Documentación técnica adicional
│
├── openapi.yaml · openapi_complete.yaml  # Especificación OpenAPI
├── DEPLOY_COOLIFY.md             # Instrucciones detalladas Coolify
├── PRODUCCION.md                 # Checklist producción
│
└── instance/    uploads/    backups/    logs/   # Volúmenes (Docker: montados)
```

---

## Setup local (desarrollo)

**Requisitos:** Python 3.10+ · pip · (opcional) Docker Desktop

```bash
# 1. Crear venv e instalar dependencias
python -m venv venv
venv\Scripts\activate                # Windows PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Configurar .env
copy .env.example .env               # o crear a mano; ver sección "Variables de entorno"

# 3. Arrancar servidor de desarrollo
python app.py                        # equivale a socketio.run(app) en modo debug
# → http://localhost:5050
```

En primer arranque, `init_db()` crea el esquema, ejecuta las migraciones idempotentes (`migrate_*`) y siembra los usuarios demo si `ENABLE_DEMO_MODE=true`.

**Usuarios demo** (solo cuando `ENABLE_DEMO_MODE=true`):

| Usuario | Rol | Empresa |
|---|---|---|
| `ana`    | admin | Manufacturas Eliot |
| `carlos` | technician | Manufacturas Eliot |
| `john`   | employee | Manufacturas Eliot |

En producción todos los usuarios se aprovisionan por LDAP/OAuth o desde el panel admin.

---

## Setup producción (Gunicorn + Docker)

### Local con Gunicorn (Windows)

```bat
start_production.bat
```

Equivale a:

```bash
gunicorn -c gunicorn.conf.py wsgi:application
```

Configuración (`gunicorn.conf.py`):
- `worker_class = "eventlet"` (obligatorio para Socket.IO)
- `workers = max(2, cpu_count())` — configurable con `GUNICORN_WORKERS`
- `worker_connections = 2000` conexiones WebSocket por worker
- `max_requests = 1000` con jitter — recicla workers para evitar memory leaks
- `preload_app = True` — schedulers arrancan una sola vez en el master

### Docker

```bash
# Build
docker build -t deskeli:latest .

# Run standalone
docker run -d --name deskeli \
  -p 5050:5050 \
  -v $(pwd)/instance:/app/instance \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/backups:/app/backups \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  deskeli:latest

# O con docker-compose (incluye PostgreSQL)
docker compose up -d
```

El `Dockerfile` es **multi-stage** (builder con `gcc`/`libpq-dev` → runtime slim con solo `libpq5`, `libffi8`, `postgresql-client`). Usuario no-root `deskeli:1000`. Healthcheck HTTP contra `/api/health` cada 30 s.

---

## Variables de entorno

Archivo `.env` en la raíz. **Nunca commitear.** Claves esenciales:

```bash
# Flask
FLASK_ENV=production                 # development activa cookies HTTP (solo localhost)
SECRET_KEY=<secrets.token_urlsafe(32)>
DEBUG=False
HOST=0.0.0.0
PORT=5050

# Base de datos (Postgres en prod, SQLite en dev)
DATABASE_URL=postgresql://user:pass@host:5432/deskeli
# DATABASE_URL=sqlite:///ticketdesk_v2.db
DATABASE_TIMEOUT=30000

# CORS · agregar todos los orígenes internos
ALLOWED_ORIGINS=http://10.161.55.5:5050,https://deskeli.tudominio.com

# Cifrado en reposo (secretos IMAP/OAuth/LDAP en BD + backups)
# Generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
DB_ENCRYPTION_KEY=<base64-32bytes>

# Sesión y auth
JWT_EXPIRATION_HOURS=8
SESSION_TIMEOUT_MINUTES=15
SESSION_WARNING_SECONDS=60
TOKEN_BLACKLIST_CLEANUP_INTERVAL_HOURS=1
RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_MINUTES=1

# LDAP (uno por empresa: _1 Eliot · _2 Pash · _3 Primatela)
LDAP_SERVER_1=ldap://ad.manufacturaseliiot.local
LDAP_PORT_1=389
LDAP_BASE_DN_1=DC=manufacturaseliiot,DC=local
LDAP_ADMIN_USER_1=serviceaccount@manufacturaseliiot.local
LDAP_ADMIN_PASSWORD_1=<cifrada>

# Microsoft Entra ID (OAuth 2.0)
AZURE_CLIENT_ID=...
AZURE_TENANT_ID=...
AZURE_CLIENT_SECRET=...

# Anthropic Claude (bot)
ANTHROPIC_API_KEY=sk-ant-api03-...

# Teams webhooks
TEAMS_WEBHOOK_CRITICAL=https://outlook.webhook.office.com/...
TEAMS_WEBHOOK_GENERAL=https://outlook.webhook.office.com/...

# SMTP (notificaciones salientes)
SMTP_SERVER=smtp.corporativo.local
SMTP_PORT=587
SMTP_USER=deskeli@corporativo.local
SMTP_PASSWORD=<cifrada>
SMTP_USE_TLS=True

# Backup
BACKUP_DIR=/app/backups
BACKUP_RETENTION_DAYS=30

# Monitoreo de servidores (RF-03-11)
SERVER_MONITORING_INTERVAL_MINUTES=5
SERVER_PING_TIMEOUT_SECONDS=5

# Gunicorn
GUNICORN_BIND=0.0.0.0:5050
GUNICORN_WORKERS=2                  # 1 requerido si usás schedulers sin preload_app
GUNICORN_LOG_LEVEL=info
```

⚠️ **El `.env` del repo contiene secretos reales de desarrollo.** Antes de cualquier despliegue público, **rotar**: `SECRET_KEY`, `DB_ENCRYPTION_KEY`, `ANTHROPIC_API_KEY`, contraseñas LDAP.

---

## Autenticación

Se soportan **tres modos** simultáneos, elegidos por endpoint de login:

### 1. Local (usuario/contraseña)
- Hash: `bcrypt` con salt por usuario
- Política configurable (longitud, complejidad) en `password_policy.py`
- Endpoint `/api/login` retorna JWT con claim `jti`

### 2. LDAP / Active Directory
- Config por empresa vía `LDAP_SERVER_N`
- `ldap_auth.py` valida bind + pertenencia a grupo → mapea a `role`
- El primer login crea o actualiza el `User` local

### 3. Microsoft Entra ID (OAuth 2.0)
- MSAL con flow `authorization code`
- `microsoft_auth.py` maneja `/auth/microsoft/login` y `/auth/microsoft/callback`
- Group claims → rol interno

### JWT + blacklist

```
Login → server firma JWT con jti único → cliente lo guarda en cookie httpOnly
Request → server valida firma + verifica JTI contra tabla token_blacklist
Logout → server inserta JTI en blacklist con TTL = exp del token
Kick admin → inserta JTI en blacklist inmediatamente
```

Lookup <5 ms gracias a índice + cacheo. Purga horaria de entradas expiradas.

---

## Real-time (Socket.IO)

- Cada usuario autenticado se une a la sala `company_{company_id}`
- Eventos emitidos:
  - `ticket_created` · `ticket_updated` · `ticket_closed`
  - `subtask_updated` · `sla_escalated` · `sla_warning`
  - `user_kicked` · `session_expired`
  - `server_down` · `server_recovered`
- Latencia objetivo: propagación <3 s
- Heartbeat cliente: ping cada 60 s; server desconecta sesiones inactivas 15 min + aviso 60 s
- Reconexión automática al cerrar el WebSocket

`session_guard.js` implementa:
- Wrapper de `fetch()` con retry-once en GET (500 ms delay)
- Endpoints silenciosos (no muestran toast de error): `/api/session/ping`, `/api/admin/sidebar-counts`, `/api/health`
- Cooldown de 15 s entre toasts "Sin conexión"

---

## Schedulers y jobs en background

Todos arrancan en `bootstrap_app()` (invocado desde `wsgi.py`). Con `preload_app=True` corren solo una vez en el proceso master.

| Scheduler | Intervalo | Función |
|---|---|---|
| SLA escalation | 5 min | Escala a 50%/100%/200% del SLA · cambia color · dispara webhooks Teams |
| Auto-close resolved tickets | 30 min | Cierra tickets en `resolved` sin actividad 24h |
| Auto-close resolved subtasks | 30 min | Cierra subtareas en `resolved` sin actividad 24h |
| Server ping | 5 min | Ping servidores críticos · registra `ServerPingLog` con latencia · genera ticket crítico si cae |
| Purge server ping logs | Diario | Retiene 90 días |
| Token blacklist cleanup | 1 h | Borra JTIs expirados |
| Backup diario | 02:00 UTC | `pg_dump` (Postgres) o snapshot JSON.gz (SQLite) · cifrado Fernet · retención 30 días |
| Mailbox poller | 2 min | (deferred) IMAP → crear ticket automáticamente |
| Reportes periódicos | Cron | (deferred) Quincenal/mensual/anual a `ReportRecipient` |

### Watchdog

Si detecta 3 timeouts consecutivos de BD, registra `system_log` y hace `sys.exit(1)`. Docker/systemd/Coolify reinicia el contenedor. Si hay >5 restarts en 1 h → alerta a admin (indica problema sistémico).

---

## Seguridad

- **RBAC** por rol (admin/technician/employee) + subroles custom (ej. PROCESOS) via `Subrole`/`UserSubrole`
- **Cifrado en reposo:** contraseñas IMAP/SMTP/LDAP_bind/OAuth secrets en BD cifradas con Fernet (`DB_ENCRYPTION_KEY`)
- **Backups cifrados:** JSON.gz + Fernet · verificar restore trimestral
- **Sanitización HTML:** `bleach` en descripciones y comentarios de tickets
- **SQL:** consultas parametrizadas con SQLAlchemy exclusivamente
- **Rate limiting:** por IP (respeta `X-Forwarded-For` detrás de Traefik) · exempt list para endpoints de polling
- **Auditoría:** tabla `AuditLog` con IP, timestamp, usuario, company; retención 12 meses
- **CSRF:** Flask-WTF en formularios; APIs usan JWT + verificación de origen
- **Headers:** CSP/HSTS/X-Frame-Options aplicados en respuestas
- **Password policy:** en `password_policy.py` (integración AD bypassa)

---

## Testing

```bash
# Toda la suite
pytest

# Módulo específico
pytest tests/test_tickets.py

# Test individual
pytest tests/test_auth.py::test_ldap_login_success

# Con cobertura
pytest --cov=. tests/
```

Suites disponibles:
- `test_auth.py` — login local · LDAP · JWT · blacklist
- `test_tickets.py` — CRUD · optimistic locking · segregación company
- `test_sla.py` — escalación · umbrales de color · timers
- `test_security.py` — SQL injection · XSS · CSRF · rate limiting · session hijack
- `test_webhooks_bot.py` — Teams delivery · endpoint bot Claude
- `test_missing_critical.py` — casos de borde detectados en pentest
- `tests/e2e/` — pruebas end-to-end de flujos completos

---

## Despliegue en Coolify

Detalles completos en [`DEPLOY_COOLIFY.md`](./DEPLOY_COOLIFY.md).

Resumen:

1. Coolify → **New Resource → Application** desde el repo Git
2. Build type: **Dockerfile** (usa el multi-stage del repo)
3. Environment: pegar `.env` completo (ver variables arriba)
4. Persistent volumes:
   - `/app/instance` → volumen managed
   - `/app/uploads` → volumen managed
   - `/app/backups` → volumen managed
   - `/app/logs` → volumen managed (opcional)
5. Networks: conectar al servicio PostgreSQL managed
6. Domain: `deskeli.tudominio.com` (Traefik + certificado Let's Encrypt automático)
7. Healthcheck: `/api/health` cada 30 s

Cada push a `main` dispara redeploy automático.

---

## Troubleshooting

### HTTP 503 desde `https://deskeli.tudominio.com`

El proxy Traefik responde pero no encuentra backend sano. Diagnosticar:

```bash
docker ps -a --format "table {{.Names}}\t{{.Status}}"
docker logs <container_name> --tail 200 --timestamps
docker inspect <container_name> --format='RestartCount={{.RestartCount}} | ExitCode={{.State.ExitCode}} | OOMKilled={{.State.OOMKilled}} | Health={{.State.Health.Status}}'
```

Causas típicas:
- Worker eventlet crashea por excepción no capturada → revisar `logs/error.log`
- Healthcheck agresivo mata el container durante init (aumentar `start_period`)
- OOM del proceso (no del host) por leak → `max_requests=1000` ya mitiga

### Backup falla con "BD no encontrada en None"

`DATABASE_URL` no está en `postgres://` y `_get_db_file_path()` devolvió None. Verificar `.env` cargado en el proceso Gunicorn.

### Rate limit 429 excesivo detrás de proxy

Todos los clientes comparten IP del proxy. Verificar que `_real_client_ip()` lee `X-Forwarded-For` (Traefik lo setea por default).

### Toast "Sin conexión" durante redeploy

Es esperado durante rolling updates (~2 min). El wrapper de `session_guard.js` reintenta GET una vez y aplica cooldown de 15 s entre toasts.

### Servidor local (Windows) se cierra al cerrar PowerShell

```powershell
# Arrancar detached
Start-Process python -ArgumentList "app.py" -WindowStyle Hidden -PassThru |
  ForEach-Object { $_.Id | Out-File logs\app.pid }
```

### Localstack (desarrollo AWS)

```bash
start_localstack.bat        # Windows
./scripts/localstack-init.sh
```

Emula S3, DynamoDB, SQS, Lambda. Config `USE_LOCALSTACK=true` en `.env`.

---

## Roadmap

**Pre-lanzamiento (pendientes):**
- [ ] Auto-arranque del mailbox IMAP poller en `bootstrap_app()`
- [ ] Cron scheduler de reportes periódicos (quincenal/mensual/anual)

**Post-lanzamiento (v2.2+):**
- [ ] Push notifications configurables (8 toggles)
- [ ] Integración Slack (adicional a Teams)
- [ ] Auditoría campo-por-campo en `Ticket.updated_at`
- [ ] Export de KB para fine-tuning de Claude
- [ ] Analytics avanzado (burndown charts, heatmaps)
- [ ] Prueba trimestral de restore de backup

---

## Referencias

- **CLAUDE.md** — Guía para asistentes IA · patrones críticos · decisiones de arquitectura
- **DEPLOY_COOLIFY.md** — Playbook de despliegue producción
- **PRODUCCION.md** — Checklist pre-lanzamiento
- **openapi.yaml** — Especificación OpenAPI 3.0 completa
- **terraform/** — IaC para AWS (documentado, no en producción)
- **TICKETS-MANUFACTURAS/** — Requerimientos v2.1 · entrevistas · product vision

---

*DeskEli / TicketDesk Enterprise · Última actualización README: 2026-07-27*
