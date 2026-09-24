// WEBSOCKET SOCKET.IO RT-01 A RT-07
// Propagación real-time de cambios a todos los clientes conectados

const socket = io();

// RT-01: Conectar a sala por company
socket.on('connect', () => {
    console.log('[Socket.IO] Conectado al servidor');
});

socket.on('disconnect', () => {
    console.log('[Socket.IO] Desconectado del servidor');
});

socket.on('user_connected', (data) => {
    console.log('[RT-01] Usuario conectado:', data.user, 'en', data.company);
});

// RT-02: Ticket creado - aparece en tiempo real
socket.on('ticket_created', (data) => {
    console.log('[RT-02] Nuevo ticket creado:', data.ticket);
    showNotification(`Nuevo ticket: ${data.ticket.ticket_number}`);
    // Refrescar los contadores del sidebar del Portal de Técnicos sin
    // recargar toda la página (antes hacía location.reload() acá, que
    // interrumpía cualquier cosa que el técnico estuviera haciendo con
    // CUALQUIER ticket nuevo de la empresa, no solo los propios).
    _refreshTechnicianSidebarCounts();
});

// RT-03: Ticket actualizado - aparece el cambio en tiempo real
socket.on('ticket_updated', (data) => {
    console.log('[RT-03] Ticket actualizado:', data.ticket.ticket_number);
    showNotification(`Ticket actualizado: ${data.ticket.ticket_number}`);
    // Recargar si estamos viendo ese ticket
    if (window.location.pathname.includes(`/ticket/${data.ticket.id}`)) {
        location.reload();
    }
});

// Ticket asignado/reasignado o cambio de estado: puede afectar los
// contadores "Asignados a mí" / "De mis grupos" del sidebar.
socket.on('ticket_assigned', () => _refreshTechnicianSidebarCounts());
socket.on('ticket_status_changed', () => _refreshTechnicianSidebarCounts());
socket.on('ticket_resolved', () => _refreshTechnicianSidebarCounts());
socket.on('ticket_reopened', () => _refreshTechnicianSidebarCounts());
socket.on('ticket_escalated', () => _refreshTechnicianSidebarCounts());
// Subtarea creada/reasignada/cambio de estado: afecta "Asignadas a mí" /
// "De mis grupos" bajo Subtareas.
socket.on('subtask_changed', () => _refreshTechnicianSidebarCounts());

// RT-04: Ticket cerrado
socket.on('ticket_closed', (data) => {
    console.log('[RT-04] Ticket cerrado:', data.ticket.ticket_number);
    showNotification(`Ticket resuelto: ${data.ticket.ticket_number}`);
});

// Trae los 4 conteos del sidebar (Tickets/Subtareas × mías/de mis grupos)
// y actualiza los badges sin recargar la página. Solo aplica en el Portal
// de Técnicos — no-op silencioso en cualquier otra página (admin, empleado).
let _sidebarCountsRefreshTimer = null;
function _refreshTechnicianSidebarCounts() {
    if (!window.location.pathname.includes('/technician/dashboard')) return;
    // Debounce: varios eventos pueden llegar juntos (ej. un flujo que genera
    // 20 subtareas de golpe dispara 20 'subtask_changed') — una sola consulta alcanza.
    clearTimeout(_sidebarCountsRefreshTimer);
    _sidebarCountsRefreshTimer = setTimeout(() => {
        fetch('/api/technician/sidebar-counts')
            .then(r => r.json())
            .then(data => {
                if (!data.success) return;
                const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
                setText('countTicketsMine', data.tickets_mine);
                setText('countTicketsTeam', data.tickets_team);
                setText('countSubtasksMine', data.subtasks_mine);
                setText('countSubtasksTeam', data.subtasks_team);
            })
            .catch(() => { /* silencioso */ });
    }, 800);
}

// RT-07: Métricas de conexión
socket.on('user_kicked', (data) => {
    console.log('[RT-04] Usuario expulsado');
    showNotification('Tu sesión fue cerrada remotamente');
    setTimeout(() => window.location.href = '/logout', 2000);
});

// Chat interno entre especialistas (DM 1-a-1 o canal grupal): el servidor
// emite esto a la sala del destinatario (ver api_chat_specialists_send()).
// Se reenvía como evento de window para que cada dashboard reaccione con su
// propia lógica de badge/banner sin acoplar este script a esos detalles.
socket.on('chat_message', (data) => {
    console.log('[Chat] Mensaje recibido:', data);
    window.dispatchEvent(new CustomEvent('deskeli:chat-message', { detail: data }));
});

function showNotification(message) {
    // Mostrar notificación tipo toast
    if (Notification && Notification.permission === 'granted') {
        new Notification('TicketDesk', {
            body: message,
            icon: '/static/icon.png'
        });
    }
    console.log('[Notificación]', message);
}

// Solicitar permiso para notificaciones
if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
    Notification.requestPermission();
}
