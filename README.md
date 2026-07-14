# 🎟️ TicketDesk Enterprise - Proyecto Funcionando

Sistema web de gestión de incidencias de TI con 3 portales interactivos.

## 🚀 Quick Start (5 minutos)

### Requisitos
- Python 3.10+
- pip (gestor de paquetes Python)

### Instalación

```bash
# 1. Clonar o descargar este directorio
cd proyecto_funcionando

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno (Windows)
venv\Scripts\activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Ejecutar la aplicación
python app.py
```

### Acceder

Abre navegador y ve a: **http://localhost:5050**

```
🔗 URL: http://localhost:5050
```

---

## 📝 Usuarios de Prueba

Puedes ingresar con cualquiera de estos usuarios:

| Usuario | Rol | Empresa | Contraseña |
|---------|-----|---------|------------|
| **john** | Empleado | Manufacturas Eliot | (sin contraseña) |
| **carlos** | Técnico | Manufacturas Eliot | (sin contraseña) |
| **ana** | Admin | Manufacturas Eliot | (sin contraseña) |

**Instrucciones:**
1. Selecciona el rol que quieres probar (Empleado, Técnico, Admin)
2. Click en "Ingresar"
3. ¡Listo! Estás dentro

---

## 🎯 Qué Puedes Hacer

### 👤 Portal de Empleados (john)
- ✅ Ver mis tickets abiertos
- ✅ Crear nuevo ticket
- ✅ Ver estado en tiempo real
- ✅ Chat con técnico
- ✅ Calificar resolución

**Ruta:** http://localhost:5050/employee/dashboard

### 👨‍💼 Portal de Técnicos (carlos)
- ✅ Ver cola de trabajo (tickets asignados)
- ✅ Recibir sugerencias de IA
- ✅ Responder a empleados en chat
- ✅ Marcar como resuelto
- ✅ Ver métricas de SLA

**Ruta:** http://localhost:5050/technician/dashboard

### 👩‍💻 Portal de Admin (ana)
- ✅ Ver dashboard ejecutivo
- ✅ Métricas por empresa
- ✅ Tablero Kanban
- ✅ Salud de SLA
- ✅ Desempeño de equipos

**Ruta:** http://localhost:5050/admin/dashboard

---

## 🔑 Características Implementadas

✅ **3 Portales Separados** — Empleado, Técnico, Admin  
✅ **Login/Autenticación** — Sistema de sesiones  
✅ **Gestión de Tickets** — Crear, asignar, resolver  
✅ **Chat en Tiempo Real** — Comunicación empleado-técnico  
✅ **Sugerencias IA** — Bot analysis de tickets  
✅ **SLA Tracking** — Contadores de tiempo  
✅ **Dashboards** — Métricas y visualización  
✅ **Datos Mock** — Poblados con ejemplos reales  

---

## 📁 Estructura del Proyecto

```
proyecto_funcionando/
├── app.py                          # Aplicación Flask principal
├── requirements.txt                # Dependencias Python
├── README.md                       # Este archivo
│
└── templates/
    ├── login.html                  # Pantalla de login
    │
    ├── employee/
    │   ├── dashboard.html          # Panel empleado
    │   ├── create_ticket.html      # Crear ticket
    │   └── ticket_detail.html      # Detalle ticket
    │
    ├── technician/
    │   ├── dashboard.html          # Cola de técnico
    │   └── ticket_detail.html      # Detalle (vista técnico)
    │
    └── admin/
        └── dashboard.html          # Panel administrativo
```

---

## 🛠️ Comandos Útiles

```bash
# Ejecutar con debug (recargar automático)
python app.py

# Ejecutar en puerto diferente
python app.py --port 8080

# Verificar salud del servidor
curl http://localhost:5050/api/health

# Ver todos los tickets (JSON)
curl http://localhost:5050/api/tickets
```

---

## 📊 API Endpoints Disponibles

```
GET  /api/health              # Estado del servidor
GET  /api/tickets             # Lista de todos los tickets
POST /api/ticket/<id>/message # Agregar comentario a ticket
```

---

## 🧪 Casos de Uso (Pruebas)

### Caso 1: Crear un Ticket
1. Ingresa como **john** (Empleado)
2. Click "Crear Nuevo Ticket"
3. Llena el formulario
4. ¡Verás el nuevo ticket instantáneamente!

### Caso 2: Responder como Técnico
1. Ingresa como **carlos** (Técnico)
2. Haz click en un ticket
3. Ve la sugerencia de IA
4. Responde al empleado

### Caso 3: Ver Métricas
1. Ingresa como **ana** (Admin)
2. Ve el dashboard con:
   - 347 tickets totales
   - 98% SLA cumplido
   - Desempeño por empresa
   - Kanban en tiempo real

---

## 🔮 Próximas Fases

Este es el **MVP (Producto Mínimo Viable)**. Próximas mejoras:

- [ ] Base de datos real (PostgreSQL)
- [ ] Autenticación LDAP/AD
- [ ] WebSocket real-time
- [ ] Integración Claude API
- [ ] Asignación automática con IA
- [ ] Notificaciones push
- [ ] Reportes avanzados
- [ ] Integración Teams

---

## ❓ Troubleshooting

### "Puerto 5050 en uso"
```bash
# Cambiar puerto en app.py línea 165:
app.run(debug=True, host='0.0.0.0', port=8080)  # Cambiar a 8080
```

### "No puedo activar venv"
```bash
# En Windows:
python -m venv venv
venv\Scripts\activate

# En Mac/Linux:
python3 -m venv venv
source venv/bin/activate
```

### "ModuleNotFoundError: Flask"
```bash
# Asegúrate de haber instalado dependencias:
pip install -r requirements.txt
```

---

## 📧 Información del Proyecto

**Proyecto:** TicketDesk Enterprise  
**Versión:** 1.0.0 MVP  
**Estado:** Funcionando  
**Última actualización:** Mayo 28, 2026

---

## 🎯 Notas Importantes

1. **Sin persistencia:** Los datos se pierden al reiniciar (en memoria)
2. **Sin autenticación real:** Cualquiera puede ingresar con cualquier usuario
3. **Mock data:** Los tickets son ejemplos, no reales
4. **Single server:** No es escalable (solo desarrollo)

Para **producción**, ver `/proyecto_final/` con especificaciones completas.

---

¡Disfruta explorando TicketDesk Enterprise! 🚀
