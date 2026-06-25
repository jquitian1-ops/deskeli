@echo off
chcp 65001 >nul
cls

echo.
echo ========================================
echo   TicketDesk Enterprise
echo ========================================
echo.

REM Crear entorno virtual si no existe
if not exist "venv" (
    echo [*] Creando entorno virtual...
    python -m venv venv
)

REM Activar entorno
echo [*] Activando entorno virtual...
call venv\Scripts\activate.bat

REM Instalar dependencias
echo [*] Instalando dependencias...
pip install -r requirements.txt -q

echo.
echo ========================================
echo   LISTO! Iniciando aplicacion...
echo ========================================
echo.
echo Abre navegador en: http://localhost:5050
echo.
echo Usuarios de prueba:
echo   - john (Empleado)
echo   - carlos (Tecnico)
echo   - ana (Admin)
echo.
echo Presiona CTRL+C para detener
echo.

REM Ejecutar aplicacion
python app.py

pause
