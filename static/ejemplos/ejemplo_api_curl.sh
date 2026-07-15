#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# Ejemplos de la API de DeskEli usando cURL
#
# Uso rápido para probar el endpoint desde terminal / Postman / scripts bash.
# ═══════════════════════════════════════════════════════════════════════════

API_URL="https://deskeli.eliotproyectos.tech/api/v1/external/tickets"
API_TOKEN="dsk_t_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"   # ← tu token

# ─── EJEMPLO A: Ticket con 3 subtareas ─────────────────────────────────────
curl -X POST "$API_URL" \
  -H "X-Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Configurar VPN para 3 nuevos empleados",
    "description": "Configurar acceso VPN corporativo para los empleados del área Comercial que ingresan el lunes.",
    "category": "Redes",
    "priority": "high",
    "applicantEmail": "supervisor@eliotcompany.com",
    "userArea": "Comercial",
    "userPhone": "+57 300 555 1111",
    "externalRef": "REQ-2026-0201",
    "subtasks": [
      {
        "title": "Crear usuarios en Active Directory",
        "description": "Alta de los 3 usuarios con estructura estándar OU=Comercial.",
        "priority": "high",
        "assigneeEmail": "admin.ad@eliotcompany.com"
      },
      {
        "title": "Habilitar acceso VPN Fortinet",
        "description": "Agregar los 3 usuarios al grupo VPN_COMERCIAL.",
        "priority": "high",
        "assigneeEmail": "redes.senior@eliotcompany.com"
      },
      {
        "title": "Enviar guía de conexión al usuario",
        "description": "Enviar por correo el manual paso a paso + credenciales temporales.",
        "priority": "medium",
        "assigneeEmail": "soporte.ti@eliotcompany.com"
      }
    ]
  }'


# ─── EJEMPLO B: Ticket desde guion preconfigurado ──────────────────────────
# curl -X POST "$API_URL" \
#   -H "X-Authorization: Bearer $API_TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "subject": "Baja de usuario: María Torres (renuncia)",
#     "description": "Ejecutar procedimiento estándar de baja de usuario.",
#     "category": "Accesos",
#     "priority": "medium",
#     "applicantEmail": "rrhh@eliotcompany.com",
#     "guion_code": "baja_usuario"
#   }'
