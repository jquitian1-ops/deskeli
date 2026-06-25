# Despliegue de DeskEli en Coolify

Esta guía explica cómo desplegar DeskEli (TicketDesk Enterprise) en Coolify usando
el `Dockerfile` que ya está en el repo.

---

## 1. Archivos relevantes (ya en el repo)

- **`Dockerfile`** — multi-stage, Python 3.11-slim, Gunicorn + eventlet
- **`.dockerignore`** — excluye `.env`, BD, uploads, backups, logs
- **`requirements.txt`** — todas las dependencias Python
- **`wsgi.py`** — entry point WSGI con `bootstrap_app()`
- **`gunicorn.conf.py`** — config Gunicorn (bind 0.0.0.0:5050, eventlet, preload_app)

---

## 2. Configuration en Coolify

### General
| Campo | Valor |
|-------|-------|
| **Build Pack** | `Dockerfile` (NO Nixpacks) |
| **Dockerfile Location** | `/Dockerfile` |
| **Base Directory** | `/` |
| **Ports Exposes** | `5050` |
| **Domains** | `https://deskeli.eliotproyectos.tech` (o el subdominio que uses) |

---

## 3. Volúmenes persistentes (CRÍTICO)

DeskEli guarda datos que **no deben perderse** entre deploys. En Coolify → **Persistent Storage**:

| Mount path | Para qué sirve |
|------------|----------------|
| `/app/instance` | BD SQLite (`ticketdesk_v2.db`) — **NO PERDER** |
| `/app/uploads` | Adjuntos de tickets, subtareas |
| `/app/backups` | Backups cifrados `.db.gz.enc` |
| `/app/logs` | Access/error log de Gunicorn (opcional) |

**Si no configurás estos volúmenes**: cada redeploy borra la BD entera. **No te olvides**.

---

## 4. Variables de entorno (Environment Variables)

Recordá la regla del paso 3 de la guía:
- **Backend (todas las de abajo)** → marcá solo **Runtime**, desmarcá Buildtime.
- Variables con `$` (hashes, contraseñas con símbolos) → marcá **"Is Literal?"**.

### 🔴 Obligatorias

| Nombre | Notas |
|--------|-------|
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | Generar con `python -c "import secrets; print(secrets.token_urlsafe(32))"` — **NUEVA**, no reuses la del .env local |
| `DB_ENCRYPTION_KEY` | Generar con `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` — **GUARDÁ COPIA SEGURA** (si la perdés, secretos y backups quedan irrecuperables) |
| `DATABASE_URL` | `sqlite:////app/instance/ticketdesk_v2.db` (4 barras = ruta absoluta) |
| `ALLOWED_ORIGINS` | Tu dominio real: `https://deskeli.eliotproyectos.tech` (sin `localhost`) |
| `ANTHROPIC_API_KEY` | Tu clave de console.anthropic.com — **REGENERAR** si la local quedó expuesta |
| `TZ` | `America/Bogota` (zona horaria) |

### 🟠 LDAP (una vez que IT habilite LDAPS)

| Nombre | Ejemplo |
|--------|---------|
| `LDAP_SERVER_1` | `ldaps://ad.manufacturaseliiot.local` |
| `LDAP_PORT_1` | `636` |
| `LDAP_BASE_DN_1` | `DC=manufacturaseliiot,DC=local` |
| `LDAP_ADMIN_USER_1` | `serviceaccount@manufacturaseliiot.local` |
| `LDAP_ADMIN_PASSWORD_1` | Contraseña del service account — marcá **"Is Literal?"** si tiene `$` o caracteres especiales |
| `LDAP_SERVER_2/3`, `LDAP_PORT_2/3`, `LDAP_BASE_DN_2/3`, `LDAP_ADMIN_USER_2/3`, `LDAP_ADMIN_PASSWORD_2/3` | Lo mismo para Pash y Primatela |

### 🟠 SMTP (notificaciones por email)

| Nombre | Ejemplo |
|--------|---------|
| `SMTP_SERVER` | `smtp.corporativo.local` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `ticketdesk@corporativo.local` |
| `SMTP_PASSWORD` | Contraseña del buzón — **"Is Literal?"** si aplica |
| `SMTP_USE_TLS` | `True` |
| `SMTP_FROM_EMAIL` | `ticketdesk@corporativo.local` |
| `SMTP_FROM_NAME` | `DeskEli` |

### 🟡 Teams (opcional, alertas)

| Nombre | Ejemplo |
|--------|---------|
| `TEAMS_WEBHOOK_CRITICAL` | `https://outlook.webhook.office.com/...` |
| `TEAMS_WEBHOOK_GENERAL` | `https://outlook.webhook.office.com/...` |

### 🟡 Tuning y seguridad

| Nombre | Default | Notas |
|--------|---------|-------|
| `GUNICORN_BIND` | `0.0.0.0:5050` | No cambies salvo que cambies el puerto expuesto |
| `GUNICORN_WORKERS` | `1` | **Importante**: con SocketIO + eventlet sin sticky session, mantené 1. Si subís a 2+, las WebSocket pueden romperse |
| `MAX_FAILED_LOGIN_ATTEMPTS` | `5` | Lockout de cuenta tras N fallos |
| `LOCKOUT_DURATION_MINUTES` | `15` | Duración del bloqueo |
| `MIN_PASSWORD_LENGTH` | `8` | Política de contraseñas |
| `RATE_LIMIT_REQUESTS` | `120` | Rate limit por IP |
| `JWT_EXPIRATION_HOURS` | `8` | Vida del JWT |
| `BACKUP_RETENTION_DAYS` | `30` | Días que se guardan los backups |

---

## 5. Probar el build local (antes de subir a Coolify)

Si tenés Docker instalado:

```bash
# Desde la carpeta del proyecto
docker build -t deskeli .

# Si compila, correlo (sin volúmenes ni variables → solo verifica que arranca):
docker run --rm -p 5050:5050 \
  -e FLASK_ENV=development \
  -e SECRET_KEY=test_secret_key_for_local_only \
  -e DB_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") \
  -e ALLOWED_ORIGINS=http://localhost:5050 \
  deskeli

# Probá: http://localhost:5050/api/health → debe responder JSON {"status":"healthy",...}
```

Si `docker build` falla, revisá el error y arregalo **antes** de subir a Coolify.

---

## 6. Después del primer Deploy

1. **Verificá el log de Coolify**. Buscá en los últimos renglones:
   ```
   [INFO] Listening at: http://0.0.0.0:5050
   [INFO] Using worker: eventlet
   ```
2. **Healthcheck**: el contenedor debe ponerse en estado **healthy** (verde) en ~40-60s.
3. **Probá el endpoint**: `https://tu-dominio/api/health` debe devolver `{"status":"healthy"}`.
4. **Logueate**: con `ana@eliot.com` / `DeskEli2026!` (te va a pedir cambio de contraseña).

---

## 7. Errores comunes (de la guía + específicos de DeskEli)

| Síntoma | Causa | Solución |
|---------|-------|----------|
| `502 Bad Gateway` permanente | Ports Exposes ≠ 5050 | Poné `5050` en Ports Exposes |
| Login da "Internal server error" tras input correcto | `SECRET_KEY` con `$` que Coolify expandió | Marcá **"Is Literal?"** en SECRET_KEY, o regenerala sin `$` |
| `RuntimeError: SECRET_KEY no está definida` al arrancar | Falta SECRET_KEY en env vars de Coolify | Agregala con un valor fuerte |
| `RuntimeError: DB_ENCRYPTION_KEY no está definida` | Lo mismo con DB_ENCRYPTION_KEY | Agregala con un valor Fernet válido |
| BD vacía después de redeploy | No configuraste el volumen `/app/instance` | Configurá Persistent Storage en Coolify y redeploy |
| Las contraseñas cifradas no se descifran | `DB_ENCRYPTION_KEY` cambió | Restaurá la clave original (guardala en gestor de secretos) |
| LDAP no autentica | Sigue usando `ldap://` | Esperá que IT habilite LDAPS y cambiá las env vars a `ldaps://` puerto 636 |
| WebSocket se desconecta cada N segundos | `GUNICORN_WORKERS > 1` sin sticky session | Bajá a `GUNICORN_WORKERS=1` |

---

## 8. Checklist de pre-deploy

- [ ] `Dockerfile` está en la raíz
- [ ] `.dockerignore` está en la raíz
- [ ] `requirements.txt` está en la raíz y commiteado
- [ ] `wsgi.py` y `gunicorn.conf.py` están en la raíz
- [ ] `.env` está en `.gitignore` (NO se sube)
- [ ] Tenés copia segura de `SECRET_KEY` y `DB_ENCRYPTION_KEY` fuera del servidor
- [ ] Tenés acceso a las credenciales SMTP, LDAP y Anthropic API
- [ ] DNS apunta al servidor de Coolify
- [ ] Ya hiciste `git push` de los cambios a la rama que va a desplegarse

---

*Generado: 2026-06-25*
