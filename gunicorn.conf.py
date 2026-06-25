"""
Configuración de Gunicorn para TicketDesk Enterprise
Optimizado para Socket.IO con eventlet + 8000 empleados / 100 técnicos.

Uso:
    gunicorn -c gunicorn.conf.py wsgi:app
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
# Con eventlet, cada worker = 1 event-loop que maneja miles de conexiones.
# Con preload_app=True, los schedulers solo arrancan una vez (en el master).
workers = int(os.getenv('GUNICORN_WORKERS', max(2, multiprocessing.cpu_count())))
worker_class = "eventlet"
worker_connections = 2000     # ~2000 conexiones WebSocket concurrentes por worker
max_requests = 1000           # Reciclar workers cada N requests para evitar memory leaks
max_requests_jitter = 50      # Variación aleatoria al reciclar

# ─────────────────────────────────────────────────────────────
# Timeouts
# ─────────────────────────────────────────────────────────────
timeout = 120                 # Mata workers que tarden más de 2 min
keepalive = 5
graceful_timeout = 30         # Tiempo para terminar requests en curso

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
