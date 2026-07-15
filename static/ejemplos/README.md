# Ejemplos de integración con la API DeskEli

Cómo consumir la API REST de DeskEli para crear tickets **usando guiones
preconfigurados** — la forma correcta de integrar sistemas externos.

## 🎯 Flujo correcto: GUIONES

En DeskEli las subtareas **NO se envían desde el sistema externo**. Se definen
UNA sola vez en el panel admin (llamadas "Guiones") y el sistema externo solo
envía el `guion_code`.

```
┌─────────────────────────────────┐
│  Sistema externo (Aranda,       │       ┌────────────────────────────┐
│  script Python, portal Web)     │       │  Panel admin DeskEli:      │
│                                 │       │                            │
│  POST /api/v1/external/tickets  │──►────│  Guión 'cambio-clave-sap'  │
│  {                              │       │  ├─ Subtarea 1: Verificar  │
│    subject: "...",              │       │  ├─ Subtarea 2: Cambiar    │
│    description: "...",          │       │  ├─ Subtarea 3: Notificar  │
│    applicantEmail: "...",       │       │  └─ Subtarea 4: Validar    │
│    guion_code: "cambio-clave-sap"│      │  (con técnicos asignados)  │
│  }                              │       └────────────────────────────┘
└─────────────────────────────────┘                     │
                                                        ▼
                                            ┌───────────────────────┐
                                            │  Ticket TKT-ELIOT-00042│
                                            │  ✓ Subtareas creadas  │
                                            │  ✓ Técnicos asignados │
                                            │  ✓ Prioridades OK     │
                                            └───────────────────────┘
```

### Ventajas de este enfoque

- ✅ **Cambios sin código**: si cambia el proceso, el admin edita el guión y no toca la integración
- ✅ **Técnicos asignados centralmente**: el admin sabe quién atiende qué, no el sistema origen
- ✅ **Auditoría clara**: cada ticket queda linkeado al guión que ejecutó
- ✅ **Payload mínimo**: 5 campos vs 30+ campos ad-hoc
- ✅ **Sin errores de tipo**: nada de listas donde el server espera strings

---

## 📋 Cómo crear un guión (Panel admin)

**Se hace una sola vez, cuando definís el proceso.**

1. Login como admin en DeskEli
2. Sidebar → **Automatización → Guiones**
3. Click **＋ Nuevo Guión** y completar:

   | Campo | Ejemplo | Descripción |
   |---|---|---|
   | `code` | `cambio-clave-sap-rise` | Identificador único, sin espacios ni acentos. Es lo que envía el sistema externo. |
   | `name` | `Cambio de clave SAP RISE` | Etiqueta amigable para el admin |
   | `description` | `Procedimiento estándar para renovar claves de acceso SAP RISE` | Documentación interna |
   | `company` | `eliot` / `pash` / `primatela` | Empresa dueña del guión |
   | `default_priority` | `high` | Se aplica a subtareas que no especifiquen prioridad |
   | `default_category` | `SAP` | Se aplica a subtareas sin categoría |
   | `is_active` | ✅ | Solo los activos se pueden invocar |

4. Dentro del guión, click **＋ Nueva Subtarea** y agregar los pasos del proceso:

   | Campo | Ejemplo |
   |---|---|
   | `order_idx` | `0`, `1`, `2`, ... — orden de creación |
   | `title` | `Paso 1: Verificar identidad del solicitante` |
   | `description` | `Confirmar por email/telefono que la solicitud es legítima` |
   | `priority` | `critical` / `high` / `medium` / `low` |
   | `category` | Opcional, sobrescribe `default_category` |
   | `assignee` | Técnico específico, o vacío (usa pool round-robin) |

5. **(Opcional)** Asignar un pool de especialistas al guión:
   - Sidebar → **Equipo → Gestión de Usuarios**
   - Editar un técnico → columna **Guiones** → agregarlo al guión
   - Cuando una subtarea NO tenga técnico fijo, se asigna por round-robin entre los especialistas del pool

---

## 🔑 Generar un token de API

1. Sidebar → **Configuración → API Keys** (o **Tokens**)
2. Click **＋ Nuevo token**:
   - **Nombre:** ej "Integración Aranda", "Script Nolberto"
   - **Empresa:** la empresa cuyos tickets se van a crear
   - **Scopes:** ✅ **`tickets:create`** (imprescindible)
   - **Expiración:** opcional. Recomendado 6-12 meses
3. Copiá el token que empieza con `dsk_t_...` — **solo se muestra una vez**

---

## 📮 Endpoint

```
POST https://deskeli.eliotproyectos.tech/api/v1/external/tickets
```

Header obligatorio:
```
X-Authorization: Bearer <TOKEN>
Content-Type: application/json
```

## 📝 Payload mínimo (con guión)

```json
{
  "subject": "Cambio clave SAP RISE 4",
  "description": "Renovación trimestral de clave para BASIS-SAP",
  "applicantEmail": "basis-sap@patprimo.com.co",
  "guion_code": "cambio-clave-sap-rise"
}
```

Con eso alcanza. **Todo lo demás lo define el guión.**

### Campos opcionales del ticket padre

| Campo | Descripción |
|---|---|
| `priority` | Sobrescribe la prioridad default del guión (para el ticket, no para las subtareas) |
| `category` | Categoría del ticket padre |
| `userArea` | Área del solicitante |
| `userLocation` | Sede/piso |
| `userPhone` | Teléfono de contacto |
| `externalRef` | Tu referencia (útil para trazar cross-system) |
| `attachments` | Array de archivos en base64 |

## 📦 Respuesta esperada (201 Created)

```json
{
  "success": true,
  "id": 42,
  "ticket_number": "TKT-ELIOT-00042",
  "url": "https://deskeli.eliotproyectos.tech/technician/ticket/42",
  "subtasks": [
    {"id": 12, "subtask_number": "TKT-ELIOT-00042-S01", "title": "Paso 1: Verificar identidad"},
    {"id": 13, "subtask_number": "TKT-ELIOT-00042-S02", "title": "Paso 2: Cambiar clave"},
    {"id": 14, "subtask_number": "TKT-ELIOT-00042-S03", "title": "Paso 3: Notificar al usuario"},
    {"id": 15, "subtask_number": "TKT-ELIOT-00042-S04", "title": "Paso 4: Validar acceso"}
  ]
}
```

## ⚠ Errores comunes

| Status | Error | Causa |
|:---:|---|---|
| 400 | `Guión no encontrado o inactivo: cambio-clave-sap-rise (empresa eliot)` | El `guion_code` no existe, o está inactivo, o pertenece a otra empresa |
| 400 | `Solicitante no encontrado. Envía applicantEmail o applicantId válido.` | El email del solicitante no existe en la BD |
| 401 | `Token inválido o revocado` | Token no existe o fue revocado |
| 403 | `Token sin scope tickets:create` | El token no tiene permiso para crear tickets |

## 📂 Archivos de ejemplo

| Archivo | Descripción |
|---|---|
| `ejemplo_api_tickets.py` | 4 casos de uso en Python (guión simple, guión con overrides, guión + adjuntos, batch) |
| `ejemplo_api_curl.sh` | Ejemplo rápido con cURL |

## 💡 Buenas prácticas

1. **Definí un guión por proceso, no por cliente.** Ejemplo: `cambio-clave-sap-rise` sirve para todos los usuarios, no crees `cambio-clave-juan`, `cambio-clave-maria`.

2. **Naming convention consistente:** `verbo-sustantivo-especificacion` — ej `alta-usuario-sap`, `baja-usuario-general`, `cambio-clave-vpn`.

3. **Un token por integrador.** Si tenés Aranda + otro script + otro sistema llamando, generá 3 tokens distintos. Facilita revocar sin cortar todo.

4. **Guardá el token en variables de entorno** (nunca hard-coded).

5. **Usá `externalRef`** con la referencia de tu sistema origen para poder buscar el ticket cuando te lo mencionen.

6. **No inventes guiones al momento**: si el proceso es nuevo, primero coordiná con el admin de DeskEli para que lo cree, después llamalo.

## 🆘 Soporte

Si algo no funciona:

1. Verificá que el guión existe: Panel admin → Automatización → Guiones. Debe aparecer en la lista con `is_active` = ✅
2. Verificá que el `code` es exacto: minúsculas, sin espacios, sin acentos
3. Verificá que la empresa del token coincide con la del guión
4. Con la corrección `dd87308`, los errores ya vienen como JSON legible — buscá el campo `error` en la respuesta
