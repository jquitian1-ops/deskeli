// SPANISH MEXICANO COMPLETO - Traducciones globales

const i18n = {
  es: {
    // Autenticación
    "login": "Iniciar Sesión",
    "logout": "Cerrar Sesión",
    "welcome": "Bienvenido",
    "invalid_credentials": "Usuario o contraseña inválidos",
    
    // Tickets
    "new_ticket": "Nuevo Ticket",
    "ticket_created": "Ticket creado exitosamente",
    "ticket_updated": "Ticket actualizado",
    "ticket_resolved": "Ticket resuelto",
    "status": "Estado",
    "priority": "Prioridad",
    "category": "Categoría",
    "description": "Descripción",
    
    // Estados
    "open": "Abierto",
    "in_progress": "En Progreso",
    "resolved": "Resuelto",
    
    // Prioridades
    "low": "Baja",
    "medium": "Media",
    "high": "Alta",
    "critical": "Crítica",
    
    // Botones
    "save": "Guardar",
    "cancel": "Cancelar",
    "delete": "Eliminar",
    "edit": "Editar",
    "search": "Buscar",
    "filter": "Filtrar",
    "export": "Exportar",
    "import": "Importar",
    
    // Mensajes
    "loading": "Cargando...",
    "error": "Error",
    "success": "Éxito",
    "warning": "Advertencia",
    "confirm": "¿Estás seguro?",
    "no_results": "Sin resultados",
    
    // Reportes
    "total_tickets": "Total de Tickets",
    "resolved": "Resueltos",
    "sla_compliance": "Cumplimiento SLA",
    "average_resolution": "Resolución Promedio",
    "technician_workload": "Carga por Técnico",
    
    // Admin
    "settings": "Configuración",
    "users": "Usuarios",
    "companies": "Empresas",
    "templates": "Plantillas",
    "servers": "Servidores",
    "webhooks": "Webhooks",
    "backups": "Respaldos",
    "audit_logs": "Registros de Auditoría"
  }
};

function t(key) {
  return i18n.es[key] || key;
}
