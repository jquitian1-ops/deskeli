@echo off
REM TicketDesk Enterprise v2.1 - LocalStack para desarrollo AWS local
REM
REM Este script inicia LocalStack via Docker Compose
REM Acceso: http://localhost:4566 (LocalStack Gateway)

echo.
echo ================================================================================
echo TicketDesk Enterprise v2.1 - LOCALSTACK (AWS Local)
echo ================================================================================
echo.
echo Iniciando LocalStack con Docker Compose...
echo.
echo Servicios disponibles:
echo   - S3: Almacenamiento de archivos
echo   - DynamoDB: Base de datos NoSQL
echo   - SQS: Colas de mensajes
echo   - SNS: Notificaciones
echo   - Lambda: Funciones sin servidor
echo.
echo LocalStack Gateway: http://localhost:4566
echo Credenciales: AWS_ACCESS_KEY_ID=test, AWS_SECRET_ACCESS_KEY=test
echo.

cd /d %~dp0

docker-compose up -d

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] LocalStack iniciado exitosamente
    echo.
    echo Esperando a que LocalStack esté listo (10 segundos)...
    timeout /t 10 /nobreak
    echo.
    echo [OK] LocalStack está listo
    echo.
    echo Para detener: docker-compose down
    echo Para ver logs: docker-compose logs -f
    echo.
) else (
    echo.
    echo [ERROR] Fallo al iniciar LocalStack
    echo Verificar que Docker Desktop está ejecutándose
    echo.
)

pause
