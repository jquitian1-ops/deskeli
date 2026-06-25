@echo off
REM TicketDesk Enterprise v2.1 - Inicio en MODO DESARROLLO
REM
REM Este script inicia el servidor Flask en modo desarrollo con hot-reload

echo.
echo ================================================================================
echo TicketDesk Enterprise v2.1 - MODO DESARROLLO
echo ================================================================================
echo.
echo Iniciando servidor Flask...
echo Servidor en: http://localhost:5050
echo Hot-reload: HABILITADO
echo.

cd /d %~dp0

REM Activar virtual environment si existe
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo (usando Python del sistema)
)

REM Iniciar Flask
python app.py

pause
