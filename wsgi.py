#!/usr/bin/env python3
"""
WSGI entry point para Gunicorn con eventlet.
Uso: gunicorn -c gunicorn.conf.py wsgi:application
"""
# CRITICO: eventlet.monkey_patch() debe correr ANTES de cualquier otro import
# (Flask, SQLAlchemy, threading, socket, ssl, etc.). De lo contrario, eventlet
# no logra parchear los módulos del sistema y se rompe el contexto de Flask.
import eventlet
eventlet.monkey_patch()

from dotenv import load_dotenv
load_dotenv()

from app import app, socketio, bootstrap_app

# Inicializar BD + schedulers solo una vez (preload_app=True garantiza una sola ejecución)
bootstrap_app()

# Alias para compatibilidad WSGI
application = app

if __name__ == "__main__":
    socketio.run(app)
