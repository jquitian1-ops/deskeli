# DOCUMENTO TÉCNICO — RESPUESTA A ANÁLISIS PRELIMINAR

**Migración de la integración de Tendency desde Aranda hacia DeskEli**

| Campo | Valor |
|---|---|
| **En respuesta a** | Análisis preliminar y solicitud de definiciones — Tendency, versión 1.0 (4 de agosto de 2026) |
| **Tarea asociada** | 11377 |
| **Requerimiento** | TV-CTI-IS-SN-F-01 v2 — Solicitud de Requerimientos Técnicos |
| **Proyecto** | Proyecto DeskEli — Integración Tendency |
| **Elaborado por** | Administración de DeskEli — Equipo de Integraciones |
| **Dirigido a** | TendencyApps S.A.S · Equipo de desarrollo e integración |
| **Versión del documento** | 1.0 |
| **Fecha** | 5 de agosto de 2026 |
| **Estado** | Emitido — respuesta formal |
| **Clasificación** | Uso interno / uso conjunto con proveedor |

---

## 1. Contexto y resumen ejecutivo

Agradecemos al equipo de Tendency el análisis preliminar entregado el 4 de agosto de 2026. El nivel de detalle del levantamiento y la revisión del código vigente son valorados y facilitan esta respuesta.

**Aclaración importante:** buena parte de las preguntas del capítulo 6 y de los puntos del capítulo 5 se resuelven al confirmar que la versión de la **Guía de Integración para Proveedores** que recibió Tendency **está incompleta**. La versión vigente del contrato de la API — que corresponde al código productivo del endpoint `/api/v1/external/tickets` — sí acepta los campos que el requerimiento TV-CTI-IS-SN-F-01 exige mapear (`applicantEmail`, `userArea`, `userLocation`, `userPhone`, `listAdditionalField`, `assigneeEmail`, `externalRef`, entre otros).

En consecuencia:

- **La contradicción del punto 5.4 se resuelve a favor del requerimiento.** La Guía v1.0 del 27 de julio de 2026 documenta el subconjunto mínimo. Se emitirá la Guía v2.0 con el contrato ampliado como parte de los insumos comprometidos (ver capítulo 4).
- **La preocupación del punto 5.5 sobre la pérdida de identidad del solicitante se cancela.** DeskEli sí soporta enviar el correo del usuario real. Ese usuario queda registrado como creador del ticket. La cuenta genérica solo aplica como *fallback* cuando el solicitante no existe en la BD.
- **El modelo de subtareas (5.1) es explícito, no híbrido.** DeskEli **no** crea subtareas automáticas por categoría. Solo se crean las que provengan del `guion_code` referenciado o del arreglo `subtasks` del payload. Esto simplifica el diseño respecto a lo asumido en el análisis.
- **La tabla de equivalencia (5.2) es responsabilidad conjunta** entre Seguridad de la Información (dueño funcional de los controles) y la Administración de DeskEli. Se propone un flujo concreto para construirla en el capítulo 4.
- **El punto 5.11 (ambiente productivo) se acepta como riesgo prioritario.** Se habilitará un ambiente de calidad separado antes del inicio del desarrollo. Detalle en el capítulo 4.

Con base en las respuestas de este documento, Tendency puede proceder a elaborar la propuesta de solución y la estimación de esfuerzo, sin bloqueos.

---

## 2. Respuestas a las 30 preguntas del capítulo 6

### Subtareas (P-01 a P-03)

**P-01 — ¿DeskEli genera subtareas propias a partir de una plantilla asociada a la categoría, o crea únicamente las que se le envían en el arreglo de subtareas?**

**DeskEli crea únicamente las subtareas que se le envían de forma explícita.** Existen dos mecanismos, y son mutuamente excluyentes:

1. **Modo guion (recomendado):** el payload incluye `guion_code` (o `guion_id`). DeskEli busca el guion configurado para la empresa asociada al token, y crea automáticamente las subtareas definidas en ese guion — con sus prioridades, categorías, técnicos asignados y textos preestablecidos.
2. **Modo explícito (ad-hoc):** el payload incluye un arreglo `subtasks` (o su alias `controls`) con la definición de cada subtarea (título, descripción, prioridad, categoría, `assigneeEmail`).

Si el payload trae ambos, gana el modo guion y se ignora el arreglo. **La categoría del ticket no dispara subtareas por sí sola.**

**P-02 — Si genera subtareas propias, ¿se duplican con las enviadas explícitamente?**

No aplica. Ver P-01. No hay duplicación posible.

**P-03 — ¿Existe algún parámetro equivalente al modelo de la mesa actual que dispare el flujo de atención?**

Sí, y es precisamente el `guion_code`. Cada guion tiene:

- Su propio conjunto de subtareas prediseñadas.
- Su propio pool de técnicos responsables (configurable desde el panel admin de DeskEli en Configuración → Guiones).
- Su propia prioridad y categoría por defecto.

El `guion_code` es la contraparte funcional de lo que en Aranda era "proyecto + categoría + servicio + modelo". La responsabilidad de determinar qué tareas existen no queda del lado de Tendency — Tendency solo indica **qué guion aplica**, y DeskEli genera todo lo demás. Esto es más cercano al comportamiento de Aranda de lo que el análisis asumió.

---

### Catálogo de guiones (P-04 a P-06)

**P-04 — ¿Cuál es la lista completa y vigente de códigos de guion disponibles?**

Se entregará como insumo formal (ver capítulo 3, I-03). Actualmente existen guiones para cada empresa (Eliot, Pash, Primatela). La lista completa se anexará como archivo JSON exportado del panel admin y como CSV humano-legible. El catálogo puede tener hasta ~50 códigos activos por empresa; los códigos son `[a-z][a-z0-9_-]{1,49}` (regex validado en el backend).

**P-05 — ¿Existe un servicio para consultar el catálogo, o se mantendrá como documento estático? ¿Cómo se notificarán los cambios?**

Actualmente el catálogo se administra desde el panel admin y **no hay un endpoint público** para consultarlo. **Se compromete la creación del endpoint `GET /api/v1/external/guiones`** antes de que Tendency inicie el desarrollo, con esta respuesta:

```json
{
  "success": true,
  "company": "pash",
  "guiones": [
    {
      "code": "onboarding-user",
      "name": "Alta de usuario",
      "description": "...",
      "default_priority": "medium",
      "default_category": "General",
      "subtask_count": 8,
      "is_active": true,
      "updated_at": "2026-08-01T10:22:00"
    },
    ...
  ]
}
```

Los cambios se notificarán proactivamente a Tendency por correo cuando se agreguen, deshabiliten o modifiquen guiones. Además el campo `updated_at` permite detección de cambios por polling si Tendency lo prefiere.

**P-06 — ¿Qué ocurre si se envía un código de guion inexistente: se rechaza la petición completa o se reporta y se continúa?**

**Se rechaza la petición completa con HTTP 400** y el ticket no se crea. Este comportamiento ya está implementado en el código productivo (`app.py`, función `api_v1_external_create_ticket`). El objetivo es evitar tickets huérfanos sin subtareas asociadas.

Respuesta de ejemplo:

```json
{
  "success": false,
  "error": "Guión no encontrado o inactivo: acceso-sap (empresa pash)"
}
```

---

### Enrutamiento (P-07 a P-09)

**P-07 — ¿Cuáles son los valores válidos de categoría, prioridad y grupo de asignación en DeskEli?**

- **Prioridad**: `low`, `medium`, `high`, `critical` (obligatoriamente uno de esos cuatro strings en minúscula). Cualquier otro valor cae a `medium`.
- **Categoría**: campo string libre hasta 100 caracteres. No hay enumeración cerrada; el frontend clasifica visualmente con base en categorías comunes (SAP, Servidores, Redes, Correo, etc.). Se entregará una lista de categorías recomendadas por empresa como insumo (I-03).
- **Grupo de asignación**: DeskEli **no maneja grupos de asignación** como campo del payload. La asignación se resuelve así, por orden de precedencia:
  1. `assigneeEmail` o `assigneeId` explícito en el payload → gana.
  2. Si viene `guion_code`, cada subtarea del guion tiene su propio técnico fijo (definido en admin); si no tiene, se selecciona por round-robin del pool del guion.
  3. Si ninguno aplica → el ticket queda sin asignar y entra a la cola general de la empresa.

**P-08 — ¿Cómo se reproduce la separación entre la mesa de ayuda de Pash y la de Tecnología?**

**Por la API key del token.** Cada empresa (Eliot, Pash, Primatela) tiene su propio token. La empresa se deriva del token y **no puede cruzarse**: si un token de Pash intenta crear un ticket cuyo `applicantEmail` es de Eliot, la petición se rechaza con HTTP 403.

Se emitirán tokens separados a Tendency:

- Token 1 → empresa `pash` (para la mesa de ayuda de Pash)
- Token 2 → empresa `eliot` (para la mesa de Tecnología)
- Token 3 → empresa `primatela` (si aplica)

La bifurcación por unidad de negocio la resuelve Tendency del lado del cliente: al leer la unidad de negocio del control vigente, elige el token correcto y llama con él. Los códigos de guion pueden repetirse entre empresas (cada guion está *scoped* por empresa).

**P-09 — ¿Existe un equivalente al estado inicial del caso y al tipo de registro?**

- Todos los tickets creados vía API arrancan siempre en `status = "open"`. No se puede sobreescribir. Este es intencional.
- No existe "tipo de registro". El modelo de DeskEli es más plano: `category` cumple ese rol si Tendency necesita mantener trazabilidad de esa clasificación.

---

### Solicitante (P-10, P-11)

**P-10 — ¿En qué campo se registra la identidad del usuario que originó la solicitud, si el correo solicitante es fijo?**

**Aquí hay que corregir la premisa del análisis:** el correo del solicitante **no es fijo**. La versión de la Guía que recibió Tendency (v1.0 del 27/07/2026) está incompleta. El endpoint productivo `/api/v1/external/tickets` acepta:

```json
{
  "applicantEmail": "juan.perez@pash.com.co",   // ← correo del usuario REAL
  "applicantId": 15192                          // ← alternativa: ID interno de DeskEli
}
```

Uno de los dos es obligatorio. DeskEli busca el usuario por email dentro de la empresa del token; si lo encuentra, lo registra como **creator** del ticket. La cuenta genérica solo se usa como fallback en el caso descrito en P-30.

Adicionalmente, si Tendency envía `authorId`, este puede diferenciarse del `applicantId` (útil cuando un analista crea el ticket en nombre del usuario real).

**P-11 — ¿La mesa de servicio podrá identificar y contactar a ese usuario a partir de la información enviada?**

Sí. El ticket queda con:

- **Creator**: usuario real (nombre, correo, teléfono, área, empresa) — visible en la interfaz del técnico.
- **user_area**, **user_location**, **user_phone**: si se envían explícitamente, sobreescriben lo que trae el perfil del `applicant`.

Esto **resuelve el punto 5.5** del análisis preliminar. **La identidad del solicitante no se pierde.**

---

### Contrato (P-12 a P-14)

**P-12 — ¿Prevalece la Guía de Integración o el requerimiento en cuanto a los campos a mapear?**

**Prevalece el requerimiento TV-CTI-IS-SN-F-01 v2.** La Guía v1.0 solo documenta el subset mínimo obligatorio; el endpoint productivo ya acepta todos los campos que el requerimiento exige mapear (`categoría`, `prioridad`, `autor`, `responsable asignado`, `área`, `ubicación`, `teléfono`, `campos adicionales`). Se publicará la **Guía v2.0** como parte de los insumos (I-05).

**P-13 — ¿Existe documentación ampliada de la interfaz que incluya los campos que el requerimiento ordena mapear?**

Sí. La Guía v2.0 estará lista antes del kickoff del desarrollo. Como referencia inmediata, el contrato productivo del endpoint acepta los siguientes campos (todos opcionales excepto los marcados):

| Campo | Tipo | Obligatorio | Aliases aceptados |
|---|---|---|---|
| `subject` | string(200) | **Sí** | `title` |
| `description` | string | **Sí** | — |
| `applicantEmail` **o** `applicantId` | string / int | **Sí** (uno de los dos) | `applicant_email`, `applicant_id` |
| `authorId` | int | No | `author_id` |
| `category` | string(100) | No (default: "General") | — |
| `priority` | string | No (default: "medium") | — |
| `assigneeEmail` / `assigneeId` | string / int | No | `assignee_email`, `assignee_id` |
| `userArea` | string(120) | No | `user_area` |
| `userLocation` | string(120) | No | `user_location` |
| `userPhone` | string(40) | No | `user_phone` |
| `externalRef` | string(100) | No | `external_ref` |
| `listAdditionalField` | array de objetos | No | `additional_fields` |
| `guion_code` | string(50) | No | `guionCode` |
| `guion_id` | int | No | `guionId` |
| `subtasks` | array | No | `controls` |
| `variables` | object | No | `vars` |
| `attachments` | array | No | — |

**P-14 — ¿Cuál es el nombre definitivo del encabezado de autenticación?**

**`X-Authorization: Bearer <TOKEN>`** es el nombre oficial. Por retrocompatibilidad, el header estándar `Authorization: Bearer <TOKEN>` también es aceptado — se recomienda usar `X-Authorization` para no colisionar con proxies o WAFs intermedios que puedan reescribir `Authorization`.

---

### Credencial (P-15, P-16)

**P-15 — ¿Cuál es la vigencia del token, el procedimiento de rotación y el canal formal para solicitarlo y revocarlo?**

- **Vigencia:** los tokens se emiten **sin fecha de expiración** por defecto. Opcionalmente se puede establecer `expires_at` al momento de la creación.
- **Rotación:** se compromete un procedimiento formal con **ventana de coexistencia de 30 días**. Durante ese lapso, el token viejo y el nuevo son válidos simultáneamente. Tendency migra su configuración cuando pueda dentro de la ventana.
- **Solicitud/revocación:** por correo a la Administración de DeskEli con firma del líder técnico de Tendency. Respuesta objetivo dentro de 2 días hábiles.
- Cada token muestra los primeros 8 caracteres como `token_prefix` en el panel admin, para identificación sin necesidad de descifrar. El token completo solo se muestra una vez, en el momento de la creación.

**P-16 — ¿Qué comportamiento se espera si el token vence durante una operación?**

Respuesta HTTP 401 con `{"error": "Token expirado"}`. Tendency debe interpretar el 401 como señal de escalamiento inmediato al canal formal para renovación. **No se implementará auto-renovación** — es intencional para preservar auditoría y control humano sobre la credencial.

Se agregará en la Guía v2.0 la recomendación de configurar una alerta en el sistema de Tendency **7 días antes** del `expires_at` (si se usa) — DeskEli publicará esta fecha en el panel admin y se comunicará a Tendency al momento de la emisión.

---

### Adjuntos (P-17, P-18)

**P-17 — ¿Cuál es el tamaño máximo por archivo, la cantidad máxima de adjuntos, los tipos de contenido aceptados y el límite total de la petición?**

| Parámetro | Valor |
|---|---|
| Tamaño máximo total de la petición | **25 MB** |
| Tamaño máximo por archivo | 25 MB (limitado por el tamaño total) |
| Cantidad máxima de adjuntos | 20 por ticket (limitado por el tamaño total y validado por el backend) |
| Tipos de contenido aceptados | `pdf`, `doc`, `docx`, `xls`, `xlsx`, `ppt`, `pptx`, `txt`, `csv`, `png`, `jpg`, `jpeg`, `gif`, `bmp`, `webp` |

El límite de 25 MB **es sobre el body completo**, incluyendo `subject`, `description`, `subtasks`, `attachments[].content_base64` y demás campos. Considerando el overhead de base64 (~33%), esto equivale a **~18 MB de contenido binario neto** por petición.

Si el archivo excede el límite, la respuesta es HTTP 413 (Request Entity Too Large). Se recomienda a Tendency validar el tamaño del PDF **antes** de codificar y enviar.

**P-18 — ¿El contenido codificado debe enviarse con prefijo de tipo de dato o sin él?**

**Sin prefijo `data:mime;base64,`.** Solo el contenido base64 puro. El tipo MIME se envía por separado en el campo `mime` del objeto attachment.

```json
{
  "attachments": [
    {
      "filename": "acta_aprobada.pdf",
      "content_base64": "JVBERi0xLjMKJcTl8uXrp/Og0MTGCjQg...",
      "mime": "application/pdf",
      "attach_to": "both"
    }
  ]
}
```

Valores válidos de `attach_to`: `"ticket"`, `"subtasks"`, `"both"` (default: `"both"`).

---

### Idempotencia (P-19, P-20)

**P-19 — ¿Qué comportamiento tiene el servicio cuando se reenvía una misma referencia externa?**

**Al día de hoy, el `externalRef` no bloquea duplicados** — la petición se procesa y crea un ticket nuevo. **Se compromete implementar la guarda de idempotencia** antes del inicio del desarrollo de Tendency:

- Si llega una petición con `externalRef` que ya existe para la empresa del token, el sistema **no crea un ticket nuevo**. En cambio, devuelve HTTP 200 con el ticket original (mismo formato de respuesta que en la creación exitosa, pero con `"idempotent": true`).
- La guarda es por par `(company, externalRef)` — misma referencia en distinta empresa se considera diferente.

**P-20 — ¿Existe algún mecanismo para consultar o conciliar por referencia externa antes de reintentar?**

Sí, se compromete el endpoint `GET /api/v1/external/tickets?externalRef=<ref>` — retorna el ticket si existe o HTTP 404 si no. Se entrega junto con la guarda de idempotencia (mismo release).

---

### Errores (P-21)

**P-21 — ¿Cuál es el contrato definitivo de códigos de error y sus mensajes?**

| HTTP | Escenario | `error_code` (nuevo) |
|---|---|---|
| **200** | Idempotencia — ticket ya existía | `already_exists` |
| **201** | Ticket creado exitosamente | — |
| **400** | Payload inválido, campos faltantes, guion inexistente, categoría inválida | `bad_request`, `missing_field`, `guion_not_found` |
| **401** | Falta el header, token vacío, token inválido, token expirado | `missing_auth`, `invalid_token`, `expired_token` |
| **403** | Token sin scope requerido, solicitante de otra empresa, asignatario cruzado | `forbidden_scope`, `cross_company` |
| **404** | Ticket no existe (en consulta), usuario solicitante no existe | `not_found`, `applicant_not_found` |
| **413** | Body excede 25 MB | `payload_too_large` |
| **429** | Rate limit excedido (100 requests/min por token) | `rate_limited` |
| **500** | Error interno de DeskEli | `internal_error` |

Todos los cuerpos de respuesta con error tienen la forma:

```json
{
  "success": false,
  "error": "Mensaje humano-legible",
  "error_code": "guion_not_found"
}
```

**El campo `error_code` es nuevo** — se agrega en la Guía v2.0 para permitir a Tendency implementar lógica programática sin parsear mensajes en español.

---

### Operación (P-22, P-23, P-24)

**P-22 — ¿Cuál es el tiempo de espera recomendado y la política oficial de reintentos?**

- **Tiempo de espera del cliente (timeout):** 30 segundos para creación de ticket con adjuntos, 10 segundos para consulta de estado.
- **Política oficial de reintentos:**
  - HTTP 5xx: reintento con backoff exponencial — 2s, 5s, 15s, 60s (máx 4 intentos).
  - HTTP 429: respetar el header `Retry-After` (si viene) o backoff de 60s. Máx 3 intentos.
  - HTTP 4xx (excepto 429): **NO reintentar automáticamente** — es error del payload; requiere intervención.
  - HTTP 200/201: obviamente no reintentar; usar `externalRef` para prevenir duplicados en caso de que el cliente no reciba la respuesta.

**P-23 — ¿Existe restricción por dirección de origen que debamos registrar previamente?**

**Sí.** Se aplicará *IP allowlist* al token de producción de Tendency. Se solicita a Tendency:

- Rango de IPs públicas fijas desde donde se harán las llamadas.
- En caso de usar IPs dinámicas o cloud (AWS/GCP/Azure), rango CIDR o mecanismo alternativo (VPN site-to-site, mTLS opcional).

Este control es requisito de Seguridad de la Información. En el ambiente de calidad la restricción se relaja durante la fase de pruebas.

**P-24 — ¿Cuál es el canal y el responsable de escalamiento técnico?**

Ver capítulo 6 (Contactos).

---

### Subtareas vacías (P-25)

**P-25 — ¿Cuál es el comportamiento esperado cuando ningún control aplica a la solicitud: se envía el arreglo vacío o se omite?**

**Se recomienda omitirlo.** Si se envía como arreglo vacío (`"subtasks": []`), el ticket se crea sin subtareas — no falla. Si se envía como `null`, tampoco falla. Ambos comportamientos son equivalentes; se recomienda omitir la clave por limpieza semántica.

Nota: si el ticket usa `guion_code`, no importa lo que traiga `subtasks` — las subtareas las genera el guion. En ausencia de guion y con `subtasks` vacío/omitido, el ticket queda como caso simple sin subtareas.

---

### Ambiente (P-26, P-27)

**P-26 — ¿Existe o puede habilitarse un ambiente de calidad?**

**Sí, se habilitará.** La Administración de DeskEli tomará esto como acción inmediata, con estos parámetros:

- URL: `https://deskeli-qa.eliotproyectos.tech` (o equivalente a acordar).
- Base de datos independiente, con snapshot inicial vacío y usuarios de prueba pre-cargados.
- Tokens de prueba emitidos separadamente (no reutilizables en producción).
- Sin restricción de IP durante la fase de pruebas.
- Mesa de servicio **NO enrutada a colas reales** — los tickets quedan en una cola dedicada de QA.

**Fecha objetivo de entrega del ambiente: 15 de agosto de 2026** (10 días hábiles).

**P-27 — Si no es posible, ¿cuál es la ventana de pruebas autorizada y el procedimiento de limpieza de los casos generados?**

No aplica al confirmarse P-26. Como contingencia (por si el ambiente QA se demora), se autoriza a Tendency:

- Ejecutar pruebas contra producción **solo con `externalRef` prefijado con `TEST-11377-`**. Esto permite identificar y limpiar los casos posteriormente.
- Ventana autorizada: lunes a viernes, 18:00 a 22:00 horas locales.
- La Administración de DeskEli hará limpieza semanal de los tickets con ese prefijo.

---

### Comportamiento actual observado (P-28, P-29)

**P-28 — ¿El valor fijo del campo de ubicación es intencional o corresponde a un defecto a corregir?**

Este punto lo debe responder el **dueño funcional (Cristian López / Seguridad de la Información)** — la Administración de DeskEli no tiene contexto del comportamiento actual de Tendency contra Aranda. Se solicita a Tendency incluir esta pregunta en la reunión de kickoff con el dueño funcional (capítulo 4). La sugerencia técnica de la Administración de DeskEli es: **si el valor de texto sí varía, corregir el valor numérico durante la migración** — es una oportunidad, no un cambio de alcance.

**P-29 — ¿El usuario de red debe enviarse a DeskEli? En caso afirmativo, ¿en qué campo?**

**Sí, se recomienda enviarlo.** Opciones:

1. **Recomendado:** dentro del arreglo `listAdditionalField`:

```json
{
  "listAdditionalField": [
    {"name": "usuario_red", "stringValue": "jperez"}
  ]
}
```

2. **Alternativa:** dentro del campo `variables` si se usa un guion que interpola `{usuario_red}` en las subtareas:

```json
{
  "guion_code": "onboarding-user",
  "variables": {"usuario_red": "jperez"}
}
```

Ambas opciones dejan el dato visible para el técnico y disponible para procesar programáticamente.

---

### Contingencia (P-30)

**P-30 — ¿Debe preverse algún comportamiento degradado equivalente al reintento sin solicitante?**

**No es necesario.** El escenario que hoy resuelve el modo degradado en Aranda (cliente no existe) se resuelve en DeskEli así:

- Si el `applicantEmail` no existe en la empresa del token, DeskEli responde HTTP 400 con `error_code = applicant_not_found`.
- Tendency puede reintentar la misma petición **usando la cuenta genérica como `applicantEmail`** (a definir por unidad de negocio — se entregará como parte de I-03), y colocar los datos del usuario real en `userArea`, `userLocation`, `userPhone` y `listAdditionalField`. El ticket queda creado con toda la información visible para el técnico.
- Se recomienda que este fallback quede loggeado en Tendency para auditoría.

Alternativa preferida: **provisionar los usuarios antes de crear los tickets.** Se compromete un endpoint `POST /api/v1/external/users` para que Tendency pueda crear usuarios *just-in-time* si no existen. Este endpoint queda como *opcional* para la primera fase, según el volumen de casos que Tendency observe.

---

## 3. Aclaración de contradicciones menores (punto 5.4)

| Aspecto | Definición oficial (Guía v2.0) |
|---|---|
| Nombre del encabezado de autenticación | `X-Authorization: Bearer <TOKEN>` (recomendado). `Authorization: Bearer <TOKEN>` (aceptado por compatibilidad). |
| Código de respuesta exitosa | **201 Created** para creación de ticket. **200 OK** para consulta de estado y para casos idempotentes (`externalRef` ya existe). |
| Códigos de error a manejar | Los 5 códigos del requerimiento se aceptan como obligatorios: **400, 401, 403, 404, 500**. Se agregan **413 y 429** por buenas prácticas. Cada respuesta trae `error_code` para lógica programática (ver P-21). |
| Identificación del solicitante | `applicantEmail` **o** `applicantId`, uno de los dos. La cuenta genérica es *fallback* opcional, no requisito. |

---

## 4. Entrega de insumos (capítulo 7)

| # | Insumo | Estado | Fecha compromiso | Responsable |
|---|---|---|---|---|
| I-01 | Token vigente + canal de entrega | **Comprometido** | 12 de agosto de 2026 | Administración de DeskEli |
| I-02 | Ambiente de calidad — URL, credenciales, tokens | **Comprometido** | 15 de agosto de 2026 | Administración de DeskEli |
| I-03 | Catálogo de códigos de guion, categorías, prioridades y grupos por empresa | **Comprometido** — se entregará en formato JSON exportado + CSV humano-legible | 12 de agosto de 2026 | Administración de DeskEli |
| I-04 | Tabla de equivalencia entre controles vigentes y códigos de guion, validada | **En construcción** — se convoca a mesa de trabajo con Cristian López y Seguridad de la Información | 22 de agosto de 2026 | Dueño funcional + Seguridad de la Información |
| I-05 | Documentación ampliada — **Guía de Integración v2.0** | **Comprometido** — cubre todos los campos del requerimiento + endpoints nuevos comprometidos en este documento (`GET /api/v1/external/guiones`, guarda de idempotencia, consulta por `externalRef`) | 12 de agosto de 2026 | Administración de DeskEli |
| I-06 | Contacto técnico de escalamiento + SLA | **Entregado** — ver capítulo 6 | — | Administración de DeskEli |
| I-07 | Definición del comportamiento ante subtareas vacías y referencias duplicadas | **Entregado** — ver P-19, P-20, P-25 | — | Administración de DeskEli |

---

## 5. Postura frente a los riesgos identificados (capítulo 8)

| # | Riesgo | Estado | Acción concreta |
|---|---|---|---|
| R-01 | Pruebas negativas contra producción | **Mitigado** | Se habilita ambiente QA (ver I-02). Contingencia: prefijo `TEST-11377-` autorizado. |
| R-02 | Ausencia de tabla de equivalencia | **En curso** | I-04 con fecha compromiso 22/08/2026. Mesa de trabajo convocada. |
| R-03 | Ausencia del catálogo de enrutamiento | **Mitigado** | I-03 con fecha compromiso 12/08/2026. Aclarada la mecánica en P-07 a P-09: no existe "grupo de asignación" clásico — se maneja por empresa (token) + guion + `assigneeEmail`. |
| R-04 | Pérdida de identidad del solicitante | **Descartado** | La premisa era incorrecta. El endpoint sí acepta el correo del usuario real. Ver P-10. |
| R-05 | Límites de petición no definidos | **Mitigado** | Ver P-17. Límite de 25 MB con detalle de tipos aceptados. |
| R-06 | Ausencia de regla de idempotencia | **Mitigado** | Se implementará la guarda por `externalRef` antes del desarrollo (ver P-19). |
| R-07 | Vencimiento del token sin renovación | **Mitigado** | Procedimiento formal con ventana de coexistencia de 30 días (ver P-15). |

---

## 6. Contactos y escalamiento

| Rol | Nombre | Correo | Canal alterno | SLA de respuesta |
|---|---|---|---|---|
| Administración de DeskEli (punto único) | *(a completar con nombre del líder)* | `basis-sap@patprimo.com.co` | Teams | 4 horas hábiles |
| Dueño funcional del requerimiento | Cristian Ferney López Giraldo | *(pendiente)* | Teams | 1 día hábil |
| Seguridad de la Información (dueño del catálogo de controles) | *(pendiente)* | *(pendiente)* | Correo | 2 días hábiles |
| Service Desk (mesa de ayuda) | *(pendiente)* | *(pendiente)* | Herramienta de tickets | Según SLA operativo |
| Escalamiento en incidentes de producción | Administración de DeskEli | mismo correo, con `[URGENTE-TENDENCY]` en el asunto | Teléfono directo (a compartir aparte) | 1 hora hábil |

---

## 7. Compromisos formales de la Administración de DeskEli

En respuesta al análisis preliminar, la Administración de DeskEli se compromete a:

1. **Publicar la Guía de Integración v2.0** con el contrato completo — antes del **12 de agosto de 2026**.
2. **Habilitar el ambiente de calidad** con base de datos independiente — antes del **15 de agosto de 2026**.
3. **Implementar el endpoint público de catálogo de guiones** (`GET /api/v1/external/guiones`) — antes del **20 de agosto de 2026**.
4. **Implementar la guarda de idempotencia por `externalRef`** — antes del **20 de agosto de 2026**.
5. **Implementar el endpoint de consulta por `externalRef`** (`GET /api/v1/external/tickets?externalRef=...`) — antes del **20 de agosto de 2026**.
6. **Emitir el `error_code` estable** en todas las respuestas de error — antes del **20 de agosto de 2026**.
7. **Entregar los tokens de QA y producción** por correo firmado, con `token_prefix` visible en el panel admin de referencia — según cronograma acordado.
8. **Convocar la mesa de trabajo funcional** con Cristian López y Seguridad de la Información para construir la tabla de equivalencia I-04 — semana del **11 al 15 de agosto de 2026**.
9. **Coordinar la ventana de rotación de tokens** con Tendency, con notificación mínima de 30 días.

---

## 8. Reconocimiento de la propuesta técnica de Tendency

Se valida y agradece:

- **Uso del código interno de la solicitud como `externalRef`** (punto 3.4): se acepta como convención. Es la mejor opción disponible y elimina la necesidad de un mecanismo separado de trazabilidad.
- **Configuración de coexistencia Aranda / DeskEli** (punto 3.3): se recomienda mantenerla durante al menos las primeras 4 semanas post-corte, con la grilla mostrando ambos identificadores. Esto facilita conciliación y rollback si aparecen defectos no detectados en QA.
- **Reemplazo del escenario 5 del plan de pruebas** (punto 5.8): se acepta la propuesta de reemplazar la comparación de estados por una validación de consulta únicamente contra DeskEli. Aranda queda fuera del alcance de las pruebas de estado.
- **Ampliación del maestro de controles con la nueva columna** (capítulo 9): se sugiere que la columna se llame `codigo_guion_deskeli` para claridad, y se mantengan las columnas de Aranda durante la coexistencia.

---

## 9. Próximos pasos

1. **Semana 33 (11–15 de agosto)**
   - Mesa de trabajo funcional para construir I-04.
   - Entrega de la Guía v2.0 y del catálogo I-03.
   - Habilitación del ambiente QA y emisión de tokens de prueba.
2. **Semana 34 (18–22 de agosto)**
   - Tendency emite propuesta de solución técnica y estimación de esfuerzo.
   - DeskEli entrega los endpoints comprometidos (catálogo, idempotencia, consulta por `externalRef`, `error_code`).
3. **Semana 35 en adelante**
   - Kickoff formal del desarrollo por parte de Tendency.
   - Reuniones semanales de seguimiento hasta el corte.

---

## 10. Control de aprobación

| Rol | Nombre | Fecha | Firma |
|---|---|---|---|
| Administración de DeskEli | | | |
| Dueño funcional del requerimiento | Cristian Ferney López Giraldo | | |
| Service Desk | | | |
| Seguridad de la Información | | | |
| TendencyApps S.A.S — Líder técnico | | | |

### Control de versiones

| Versión | Fecha | Descripción del cambio | Elaborado por |
|---|---|---|---|
| 1.0 | 2026-08-05 | Versión inicial. Respuesta formal al análisis preliminar de Tendency v1.0 (2026-08-04). Se responden las 30 preguntas del capítulo 6, se comprometen los 7 insumos y se documenta la postura frente a los 7 riesgos. | Administración de DeskEli — Equipo de Integraciones |
