# Ejemplos de integración con la API DeskEli

Cómo consumir la API REST de DeskEli para crear tickets con múltiples subtareas
y adjuntos desde una integración externa (Aranda, scripts propios, otras plataformas).

## Endpoint

```
POST https://deskeli.eliotproyectos.tech/api/v1/external/tickets
```

## Autenticación

Header obligatorio:

```
X-Authorization: Bearer <TOKEN>
```

o también:

```
Authorization: Bearer <TOKEN>
```

## Cómo generar un token

1. Ingresá al portal admin de DeskEli
2. Andá a **Configuración → API Keys** (o **Tokens**)
3. Cliqueá **Nuevo token** con estos datos:
   - **Nombre:** una descripción amigable (ej: "Integración Aranda", "Script pruebas Nolberto")
   - **Empresa:** la empresa cuyos tickets se van a crear (Eliot / Pash / Primatela)
   - **Scopes:** marcá **`tickets:create`** (imprescindible)
   - **Expiración:** opcional. Recomendado 6-12 meses
4. Copiá el token que empieza con `dsk_t_...` — **solo se muestra una vez**
5. Pegalo en `API_TOKEN` del script

## Archivos de ejemplo

| Archivo | Descripción |
|---|---|
| `ejemplo_api_tickets.py` | 4 ejemplos completos en Python (subtareas ad-hoc, desde guión, con adjuntos, procedimiento largo) |
| `ejemplo_api_curl.sh` | Ejemplo rápido en cURL para probar desde terminal |

## Estructura del payload

### Ticket padre (campos principales)

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:---:|---|
| `subject` | string | ✅ | Título del ticket (máx 200 caracteres) |
| `description` | string | ✅ | Descripción larga (acepta HTML sanitizado) |
| `category` | string | opcional | Categoría (ej: "SAP", "Redes"). Default: `"General"` |
| `priority` | string | opcional | `low` / `medium` / `high` / `critical`. Default: `medium` |
| `applicantEmail` | string | ✅ | Email del solicitante (debe existir en la BD) |
| `applicantId` | int | opcional | Alternativa al email, ID del usuario |
| `authorId` | int | opcional | Quién registra el ticket (para trazabilidad). Fallback: applicant |
| `assigneeEmail` | string | opcional | Técnico al que asignar. Sin esto, se asigna automáticamente |
| `userArea` | string | opcional | Área/departamento del solicitante |
| `userLocation` | string | opcional | Sede/edificio/piso |
| `userPhone` | string | opcional | Contacto del solicitante |
| `externalRef` | string | opcional | Referencia externa (útil para tracing cross-system) |

### Subtareas (2 modos, mutuamente excluyentes)

**Modo A — Desde guión preconfigurado:**

```json
{
  "guion_code": "onboarding_usuario"
}
```

O por id:
```json
{
  "guion_id": 5
}
```

Los guiones se definen en el panel admin. Cada guión genera N subtareas
automáticamente con orden, prioridad y técnico definidos.

**Modo B — Subtareas ad-hoc en el payload:**

```json
{
  "subtasks": [
    {
      "title": "Paso 1: Backup",
      "description": "Ejecutar backup completo",
      "priority": "high",
      "category": "SAP",
      "assigneeEmail": "tecnico1@empresa.com"
    },
    { "title": "Paso 2: Migración", "priority": "high", ... },
    { "title": "Paso 3: Pruebas", "priority": "medium", ... }
  ]
}
```

⚠ **Si mandás `guion_code` Y `subtasks` juntos, gana el guión** y se ignoran
los subtasks del payload.

### Adjuntos (en base64)

```json
{
  "attachments": [
    {
      "filename": "acta.pdf",
      "content_base64": "JVBERi0xLjMK...",
      "mime": "application/pdf",
      "attach_to": "both"
    }
  ]
}
```

- `attach_to`: `"ticket"` (solo padre), `"subtasks"` (se copia a todas las subtareas), `"both"` (default)
- Límite: **20 adjuntos por request, 50 MB por archivo**
- Tipos permitidos: PDF, DOC/DOCX, XLS/XLSX, PPT, TXT, CSV, PNG/JPG/GIF, ZIP/RAR/7Z

## Respuesta esperada (201 Created)

```json
{
  "success": true,
  "id": 42,
  "ticket_number": "TKT-ELIOT-00042",
  "url": "https://deskeli.eliotproyectos.tech/technician/ticket/42",
  "subtasks": [
    {"id": 12, "subtask_number": "TKT-ELIOT-00042-S01", "title": "Control 1: Backup"},
    {"id": 13, "subtask_number": "TKT-ELIOT-00042-S02", "title": "Control 2: Migración"},
    {"id": 14, "subtask_number": "TKT-ELIOT-00042-S03", "title": "Control 3: Pruebas"}
  ],
  "attachments": {
    "ticket": 1,
    "subtasks": 3
  }
}
```

## Errores comunes

| Status | Error | Causa |
|:---:|---|---|
| 400 | `Faltan campos requeridos: subject y description` | Payload sin los campos obligatorios |
| 400 | `Solicitante no encontrado. Envía applicantEmail o applicantId válido.` | El email del solicitante no existe en la BD |
| 400 | `Guión no encontrado o inactivo` | El `guion_code` no matchea o está inactivo para esta empresa |
| 401 | `Falta header X-Authorization: Bearer <token>` | Header ausente o formato inválido |
| 401 | `Token inválido o revocado` | Token no existe o fue revocado |
| 401 | `Token expirado` | Pasó la fecha de expiración |
| 403 | `Token sin scope tickets:create` | El token no tiene permiso para crear tickets |
| 403 | `Solicitante no pertenece a la empresa` | El email es de otra empresa distinta a la del token |

## Buenas prácticas

1. **Un token por integración.** Si tenés varios sistemas llamando a DeskEli, generá un token para cada uno. Facilita revocar sin afectar otros.
2. **Guardá el token en variables de entorno**, nunca hard-coded en el script.
3. **Usá `externalRef`** para tracing bidireccional entre tu sistema y DeskEli.
4. **Preferí guiones preconfigurados** sobre subtareas ad-hoc. Los guiones se definen 1 vez y todos los tickets siguen la misma estructura — mejor para auditoría.
5. **Comprimí los adjuntos grandes** antes de convertir a base64. Base64 aumenta el tamaño ~33%, así que un PDF de 40 MB queda cerca del límite.
6. **Manejá los códigos de error** en tu script para reintentar o alertar según corresponda.

## Soporte

Si algo no funciona, verificá:
1. El token está activo y no expirado (Panel admin → API Keys)
2. El solicitante existe en la BD con el email exacto
3. El JSON está bien formado (validá con jq: `echo '$payload' | jq .`)
4. Los adjuntos están correctamente codificados en base64 (sin saltos de línea)

Para soporte técnico, contactá al equipo de TI de Manufacturas Eliot.
