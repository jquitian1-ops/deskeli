@echo off
REM TicketDesk Enterprise v2.1 - Inicializar LocalStack
REM
REM Este script inicia LocalStack y crea todos los servicios necesarios

echo.
echo ================================================================================
echo TicketDesk Enterprise v2.1 - INICIALIZAR LOCALSTACK
echo ================================================================================
echo.

cd /d %~dp0

REM Verificar que Docker está corriendo
echo Verificando Docker...
docker ps >/dev/null 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker no está ejecutándose
    echo Inicia Docker Desktop y vuelve a intentar
    pause
    exit /b 1
)

REM Activar venv si existe
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Iniciar LocalStack en background
echo [1/3] Iniciando LocalStack...
docker-compose up -d >/dev/null 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Fallo al iniciar LocalStack
    docker-compose logs
    pause
    exit /b 1
)

echo [OK] LocalStack iniciado
echo.

REM Esperar a que LocalStack esté listo
echo [2/3] Esperando a que LocalStack esté listo...
timeout /t 5 /nobreak >/dev/null

REM Inicializar servicios AWS
echo.
echo [3/3] Inicializando servicios AWS...
python scripts\init_localstack.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================================================
    echo [OK] LocalStack está listo para TicketDesk Enterprise
    echo ================================================================================
    echo.
    echo Servicios disponibles:
    echo   - S3: http://localhost:4566/ticketdesk-attachments
    echo   - DynamoDB: ticketdesk-cache
    echo   - SQS: ticketdesk-tasks
    echo.
    echo Dashboard: http://localhost:4566/_localstack/console
    echo.
    echo Para detener: docker-compose down
    echo Para ver logs: docker-compose logs -f
    echo.
) else (
    echo.
    echo [ERROR] Fallo al inicializar servicios AWS
    echo Ver arriba para más detalles
    echo.
)

pause
