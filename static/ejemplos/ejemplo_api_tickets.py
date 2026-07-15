"""
ejemplo_api_tickets.py
======================

Ejemplos completos de cómo consumir la API de DeskEli para crear tickets con
múltiples subtareas y adjuntos desde una integración externa.

Endpoint : POST https://deskeli.eliotproyectos.tech/api/v1/external/tickets
Auth     : Header 'X-Authorization: Bearer <TOKEN>'
Scope    : tickets:create

Requisitos:
    pip install requests

Uso:
    py ejemplo_api_tickets.py

Antes de correr:
    1. Panel admin → Configuración → API Keys → Nuevo token con scope tickets:create
    2. Copiá el token que empieza con 'dsk_t_...' y pegalo en API_TOKEN
    3. Ajustá URL, empresa, correos de solicitante y técnicos según tu instalación
"""

import requests
import json
import base64
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════

API_URL = 'https://deskeli.eliotproyectos.tech/api/v1/external/tickets'
API_TOKEN = 'dsk_t_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'  # ← reemplazá con tu token

HEADERS = {
    'X-Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}


# ═══════════════════════════════════════════════════════════════════════════
# EJEMPLO 1: Ticket con 3 subtareas ad-hoc (sin guión preconfigurado)
# ═══════════════════════════════════════════════════════════════════════════
def ejemplo_1_subtareas_adhoc():
    """Un ticket con 3 subtareas creadas explícitamente en el payload.

    Cada subtarea puede tener su propia prioridad, categoría y técnico asignado.
    Si no se especifican, heredan del ticket padre.
    """
    payload = {
        # ─── Datos del ticket padre ─────────────────────────────────────
        "subject": "Migración de módulo SAP-MM a nuevo servidor",
        "description": (
            "Solicitud para migrar el módulo SAP-MM del ambiente PRD al nuevo "
            "servidor SAP-RISE. La migración debe hacerse en horario nocturno "
            "para minimizar impacto operativo.\n\n"
            "Detalles técnicos en el documento adjunto (si aplica)."
        ),
        "category": "SAP",
        "priority": "high",

        # ─── Solicitante y autor ─────────────────────────────────────────
        "applicantEmail": "usuario.solicitante@eliotcompany.com",
        "authorId": 1,  # opcional: id del que registra el ticket. Fallback: applicant

        # ─── Contacto del solicitante ────────────────────────────────────
        "userArea": "Producción",
        "userLocation": "Planta CALLE 19 · Piso 2",
        "userPhone": "+57 300 555 1234",

        # ─── Referencia externa (para trazabilidad cross-system) ─────────
        "externalRef": "REQ-2026-0142",

        # ─── SUBTAREAS: se crean 3 subtareas del ticket padre ────────────
        "subtasks": [
            {
                "title": "Control 1: Backup pre-migración",
                "description": (
                    "Ejecutar backup completo de SAP-MM antes de iniciar. "
                    "Verificar tamaño del backup y validar restauración de prueba."
                ),
                "priority": "critical",
                "category": "SAP",
                "assigneeEmail": "tecnico.backup@eliotcompany.com"
            },
            {
                "title": "Control 2: Migración de datos",
                "description": (
                    "Copiar datos del ambiente PRD al servidor RISE. "
                    "Validar consistencia con checksum MD5."
                ),
                "priority": "high",
                "category": "SAP",
                "assigneeEmail": "tecnico.sap@eliotcompany.com"
            },
            {
                "title": "Control 3: Pruebas post-migración",
                "description": (
                    "Ejecutar las 5 transacciones críticas (MM01, MM02, ME21N, "
                    "MIRO, MB1B) y validar que retornen los mismos resultados "
                    "que en el ambiente PRD anterior."
                ),
                "priority": "high",
                "category": "SAP",
                "assigneeEmail": "tecnico.qa@eliotcompany.com"
            }
        ]
    }

    print("\n═══ EJEMPLO 1: 3 subtareas ad-hoc ═══")
    r = requests.post(API_URL, headers=HEADERS, data=json.dumps(payload))
    _print_response(r)


# ═══════════════════════════════════════════════════════════════════════════
# EJEMPLO 2: Ticket que dispara un GUION preconfigurado
# ═══════════════════════════════════════════════════════════════════════════
def ejemplo_2_desde_guion():
    """Ticket que usa un guión (script de subtareas) ya definido en DeskEli.

    Los guiones se crean en Panel admin → Automatización → Guiones. Cada
    guión tiene:
    - Un code único (ej: 'sap_upgrade', 'onboarding_usuario')
    - Una lista de subtareas con orden, prioridad, técnico fijo o pool
    - Puede tener un pool de técnicos (asignación round-robin por carga)

    Cuando se envía 'guion_code' en el payload, se ignoran los 'subtasks' y
    se generan automáticamente las subtareas definidas en el guión.
    """
    payload = {
        "subject": "Onboarding TI: nuevo empleado José García",
        "description": (
            "Solicitud de habilitación de accesos para el nuevo empleado "
            "José García que ingresa el 2026-08-01. Todos los accesos del "
            "guión de onboarding estándar."
        ),
        "category": "Accesos",
        "priority": "medium",

        "applicantEmail": "rrhh@eliotcompany.com",
        "userArea": "RRHH",
        "userPhone": "+57 601 555 2000",

        # ─── GUION: dispara la creación automática de subtareas ──────────
        "guion_code": "onboarding_usuario",   # code del guion definido en admin
        # Alternativa: "guion_id": 5

        # NOTA: si mandás guion_code Y subtasks, guion_code tiene prioridad
        # y los subtasks del payload se ignoran.
    }

    print("\n═══ EJEMPLO 2: Desde guion preconfigurado ═══")
    r = requests.post(API_URL, headers=HEADERS, data=json.dumps(payload))
    _print_response(r)


# ═══════════════════════════════════════════════════════════════════════════
# EJEMPLO 3: Ticket con múltiples subtareas + adjuntos (base64)
# ═══════════════════════════════════════════════════════════════════════════
def ejemplo_3_con_adjuntos():
    """Ticket con subtareas + archivos adjuntos codificados en base64.

    Los adjuntos pueden ir al ticket padre, a las subtareas, o a ambos
    (según el campo 'attach_to').
    """

    # Leer un archivo de prueba y codificar en base64
    # (para el ejemplo, generamos un PDF ficticio de prueba)
    fake_pdf = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n(Este es un PDF de prueba para DeskEli)'
    pdf_b64 = base64.b64encode(fake_pdf).decode('ascii')

    # Si tenés un archivo real:
    #   pdf_bytes = Path('acta_aprobacion.pdf').read_bytes()
    #   pdf_b64 = base64.b64encode(pdf_bytes).decode('ascii')

    payload = {
        "subject": "Compra de equipos: 15 laptops Dell Latitude",
        "description": (
            "Solicitud de compra aprobada por Dirección para renovar el parque "
            "de laptops del área Comercial. Ver acta adjunta."
        ),
        "category": "Compras",
        "priority": "medium",

        "applicantEmail": "comercial.lider@eliotcompany.com",
        "userArea": "Comercial",
        "userPhone": "+57 300 555 5678",
        "externalRef": "PO-2026-0089",

        # Múltiples subtareas
        "subtasks": [
            {
                "title": "Solicitar cotización a 3 proveedores",
                "description": "Contactar Dell, HP y Lenovo. Comparar precios y garantía.",
                "priority": "high",
                "assigneeEmail": "compras@eliotcompany.com"
            },
            {
                "title": "Preparar orden de compra en SAP",
                "description": "Crear PO en SAP-MM con el proveedor seleccionado.",
                "priority": "medium",
                "assigneeEmail": "compras@eliotcompany.com"
            },
            {
                "title": "Coordinar instalación y entrega",
                "description": "Al recibir equipos, coordinar con TI para setup inicial.",
                "priority": "medium",
                "assigneeEmail": "soporte.ti@eliotcompany.com"
            }
        ],

        # Adjuntos
        "attachments": [
            {
                "filename": "acta_aprobacion_direccion.pdf",
                "content_base64": pdf_b64,
                "mime": "application/pdf",
                "attach_to": "ticket"   # solo al ticket padre
            },
            # Podrías agregar más archivos:
            # {
            #     "filename": "cotizacion_dell.pdf",
            #     "content_base64": base64.b64encode(open('cotizacion.pdf','rb').read()).decode(),
            #     "mime": "application/pdf",
            #     "attach_to": "subtasks"  # se copia a todas las subtareas
            # },
        ]
    }

    print("\n═══ EJEMPLO 3: Subtareas + adjuntos ═══")
    r = requests.post(API_URL, headers=HEADERS, data=json.dumps(payload))
    _print_response(r)


# ═══════════════════════════════════════════════════════════════════════════
# EJEMPLO 4: Ticket con muchas subtareas (procedimiento largo)
# ═══════════════════════════════════════════════════════════════════════════
def ejemplo_4_procedimiento_largo():
    """Ticket con procedimiento de varias subtareas para dejar traza detallada.

    Útil para procesos regulados (Sarbanes-Oxley, ISO 27001, procesos de
    cambio con múltiples checkpoints).
    """

    # Generar dinámicamente 8 subtareas de un procedimiento de cambio
    controles_procedimiento = [
        ("Revisar RFC (Request For Change)", "Confirmar aprobaciones y ventana de mantenimiento."),
        ("Notificar a usuarios afectados", "Enviar comunicado 48h antes del inicio."),
        ("Snapshot de la BD productiva", "Crear punto de restauración en Postgres."),
        ("Ejecutar migración schema", "Aplicar migrations/2026-07/upgrade_v3.sql"),
        ("Validar tablas críticas", "Chequear que users, tickets y config no perdieron filas."),
        ("Test smoke: login + creación ticket", "Loguearse como admin y crear un ticket de prueba."),
        ("Deployment del nuevo backend", "docker-compose up con la nueva imagen."),
        ("Monitorear 2 horas post-deploy", "Revisar logs de error y métricas de latencia.")
    ]

    subtareas = []
    for i, (titulo, desc) in enumerate(controles_procedimiento, start=1):
        subtareas.append({
            "title": f"Paso {i:02d}: {titulo}",
            "description": desc,
            "priority": "high" if i in (1, 3, 4) else "medium",  # críticos del proceso
            "category": "Cambio",
            "assigneeEmail": "devops.senior@eliotcompany.com"
        })

    payload = {
        "subject": "Cambio programado: upgrade DeskEli v3.0",
        "description": (
            "Cambio planificado para el sábado 2026-08-15 a las 22:00.\n\n"
            "Todos los pasos deben completarse en orden y quedar documentados."
        ),
        "category": "Cambio",
        "priority": "high",
        "applicantEmail": "cambios@eliotcompany.com",
        "userArea": "Infraestructura",
        "externalRef": "CHG-2026-0031",
        "subtasks": subtareas   # 8 subtareas generadas dinámicamente
    }

    print("\n═══ EJEMPLO 4: 8 subtareas de procedimiento ═══")
    r = requests.post(API_URL, headers=HEADERS, data=json.dumps(payload))
    _print_response(r)


# ═══════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════════════════════════════
def _print_response(r):
    print(f"HTTP Status: {r.status_code}")
    try:
        data = r.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        if data.get('success'):
            print(f"\n✅ Ticket creado: {data.get('ticket_number')}")
            print(f"   URL: {data.get('url')}")
            subtasks = data.get('subtasks') or []
            if subtasks:
                print(f"   Subtareas ({len(subtasks)}):")
                for st in subtasks:
                    print(f"     - {st.get('subtask_number')}: {st.get('title')}")
            atts = data.get('attachments') or {}
            if atts:
                print(f"   Adjuntos: {atts.get('ticket', 0)} en ticket, {atts.get('subtasks', 0)} en subtareas")
    except ValueError:
        print("(respuesta no es JSON)")
        print(r.text[:500])


# ═══════════════════════════════════════════════════════════════════════════
# EJECUCIÓN
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    if API_TOKEN.startswith('dsk_t_XXXXX'):
        print("⚠  Editá API_TOKEN en el archivo antes de ejecutar")
        exit(1)

    # Descomentá el ejemplo que querés probar:
    ejemplo_1_subtareas_adhoc()
    # ejemplo_2_desde_guion()
    # ejemplo_3_con_adjuntos()
    # ejemplo_4_procedimiento_largo()
