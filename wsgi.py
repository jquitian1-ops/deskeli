#!/usr/bin/env python3
"""
WSGI entry point para Gunicorn
Uso: gunicorn -c gunicorn.conf.py wsgi:app
"""
from dotenv import load_dotenv
load_dotenv()

from app import app, socketio, bootstrap_app

# Inicializar BD + schedulers solo una vez (preload_app=True garantiza una sola ejecución)
bootstrap_app()

# Alias para compatibilidad WSGI
application = app

if __name__ == "__main__":
    socketio.run(app)
