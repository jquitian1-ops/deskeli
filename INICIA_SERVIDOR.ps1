# ============================================================
# SCRIPT PARA INICIAR TICKETDESK ENTERPRISE v2.1
# ============================================================

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  INICIANDO TICKETDESK ENTERPRISE v2.1" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Cambiar a directorio del proyecto
Set-Location "C:\Users\jquitian\proyecto_funcionando"

# Mostrar información
Write-Host "Directorio: $(Get-Location)" -ForegroundColor Green
Write-Host "Python: $(python --version)" -ForegroundColor Green
Write-Host ""

# Verificar que app.py existe
if (Test-Path "app.py") {
    Write-Host "app.py encontrado" -ForegroundColor Green
} else {
    Write-Host "ERROR: app.py no encontrado" -ForegroundColor Red
    exit 1
}

# Verificar que requirements.txt existe
if (Test-Path "requirements.txt") {
    Write-Host "requirements.txt encontrado" -ForegroundColor Green
} else {
    Write-Host "ERROR: requirements.txt no encontrado" -ForegroundColor Red
    exit 1
}

# Verificar que BD existe
if (Test-Path "ticketdesk_v2.db") {
    Write-Host "Base de datos encontrada" -ForegroundColor Green
} else {
    Write-Host "ADVERTENCIA: Base de datos no encontrada" -ForegroundColor Yellow
    Write-Host "Se creara una nueva al iniciar..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  INICIANDO SERVIDOR FLASK" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "El servidor estara disponible en:" -ForegroundColor Yellow
Write-Host "  HTTP:  http://localhost:5050" -ForegroundColor Yellow
Write-Host "  HTTPS: https://localhost:5050 (con certificado auto-firmado)" -ForegroundColor Yellow
Write-Host ""

Write-Host "USUARIOS DE PRUEBA DISPONIBLES:" -ForegroundColor Yellow
Write-Host "  Empleado (Eliot):" -ForegroundColor White
Write-Host "    - Usuario: john_eliot" -ForegroundColor Cyan
Write-Host "    - Contraseña: demo" -ForegroundColor Cyan
Write-Host "  Tecnico (Eliot):" -ForegroundColor White
Write-Host "    - Usuario: carlos_eliot" -ForegroundColor Cyan
Write-Host "    - Contraseña: demo" -ForegroundColor Cyan
Write-Host "  Admin (Eliot):" -ForegroundColor White
Write-Host "    - Usuario: ana_eliot" -ForegroundColor Cyan
Write-Host "    - Contraseña: demo" -ForegroundColor Cyan
Write-Host ""

Write-Host "  EMPRESAS DISPONIBLES:" -ForegroundColor White
Write-Host "    1. Manufactureras Eliot (eliot)" -ForegroundColor Cyan
Write-Host "    2. Pash (pash)" -ForegroundColor Cyan
Write-Host "    3. Primatela (primatela)" -ForegroundColor Cyan
Write-Host ""

Write-Host "Presiona Ctrl+C para detener el servidor" -ForegroundColor Yellow
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Iniciar servidor
python app.py
