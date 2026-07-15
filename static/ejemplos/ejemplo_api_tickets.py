"""
ejemplo_api_tickets.py
======================

Ejemplo de integración con la API de DeskEli usando GUIONES preconfigurados.

Un GUION es una plantilla de subtareas que el admin de DeskEli define UNA VEZ
en el panel. La integración externa solo necesita conocer el `guion_code` y no
tiene que saber nada sobre técnicos, prioridades ni estructura de subtareas.

Ventajas del enfoque con guiones vs enviar subtareas explícitas:
- ✅ Cambios en el proceso no requieren tocar el código del integrador
- ✅ Los técnicos asignados los define el admin, no el sistema origen
- ✅ Auditoría más limpia: sabés qué versión del proceso ejecutó qué ticket
- ✅ Menos payload (2 líneas vs 30) → menos errores de tipos

Endpoint : POST https://deskeli.eliotproyectos.tech/api/v1/external/tickets
Auth     : Header 'X-Authorization: Bearer <TOKEN>'
Scope    : tickets:create

Requisitos:
    pip install requests

Uso:
    py ejemplo_api_tickets.py
"""

import requests
import json


# ═══════════════════════════════════════════════════════════════════════════
# PASO 0 — Antes de correr este script (una sola vez):
# ═══════════════════════════════════════════════════════════════════════════
# 1. Crear el GUIÓN en el panel admin de DeskEli:
#    a. Login como admin → sidebar → Automatización → Guiones
#    b. Botón "＋ Nuevo Guión" y completar:
#       - code:  "cambio-clave-sap-rise"      (identificador único, sin espacios)
#       - name:  "Cambio de clave SAP RISE"   (etiqueta amigable)
#       - description: "Procedimiento completo para cambio de clave..."
#       - company: eliot / pash / primatela
#       - default_priority: high
#       - default_category: SAP
#       - is_active: ✅
#    c. Dentro del guión, agregar las SUBTAREAS (una por paso del proceso).
#       Cada subtarea puede tener:
#       - title:       ej "Paso 1: Verificar identidad del solicitante"
#       - description: instrucciones detalladas del paso
#       - priority:    critical/high/medium/low
#       - category:    (opcional, hereda del guión)
#       - assignee:    técnico específico o vacío (usa pool round-robin)
#       - order_idx:   orden de ejecución (0, 1, 2, ...)
#    d. Opcional: en Gestión de Usuarios → columna "Guiones", asignar
#       especialistas al guión (pool de asignación round-robin).
#
# 2. Generar el API TOKEN:
#    Sidebar → Configuración → API Keys → Nuevo token con scope tickets:create
#    Copiar el token que empieza con 'dsk_t_...' y pegarlo abajo.
# ═══════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════

API_URL = 'https://deskeli.eliotproyectos.tech/api/v1/external/tickets'
API_TOKEN = 'dsk_t_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'  # ← tu token

HEADERS = {
    'X-Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}


# ═══════════════════════════════════════════════════════════════════════════
# EJEMPLO 1 (RECOMENDADO): Crear ticket desde un GUIÓN preconfigurado
# ═══════════════════════════════════════════════════════════════════════════
def ejemplo_desde_guion():
    """El ticket se crea con un simple payload. Las subtareas, técnicos
    asignados, prioridades y orden salen del guión definido en el panel."""

    payload = {
        # ─── Datos del ticket padre ──────────────────────────────────────
        "subject": "RV: cambio clave sap rise 4",
        "description": (
            "Solicito el cambio de clave para el ambiente SAP RISE 4. "
            "Usuario: BASIS-SAP. Motivo: renovación periódica trimestral."
        ),

        # ─── Solicitante ─────────────────────────────────────────────────
        "applicantEmail": "basis-sap@patprimo.com.co",
        "userArea": "Basis SAP",
        "userPhone": "+57 300 555 1234",

        # ─── Referencia externa (para tracing bidireccional) ─────────────
        "externalRef": "REQ-2026-0142",

        # ─── EL GUIÓN ───────────────────────────────────────────────────
        # Este es el único campo especial: dispara la creación automática
        # de las subtareas definidas en el guión.
        "guion_code": "cambio-clave-sap-rise"

        # Alternativa por id numérico:
        #   "guion_id": 7
    }

    print("\n═══ Ticket desde guión 'cambio-clave-sap-rise' ═══")
    r = requests.post(API_URL, headers=HEADERS, data=json.dumps(payload))
    _print_response(r)


# ═══════════════════════════════════════════════════════════════════════════
# EJEMPLO 2: Guión + campos opcionales para override de prioridad/asignación
# ═══════════════════════════════════════════════════════════════════════════
def ejemplo_con_overrides():
    """Se dispara el guión pero se sobrescriben algunos valores.

    IMPORTANTE: los campos priority/category del ticket padre se aplican al
    ticket. La prioridad de cada SUBTAREA sale del guión (no del payload).
    Si en un caso necesitás elevar la prioridad de todas las subtareas,
    definí eso en el guión, no acá.
    """

    payload = {
        "subject": "URGENTE: cambio clave SAP - producción caída",
        "description": (
            "Se necesita cambio de clave con urgencia. El acceso actual "
            "no permite login y hay usuarios de negocio bloqueados en el ERP."
        ),
        "priority": "critical",           # override del default del guión
        "category": "SAP",

        "applicantEmail": "basis-sap@patprimo.com.co",
        "userArea": "Basis SAP",
        "externalRef": "INC-2026-0399",

        # Guión que dispara las subtareas
        "guion_code": "cambio-clave-sap-rise"
    }

    print("\n═══ Ticket con guión + overrides ═══")
    r = requests.post(API_URL, headers=HEADERS, data=json.dumps(payload))
    _print_response(r)


# ═══════════════════════════════════════════════════════════════════════════
# EJEMPLO 3: Guión + adjuntos (base64)
# ═══════════════════════════════════════════════════════════════════════════
def ejemplo_guion_con_adjuntos():
    """Ticket con guión + archivos adjuntos codificados en base64.

    Los adjuntos van al ticket padre (o a todas las subtareas, según attach_to).
    El guión sigue disparando sus subtareas normalmente.
    """
    import base64
    # Para el ejemplo, generamos un PDF ficticio
    # En producción: pdf_bytes = open('acta.pdf', 'rb').read()
    pdf_bytes = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n(Acta de aprobacion ficticia)'
    pdf_b64 = base64.b64encode(pdf_bytes).decode('ascii')

    payload = {
        "subject": "Solicitud de cambio de clave SAP autorizada por gerencia",
        "description": "Cambio autorizado según acta adjunta.",
        "applicantEmail": "basis-sap@patprimo.com.co",
        "userArea": "Basis SAP",
        "externalRef": "REQ-2026-0143",

        "guion_code": "cambio-clave-sap-rise",

        "attachments": [
            {
                "filename": "acta_autorizacion_gerencia.pdf",
                "content_base64": pdf_b64,
                "mime": "application/pdf",
                "attach_to": "ticket"  # solo al ticket padre
            }
        ]
    }

    print("\n═══ Ticket con guión + adjunto ═══")
    r = requests.post(API_URL, headers=HEADERS, data=json.dumps(payload))
    _print_response(r)


# ═══════════════════════════════════════════════════════════════════════════
# EJEMPLO 4: Loop para crear varios tickets seguidos (batch)
# ═══════════════════════════════════════════════════════════════════════════
def ejemplo_batch():
    """Crea N tickets en secuencia, cada uno disparando el mismo guión.

    Útil para procesos que se ejecutan por lotes (ej: cambios de clave
    trimestrales para 20 usuarios).
    """
    usuarios_pendientes = [
        {"email": "usuario1@patprimo.com.co", "nombre": "Ana Pérez", "sap_id": "USR001"},
        {"email": "usuario2@patprimo.com.co", "nombre": "Juan López", "sap_id": "USR002"},
        {"email": "usuario3@patprimo.com.co", "nombre": "María Torres", "sap_id": "USR003"},
    ]

    creados = []
    for u in usuarios_pendientes:
        payload = {
            "subject": f"Cambio clave SAP RISE — {u['nombre']}",
            "description": (
                f"Cambio de clave trimestral programado para el usuario "
                f"{u['nombre']} (ID SAP: {u['sap_id']})."
            ),
            "applicantEmail": u['email'],
            "externalRef": f"REQ-Q1-2026-{u['sap_id']}",
            "guion_code": "cambio-clave-sap-rise"
        }
        r = requests.post(API_URL, headers=HEADERS, data=json.dumps(payload))
        if r.status_code == 201 and r.json().get('success'):
            creados.append(r.json().get('ticket_number'))
            print(f"  ✅ {u['nombre']}: {r.json().get('ticket_number')}")
        else:
            print(f"  ✗ {u['nombre']}: {r.status_code} - {r.text[:200]}")

    print(f"\n═══ Total tickets creados: {len(creados)}/{len(usuarios_pendientes)} ═══")


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
                print(f"\n   📋 Subtareas del guión ({len(subtasks)}):")
                for st in subtasks:
                    print(f"     • {st.get('subtask_number')} — {st.get('title')}")
            atts = data.get('attachments') or {}
            if atts.get('ticket', 0) > 0 or atts.get('subtasks', 0) > 0:
                print(f"\n   📎 Adjuntos: {atts.get('ticket', 0)} en ticket, {atts.get('subtasks', 0)} en subtareas")
        else:
            print(f"\n✗ Error: {data.get('error')}")
            if data.get('hint'):
                print(f"   💡 {data.get('hint')}")
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

    # ═══ Descomentá el ejemplo que querés probar ═══

    ejemplo_desde_guion()             # ← el flujo principal recomendado
    # ejemplo_con_overrides()         # con prioridad crítica
    # ejemplo_guion_con_adjuntos()    # con archivos adjuntos
    # ejemplo_batch()                 # varios tickets en loop
