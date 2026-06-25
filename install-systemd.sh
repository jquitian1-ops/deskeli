#!/bin/bash
# ============================================================================
# Script de instalación - Systemd services para TicketDesk
# Uso: sudo bash install-systemd.sh
# ============================================================================

set -euo pipefail

echo "=========================================="
echo "Instalación de TicketDesk con Systemd"
echo "=========================================="

# Verificar que se ejecuta como root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Este script debe ejecutarse con sudo"
    exit 1
fi

PROJECT_DIR="/opt/ticketdesk"
APP_USER="ticketdesk"

# ============================================================================
# 1. Crear usuario ticketdesk
# ============================================================================
echo "Creando usuario $APP_USER..."
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash -d /home/$APP_USER $APP_USER
    echo "✓ Usuario $APP_USER creado"
else
    echo "✓ Usuario $APP_USER ya existe"
fi

# ============================================================================
# 2. Crear directorios
# ============================================================================
echo "Creando directorios..."
mkdir -p /var/log/ticketdesk
mkdir -p $PROJECT_DIR/backups
mkdir -p $PROJECT_DIR/instance
mkdir -p $PROJECT_DIR/certs
mkdir -p $PROJECT_DIR/logs

chown -R $APP_USER:$APP_USER /var/log/ticketdesk
chown -R $APP_USER:$APP_USER $PROJECT_DIR

echo "✓ Directorios creados"

# ============================================================================
# 3. Instalar dependencias del sistema
# ============================================================================
echo "Instalando dependencias del sistema..."
apt-get update
apt-get install -y \
    python3-pip \
    python3-venv \
    postgresql-client \
    git \
    curl \
    wget \
    nginx \
    certbot \
    python3-certbot-nginx

echo "✓ Dependencias instaladas"

# ============================================================================
# 4. Instalar dependencias Python
# ============================================================================
echo "Instalando dependencias Python..."
cd $PROJECT_DIR
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    echo "✓ Entorno virtual creado"
else
    source venv/bin/activate
    pip install --upgrade -r requirements.txt
    echo "✓ Dependencias Python actualizadas"
fi

# ============================================================================
# 5. Copiar archivos systemd
# ============================================================================
echo "Instalando servicios systemd..."
cp ticketdesk.service /etc/systemd/system/
cp ticketdesk-scheduler.service /etc/systemd/system/

chmod 644 /etc/systemd/system/ticketdesk*.service

# Recargar systemd
systemctl daemon-reload
echo "✓ Servicios systemd instalados"

# ============================================================================
# 6. Instalar Nginx
# ============================================================================
echo "Configurando Nginx..."
cp nginx-ticketdesk.conf /etc/nginx/sites-available/ticketdesk
ln -sf /etc/nginx/sites-available/ticketdesk /etc/nginx/sites-enabled/

# Verificar configuración
if nginx -t; then
    systemctl restart nginx
    echo "✓ Nginx configurado"
else
    echo "⚠ Error en configuración Nginx"
fi

# ============================================================================
# 7. Crear certificado auto-firmado (desarrollo)
# ============================================================================
echo "Creando certificado SSL..."
if [ ! -f "$PROJECT_DIR/certs/fullchain.pem" ]; then
    openssl req -x509 -newkey rsa:4096 -nodes \
        -out $PROJECT_DIR/certs/fullchain.pem \
        -keyout $PROJECT_DIR/certs/privkey.pem \
        -days 365 \
        -subj "/C=CO/ST=Bogota/L=Bogota/O=TicketDesk/CN=ticketdesk.local"

    chown $APP_USER:$APP_USER $PROJECT_DIR/certs/*
    chmod 600 $PROJECT_DIR/certs/*
    echo "✓ Certificado auto-firmado creado"
else
    echo "✓ Certificado ya existe"
fi

# ============================================================================
# 8. Inicializar base de datos
# ============================================================================
echo "Inicializando base de datos..."
cd $PROJECT_DIR
source venv/bin/activate

python3 -c "
from app import app, init_db
app.app_context().push()
init_db()
print('✓ Base de datos inicializada')
" || echo "⚠ BD ya inicializada"

# ============================================================================
# 9. Habilitar servicios
# ============================================================================
echo "Habilitando servicios systemd..."
systemctl enable ticketdesk.service
systemctl enable ticketdesk-scheduler.service
echo "✓ Servicios habilitados"

# ============================================================================
# 10. Iniciar servicios
# ============================================================================
echo "Iniciando servicios..."
systemctl start ticketdesk.service
systemctl start ticketdesk-scheduler.service

# Esperar a que inicie
sleep 3

# Verificar estado
if systemctl is-active --quiet ticketdesk; then
    echo "✓ TicketDesk iniciado"
else
    echo "⚠ Error al iniciar TicketDesk"
    systemctl status ticketdesk
fi

# ============================================================================
# 11. Configurar logrotate
# ============================================================================
echo "Configurando logrotate..."
cat > /etc/logrotate.d/ticketdesk << 'EOF'
/var/log/ticketdesk/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 ticketdesk ticketdesk
    sharedscripts
    postrotate
        systemctl reload ticketdesk >/dev/null 2>&1 || true
    endscript
}
EOF
echo "✓ Logrotate configurado"

# ============================================================================
# 12. Configurar cron para backups
# ============================================================================
echo "Configurando backups automáticos..."
cat > /home/$APP_USER/backup-cron << 'EOF'
# Backup diario a las 2 AM
0 2 * * * cd /opt/ticketdesk && bash backup.sh >> /var/log/ticketdesk/backup.log 2>&1
EOF

# Instalar en crontab de ticketdesk
crontab -u $APP_USER /home/$APP_USER/backup-cron
rm /home/$APP_USER/backup-cron
echo "✓ Backups automáticos configurados"

# ============================================================================
# Resumen Final
# ============================================================================
echo ""
echo "=========================================="
echo "✓ Instalación completada exitosamente"
echo "=========================================="
echo ""
echo "Próximos pasos:"
echo ""
echo "1. Editar configuración:"
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "2. Obtener certificado Let's Encrypt:"
echo "   sudo certbot certonly --standalone -d ticketdesk.tuempresa.com"
echo ""
echo "3. Ver estado de servicios:"
echo "   systemctl status ticketdesk"
echo "   systemctl status ticketdesk-scheduler"
echo ""
echo "4. Ver logs en tiempo real:"
echo "   journalctl -u ticketdesk -f"
echo "   journalctl -u ticketdesk-scheduler -f"
echo ""
echo "5. Acceder a la aplicación:"
echo "   https://localhost"
echo ""
echo "6. Verificar health check:"
echo "   curl https://localhost/api/health"
echo ""

exit 0
