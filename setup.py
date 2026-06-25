#!/usr/bin/env python3
"""
TICKETDESK ENTERPRISE v2.1 - SETUP AUTOMÁTICO
Configuración e inicialización de la aplicación
"""

import os
import sys
import subprocess
import secrets
from pathlib import Path

def print_header(text):
    """Imprimir encabezado"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_step(step_num, text):
    """Imprimir paso"""
    print(f"\n[{step_num}] {text}")

def print_success(text):
    """Imprimir éxito"""
    print(f"✅ {text}")

def print_error(text):
    """Imprimir error"""
    print(f"❌ {text}")

def print_warning(text):
    """Imprimir advertencia"""
    print(f"⚠️  {text}")

def check_python_version():
    """Verificar versión de Python"""
    print_step(1, "Verificando Python 3.10+")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python 3.10+ requerido. Tienes: {version.major}.{version.minor}")
        return False

def check_dependencies():
    """Verificar dependencias instaladas"""
    print_step(2, "Verificando dependencias")
    required = ['flask', 'sqlalchemy', 'flask-socketio', 'pyjwt', 'requests']
    missing = []

    for package in required:
        try:
            __import__(package.replace('-', '_'))
            print_success(f"{package} instalado")
        except ImportError:
            print_warning(f"{package} NO instalado")
            missing.append(package)

    if missing:
        print_warning(f"\nFaltan {len(missing)} dependencias. Instalando...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
            print_success("Dependencias instaladas")
            return True
        except subprocess.CalledProcessError:
            print_error("Error instalando dependencias. Ejecuta: pip install -r requirements.txt")
            return False
    return True

def create_env_file():
    """Crear archivo .env si no existe"""
    print_step(3, "Configurando .env")

    env_file = Path('.env')

    if env_file.exists():
        print_warning(".env ya existe. Saltando...")
        return True

    # Generar SECRET_KEY segura
    secret_key = secrets.token_urlsafe(32)

    env_content = f"""# TICKETDESK ENTERPRISE v2.1
FLASK_ENV=production
SECRET_KEY={secret_key}
DEBUG=False
HOST=0.0.0.0
PORT=5050
DATABASE_URL=sqlite:///ticketdesk_v2.db
DATABASE_TIMEOUT=30000
ANTHROPIC_API_KEY=sk-ant-v1-your-api-key-here
LDAP_SERVER_1=ldap://ad.manufacturaseliiot.local
LDAP_BASE_DN_1=DC=manufacturaseliiot,DC=local
BACKUP_DIR=./backups
BACKUP_RETENTION_DAYS=30
"""

    with open(env_file, 'w') as f:
        f.write(env_content)

    print_success(f".env creado con SECRET_KEY segura")
    return True

def create_backup_dir():
    """Crear directorio de backups"""
    print_step(4, "Creando directorio de backups")

    backup_dir = Path('./backups')
    backup_dir.mkdir(exist_ok=True)
    print_success(f"Directorio: {backup_dir.absolute()}")
    return True

def init_database():
    """Inicializar base de datos"""
    print_step(5, "Inicializando base de datos")

    try:
        from app import app, init_db
        with app.app_context():
            init_db()
        print_success("Base de datos inicializada")
        return True
    except Exception as e:
        print_error(f"Error inicializando BD: {str(e)}")
        print_warning("Intenta manualmente: python -c \"from app import app, init_db; app.app_context().push(); init_db()\"")
        return False

def verify_database():
    """Verificar que BD fue creada correctamente"""
    print_step(6, "Verificando base de datos")

    db_file = Path('ticketdesk_v2.db')
    if db_file.exists():
        size_mb = db_file.stat().st_size / (1024*1024)
        print_success(f"BD creada: ticketdesk_v2.db ({size_mb:.2f} MB)")
        return True
    else:
        print_warning("BD no encontrada. Asegúrate que init_db() se ejecutó.")
        return False

def create_startup_script():
    """Crear script de inicio"""
    print_step(7, "Creando script de inicio")

    # Script para Windows (PowerShell)
    ps_script = """# TICKETDESK ENTERPRISE v2.1 - START SERVER
$env:FLASK_ENV = 'production'
python app.py
"""

    # Script para Windows (Batch)
    bat_script = """@echo off
setlocal enabledelayedexpansion
set FLASK_ENV=production
python app.py
pause
"""

    # Script para Unix/Linux
    sh_script = """#!/bin/bash
export FLASK_ENV=production
python app.py
"""

    with open('start_server.ps1', 'w') as f:
        f.write(ps_script)
    print_success("start_server.ps1 creado")

    with open('start_server.bat', 'w') as f:
        f.write(bat_script)
    print_success("start_server.bat creado")

    with open('start_server.sh', 'w') as f:
        f.write(sh_script)
    os.chmod('start_server.sh', 0o755)
    print_success("start_server.sh creado")

    return True

def show_next_steps():
    """Mostrar próximos pasos"""
    print_header("🎉 SETUP COMPLETADO")

    print("""
✅ Pasos completados:
   1. Verificación de Python 3.10+
   2. Instalación de dependencias
   3. Creación de .env
   4. Directorio de backups
   5. Inicialización de base de datos
   6. Verificación de BD
   7. Scripts de inicio

📋 PRÓXIMOS PASOS:

1. EDITAR .env con valores reales:
   - ANTHROPIC_API_KEY (para bot inteligente)
   - LDAP_SERVER_1, LDAP_BASE_DN_1, etc. (para autenticación)
   - SMTP_* (para emails, opcional)
   - TEAMS_WEBHOOK_* (para notificaciones, opcional)

2. INICIAR SERVIDOR:
   PowerShell: .\\start_server.ps1
   Batch:     start_server.bat
   Linux:     ./start_server.sh
   Python:    python app.py

3. ACCEDER A LA APLICACIÓN:
   http://localhost:5050

4. LOGIN CON USUARIOS DE PRUEBA:
   Email: ana@eliot.com
   Contraseña: demo

5. VERIFICAR HEALTH:
   http://localhost:5050/api/health

6. DOCUMENTACIÓN:
   - CONFIGURACION_PRODUCCION.md (setup detallado)
   - README.md (features)
   - DEPLOYMENT_GUIDE.md (producción)

⚠️  IMPORTANTE:
   - Cambiar SECRET_KEY en .env antes de producción
   - Cambiar contraseñas de demo (ana@eliot.com, etc.)
   - Configurar LDAP/AD real
   - Habilitar HTTPS en producción
   - Realizar backup diarios (automático cada 2 AM)

📊 ESTADO DEL SISTEMA:
""")

    try:
        from app import app, db, User, Ticket
        with app.app_context():
            users = db.session.query(User).count()
            tickets = db.session.query(Ticket).count()
            print(f"   - Usuarios en BD: {users}")
            print(f"   - Tickets de ejemplo: {tickets}")
    except:
        print("   - BD no disponible aún")

    print("\n" + "="*70)
    print("¡Listo para iniciar! 🚀")
    print("="*70 + "\n")

def main():
    """Función principal"""
    print_header("TICKETDESK ENTERPRISE v2.1 - SETUP AUTOMÁTICO")

    checks = [
        ("Python version", check_python_version),
        ("Dependencies", check_dependencies),
        (".env file", create_env_file),
        ("Backup directory", create_backup_dir),
        ("Database", init_database),
        ("Database verify", verify_database),
        ("Startup scripts", create_startup_script),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"{name}: {str(e)}")
            results.append((name, False))

    # Resumen
    print("\n" + "="*70)
    print("RESUMEN")
    print("="*70)
    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")

    print(f"\nResult: {passed}/{total} checks passed")

    if passed == total:
        show_next_steps()
        return 0
    else:
        print_warning(f"\n{total - passed} checks fallidos. Revisa los errores arriba.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
