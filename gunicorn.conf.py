"""
Configuración de Gunicorn para TicketDesk Enterprise / DeskEli
Optimizado para Socket.IO con eventlet + carga objetivo 4000 conexiones concurrentes.

Uso:
    gunicorn -c gunicorn.conf.py wsgi:app

Notas de escala:
    - Eventlet corre miles de green-threads en 1 solo worker sin problema.
    - Con multi-worker + Socket.IO se necesitaría un message queue (Redis)
      para que los broadcasts lleguen a todos los clientes, o sticky sessions
      en el reverse proxy. Por eso el default es 1 worker.
    - Para pasar de 4000 conexiones subí GUNICORN_WORKER_CONNECTIONS en .env.
"""
import os
import multiprocessing

# ─────────────────────────────────────────────────────────────
# Bind
# ─────────────────────────────────────────────────────────────
bind = os.getenv('GUNICORN_BIND', '0.0.0.0:5050')

# ─────────────────────────────────────────────────────────────
# Workers
# ─────────────────────────────────────────────────────────────
# Con eventlet, cada worker = 1 event-loop cooperativo que maneja miles de
# conexiones. Preferimos 1 worker (sin Redis pubsub para Socket.IO).
# Override con GUNICORN_WORKERS si tenés sticky sessions + queue configurados.
workers = int(os.getenv('GUNICORN_WORKERS', '1'))
worker_class = "eventlet"

# Objetivo: 4000 conexiones concurrentes con margen (5000). Cada conexión
# WebSocket + tráfico HTTP cuenta hacia este techo.
worker_connections = int(os.getenv('GUNICORN_WORKER_CONNECTIONS', '5000'))

# Reciclaje de workers para evitar memory leaks acumulados.
# NOTA: para eventlet + Socket.IO subimos max_requests porque cada broadcast
# no cuenta como request pero cada request HTTP sí, y no queremos ciclos frecuentes.
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', '10000'))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', '500'))

# ─────────────────────────────────────────────────────────────
# Timeouts
# ─────────────────────────────────────────────────────────────
timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))     # mata worker si tarda >2 min
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', '5'))
graceful_timeout = 30                                    # espera 30s para requests en curso

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)
accesslog = os.path.join(LOGS_DIR, 'access.log')
errorlog = os.path.join(LOGS_DIR, 'error.log')
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# ─────────────────────────────────────────────────────────────
# Preload app
# ─────────────────────────────────────────────────────────────
# Los schedulers SOLO se inicializan una vez gracias al flag _bootstrapped.
preload_app = True

# ─────────────────────────────────────────────────────────────
# Process naming
# ─────────────────────────────────────────────────────────────
proc_name = "ticketdesk"
daemon = False
pidfile = None
umask = 0
