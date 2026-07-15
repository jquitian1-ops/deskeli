#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# Ejemplo cURL: crear ticket disparando un GUION preconfigurado
#
# Prerequisitos (una sola vez):
# 1. Panel admin → Automatización → Guiones → crear el guión con las
#    subtareas del proceso. Anotá el `code` que le pusiste.
# 2. Panel admin → Configuración → API Keys → nuevo token con scope
#    tickets:create. Copiá el token 'dsk_t_...'.
# ═══════════════════════════════════════════════════════════════════════════

API_URL="https://deskeli.eliotproyectos.tech/api/v1/external/tickets"
API_TOKEN="dsk_t_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"   # ← tu token

# ─── Payload mínimo con guión ─────────────────────────────────────────────
curl -X POST "$API_URL" \
  -H "X-Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Cambio clave SAP RISE 4",
    "description": "Renovación trimestral de clave para BASIS-SAP",
    "applicantEmail": "basis-sap@patprimo.com.co",
    "userArea": "Basis SAP",
    "userPhone": "+57 300 555 1234",
    "externalRef": "REQ-2026-0142",
    "guion_code": "cambio-clave-sap-rise"
  }'


# ─── Con prioridad crítica (override del default del guión) ───────────────
# curl -X POST "$API_URL" \
#   -H "X-Authorization: Bearer $API_TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "subject": "URGENTE: cambio clave SAP RISE - produccion caida",
#     "description": "Se necesita cambio urgente. Usuarios bloqueados.",
#     "priority": "critical",
#     "applicantEmail": "basis-sap@patprimo.com.co",
#     "externalRef": "INC-2026-0399",
#     "guion_code": "cambio-clave-sap-rise"
#   }'
