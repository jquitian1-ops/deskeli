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
    // Recargar cola si estamos en technician dashboard
    if (window.location.pathname.includes('/technician/dashboard')) {
        location.reload();
    }
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

// RT-04: Ticket cerrado
socket.on('ticket_closed', (data) => {
    console.log('[RT-04] Ticket cerrado:', data.ticket.ticket_number);
    showNotification(`Ticket resuelto: ${data.ticket.ticket_number}`);
});

// RT-07: Métricas de conexión
socket.on('user_kicked', (data) => {
    console.log('[RT-04] Usuario expulsado');
    showNotification('Tu sesión fue cerrada remotamente');
    setTimeout(() => window.location.href = '/logout', 2000);
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
