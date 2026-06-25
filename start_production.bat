@echo off
REM TicketDesk Enterprise v2.1 - Inicio en MODO PRODUCCION
REM
REM Este script inicia el servidor con Gunicorn en produccion
REM Accesible en: http://0.0.0.0:5050 (desde cualquier IP en la red)

echo.
echo ================================================================================
echo TicketDesk Enterprise v2.1 - MODO PRODUCCION
echo ================================================================================
echo.
echo Iniciando servidor con Gunicorn...
echo Puerto: 5050
echo Logs: ./logs/
echo.

cd /d %~dp0

REM Crear carpeta de logs si no existe
if not exist logs mkdir logs

REM Activar virtual environment si existe
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo (usando Python del sistema)
)

REM Iniciar Gunicorn
python -m gunicorn -c gunicorn.conf.py wsgi:app

pause
