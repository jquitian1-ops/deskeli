#!/bin/bash
# ============================================================================
# Backup Script - TicketDesk Enterprise v2.1
# Ejecutar vía cron: 0 2 * * * /opt/ticketdesk/backup.sh
# O vía Supervisor
# ============================================================================

set -euo pipefail

# Configuración
BACKUP_DIR="${BACKUP_DIR:-.}/backups"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
DB_FILE="ticketdesk_v2.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/ticketdesk_backup_$TIMESTAMP.db.gz"
LOG_FILE="${LOG_DIR:-./logs}/backup.log"

# Crear directorio de logs si no existe
mkdir -p "$(dirname "$LOG_FILE")"

# Log function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "========================================"
log "Iniciando Backup de TicketDesk"
log "========================================"

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"
log "Directorio de backups: $BACKUP_DIR"

# Verificar que la BD existe
if [ ! -f "$DB_FILE" ]; then
    log "ERROR: Base de datos no encontrada: $DB_FILE"
    exit 1
fi

# Crear backup comprimido
log "Comprimiendo base de datos..."
if gzip -c "$DB_FILE" > "$BACKUP_FILE"; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "✓ Backup creado exitosamente: $BACKUP_FILE ($BACKUP_SIZE)"
else
    log "ERROR: Fallo al crear backup"
    exit 1
fi

# ============================================================================
# Subir a AWS S3 (Opcional)
# ============================================================================
if command -v aws &> /dev/null && [ -n "${AWS_ACCESS_KEY_ID:-}" ]; then
    log "Subiendo backup a AWS S3..."
    if aws s3 cp "$BACKUP_FILE" \
        "s3://${S3_BUCKET:-ticketdesk-backups}/$(basename "$BACKUP_FILE")" \
        --sse AES256 \
        --storage-class STANDARD_IA; then
        log "✓ Backup subido a S3"
    else
        log "⚠ Error al subir a S3 (continuando localmente)"
    fi
fi

# ============================================================================
# Subir a Google Drive (Opcional)
# ============================================================================
if command -v rclone &> /dev/null && [ -n "${GOOGLE_DRIVE_FOLDER_ID:-}" ]; then
    log "Subiendo backup a Google Drive..."
    if rclone copy "$BACKUP_FILE" \
        "gdrive:${GOOGLE_DRIVE_FOLDER_ID}/" \
        --config=/home/ticketdesk/.config/rclone/rclone.conf; then
        log "✓ Backup subido a Google Drive"
    else
        log "⚠ Error al subir a Google Drive (continuando localmente)"
    fi
fi

# ============================================================================
# Limpiar backups antiguos (retención)
# ============================================================================
log "Limpiando backups más antiguos que $RETENTION_DAYS días..."
find "$BACKUP_DIR" -name "ticketdesk_backup_*.db.gz" -type f -mtime "+$RETENTION_DAYS" | while read -r old_backup; do
    OLD_SIZE=$(du -h "$old_backup" | cut -f1)
    if rm -f "$old_backup"; then
        log "✓ Eliminado: $(basename "$old_backup") ($OLD_SIZE)"
    else
        log "⚠ Error al eliminar: $(basename "$old_backup")"
    fi
done

# Contar backups restantes
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "ticketdesk_backup_*.db.gz" -type f | wc -l)
log "Backups locales retenidos: $BACKUP_COUNT"

# ============================================================================
# Reportar estado
# ============================================================================
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "Tamaño total de backups: $TOTAL_SIZE"
log "✓ Backup completado exitosamente"
log "========================================"

# Enviar notificación (Opcional)
if [ -n "${TEAMS_WEBHOOK_GENERAL:-}" ]; then
    curl -X POST \
        -H 'Content-Type: application/json' \
        -d "{
            \"@type\": \"MessageCard\",
            \"@context\": \"https://schema.org/extensions\",
            \"themeColor\": \"0078D4\",
            \"summary\": \"Backup de TicketDesk completado\",
            \"sections\": [{
                \"activityTitle\": \"✓ Backup de TicketDesk Completado\",
                \"facts\": [
                    {\"name\": \"Fecha\", \"value\": \"$(date +'%Y-%m-%d %H:%M:%S')\"},
                    {\"name\": \"Archivo\", \"value\": \"$(basename "$BACKUP_FILE")\"},
                    {\"name\": \"Tamaño\", \"value\": \"$BACKUP_SIZE\"},
                    {\"name\": \"Total retenido\", \"value\": \"$TOTAL_SIZE\"}
                ]
            }]
        }" \
        "${TEAMS_WEBHOOK_GENERAL}" || true
fi

exit 0
