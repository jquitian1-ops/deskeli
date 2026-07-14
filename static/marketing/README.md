# Material de comunicación — DeskEli

Piezas listas para difundir DeskEli a los empleados de las 3 empresas.
**Sin fecha de lanzamiento** — sirven en cualquier momento (evergreen).

## Archivos

| Archivo | Propósito |
|---|---|
| `email_eliot.html` | Correo corporativo para Manufactureras Eliot (paleta azul) |
| `email_pash.html` | Correo corporativo para Pash (paleta púrpura) |
| `email_primatela.html` | Correo corporativo para Primatela (paleta verde) |
| `email_texto_plano.txt` | Versión de sólo texto (accesibilidad, Outlook antiguos, filtros) |

## Cómo enviarlos

### Opción A — Desde Outlook / cliente de correo

1. Abrí el `.html` en un navegador (Chrome o Edge).
2. `Ctrl + A` para seleccionar todo → `Ctrl + C` para copiar.
3. En Outlook: **Nuevo correo → Formato HTML** → `Ctrl + V`.
4. Ajustá el asunto y los destinatarios (CCO para envíos masivos).
5. Enviá.

### Opción B — Desde un servicio de email marketing (Mailchimp, SendGrid, etc.)

1. Creá una campaña "HTML personalizado".
2. Pegá el contenido completo del `.html`.
3. Configurá los enlaces de tracking si tu proveedor lo permite.
4. Enviá o programá.

### Opción C — Desde el propio DeskEli (SMTP configurado)

Podés adaptar el HTML como plantilla del sistema y enviarlo con `send_email()`
desde un script auxiliar.

## Personalización recomendada antes de enviar

1. **Asunto**: elegí uno según el tono
   - Corporativo: "Presentamos DeskEli — Tu nueva mesa de ayuda TI"
   - Directo: "Ahora podés reportar incidencias de TI en un solo lugar"
   - Beneficio: "Menos llamadas al TI, más tiempo para lo que importa"

2. **Firma**: reemplazá "Dirección de Tecnología" por tu nombre + cargo real
   si querés que sea más personal.

3. **URL**: si tu instancia usa otro dominio, cambiá
   `https://deskeli.eliotproyectos.tech` por el correcto.

## Buenas prácticas de envío

- **CCO / BCC**: nunca poner 8.000 correos en TO o CC. Usar CCO o lotes.
- **Horario**: enviar martes o jueves 9-11 AM tiene mejor tasa de apertura.
- **Cliente**: envialo primero a vos mismo y revisalo en Gmail, Outlook web
  y Outlook de escritorio antes del envío masivo.
- **Tracking**: si usás herramienta de email marketing, activá tracking de
  aperturas para medir efectividad.

## Métricas a esperar (referencia sector interno)

- **Tasa de apertura**: 40-60% (empleados internos leen más que público general)
- **Click en CTA**: 8-15% en la primera semana post-envío
- **Registro/uso**: 5-10% de los que abren el correo entran al portal en 24h

## Refuerzo posterior

A los 3-5 días del primer envío, considerá:
- Mensaje corto por Teams recordando el link
- Poster/flyer en salas de reuniones y comedores
- Slide en pantallas de recepción (si aplica)

## Preguntas / soporte

Si necesitás ajustar tono, colores, longitud o agregar secciones, pedí ayuda
al desarrollador que mantiene DeskEli.
