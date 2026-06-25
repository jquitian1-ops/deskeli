# TicketDesk Enterprise - Script de Ejecucion Rapida
# Este script configura e inicia la aplicacion automaticamente

Write-Host "TicketDesk Enterprise - Inicio Rapido" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si Python está instalado
Write-Host "Verificando Python..." -ForegroundColor Yellow
python --version

if ($LASTEXITCODE -ne 0) {
    Write-Host "Python no esta instalado. Descargalo de https://www.python.org/" -ForegroundColor Red
    exit 1
}

# Crear entorno virtual si no existe
if (!(Test-Path "venv")) {
    Write-Host "Creando entorno virtual..." -ForegroundColor Yellow
    python -m venv venv
}

# Activar entorno virtual
Write-Host "Activando entorno virtual..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Instalar dependencias
Write-Host "Instalando dependencias..." -ForegroundColor Yellow
pip install -r requirements.txt -q

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup completado!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Iniciar la aplicación
Write-Host "Iniciando aplicacion..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Accede a: http://localhost:5050" -ForegroundColor Green
Write-Host ""
Write-Host "Usuarios de prueba:" -ForegroundColor Yellow
Write-Host "  - john (Empleado)" -ForegroundColor White
Write-Host "  - carlos (Tecnico)" -ForegroundColor White
Write-Host "  - ana (Admin)" -ForegroundColor White
Write-Host ""
Write-Host "Presiona CTRL+C para detener" -ForegroundColor Gray
Write-Host ""

# Ejecutar la aplicación
python app.py
