/**
 * session_guard.js — Intercepta fetch() global para manejar sesiones expiradas,
 * rate-limits y errores del servidor de forma consistente.
 *
 * Sin esto, un fetch que recibe 401 se muestra como "Error al cargar" genérico
 * y el usuario no sabe que su sesión expiró.
 *
 * Comportamiento:
 *  - 401 con forced_logout=true  → redirect inmediato a /login?forced_logout=1
 *  - 401 sesión expirada         → modal "Tu sesión expiró" con botón "Reingresar"
 *  - 429 rate-limit              → toast "Demasiadas solicitudes"
 *  - 500+                        → toast "Error del servidor"
 *
 * Keep-alive: ping cada 5 min a /api/session/ping para renovar la cookie
 * mientras el usuario tenga la pestaña abierta.
 */
(function () {
    'use strict';

    if (window.__DESKELI_SESSION_GUARD_LOADED) return;
    window.__DESKELI_SESSION_GUARD_LOADED = true;

    const PING_INTERVAL_MS = 5 * 60 * 1000; // 5 minutos
    const TOAST_TIMEOUT = 5000;

    // ─── UI: modal de sesión expirada ────────────────────────────────
    let sessionExpiredShown = false;
    function showSessionExpiredModal(reason) {
        if (sessionExpiredShown) return;
        sessionExpiredShown = true;

        const backdrop = document.createElement('div');
        backdrop.id = '__deskeli_session_modal';
        backdrop.style.cssText =
            'position:fixed;inset:0;background:rgba(0,0,0,0.65);z-index:2147483000;' +
            'display:flex;align-items:center;justify-content:center;padding:20px;' +
            'font-family:"Segoe UI",Tahoma,sans-serif;backdrop-filter:blur(4px);';

        backdrop.innerHTML = `
            <div style="background:white;border-radius:12px;max-width:440px;width:100%;padding:32px 30px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.3);">
                <div style="font-size:56px;margin-bottom:14px;">⏰</div>
                <h2 style="color:#1f2937;font-size:22px;margin-bottom:10px;">Tu sesión expiró</h2>
                <p style="color:#6b7280;font-size:14px;line-height:1.5;margin-bottom:20px;">
                    ${reason || 'Por seguridad, tu sesión terminó después de un período de inactividad. Volvé a iniciar sesión para continuar.'}
                </p>
                <button onclick="location.href='/login?next=' + encodeURIComponent(location.pathname)"
                        style="width:100%;padding:12px;background:#7c3aed;color:white;border:none;border-radius:8px;font-weight:700;font-size:15px;cursor:pointer;">
                    🔑 Iniciar sesión nuevamente
                </button>
                <button onclick="document.getElementById('__deskeli_session_modal').remove(); window.__DESKELI_SG_dismissed=true;"
                        style="width:100%;padding:8px;background:none;color:#9ca3af;border:none;font-size:12px;cursor:pointer;margin-top:8px;">
                    Cerrar (perderás cambios no guardados)
                </button>
            </div>
        `;
        document.body.appendChild(backdrop);
    }

    // ─── UI: toast para errores no críticos ──────────────────────────
    let toastEl = null;
    function showToast(msg, type) {
        // Reutilizar un solo toast
        if (toastEl) toastEl.remove();
        toastEl = document.createElement('div');
        const bgColor = type === 'error' ? '#dc2626' : (type === 'warn' ? '#f59e0b' : '#374151');
        toastEl.style.cssText =
            `position:fixed;bottom:24px;right:24px;background:${bgColor};color:white;` +
            'padding:14px 20px;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,0.25);' +
            'z-index:2147482999;font-family:"Segoe UI",Tahoma,sans-serif;font-size:14px;' +
            'max-width:400px;transition:opacity 0.3s;';
        toastEl.textContent = msg;
        document.body.appendChild(toastEl);
        const localRef = toastEl;
        setTimeout(() => {
            if (localRef === toastEl) {
                localRef.style.opacity = '0';
                setTimeout(() => { if (localRef.parentNode) localRef.remove(); }, 300);
            }
        }, TOAST_TIMEOUT);
    }

    // ─── Wrapper del fetch ────────────────────────────────────────────
    const originalFetch = window.fetch.bind(window);

    window.fetch = async function (input, init) {
        let response;
        try {
            response = await originalFetch(input, init);
        } catch (netErr) {
            // Error de red (offline, DNS, etc.)
            const url = typeof input === 'string' ? input : (input && input.url) || '';
            if (url.startsWith('/api/') || url.startsWith('/admin/') || url.startsWith('/technician/') || url.startsWith('/employee/')) {
                showToast('🔌 Sin conexión con el servidor. Revisá tu red.', 'error');
            }
            throw netErr;
        }

        // Analizar respuesta solo para llamadas a nuestra API
        const url = typeof input === 'string' ? input : (input && input.url) || '';
        const isOurApi = url.startsWith('/api/') || url.includes(location.host + '/api/');

        if (!isOurApi) return response;

        // Clonar para no consumir el body del caller
        const status = response.status;
        if (status === 401) {
            try {
                const cloned = response.clone();
                const body = await cloned.json();
                if (body && body.forced_logout) {
                    // Expulsado por admin → redirect inmediato
                    location.href = '/login?forced_logout=1';
                    // Devolvemos la respuesta para que el caller no se rompa
                    return response;
                }
                if (body && body.must_change_password && body.redirect) {
                    location.href = body.redirect;
                    return response;
                }
            } catch (e) { /* body no era JSON válido, ignorar */ }

            if (!window.__DESKELI_SG_dismissed) {
                showSessionExpiredModal();
            }
        } else if (status === 429) {
            showToast('⚠ Demasiadas solicitudes. Esperá un momento e intentá de nuevo.', 'warn');
        } else if (status >= 500) {
            // Loggear el detalle en consola para diagnostico
            try {
                const cloned = response.clone();
                cloned.text().then(txt => {
                    console.groupCollapsed(
                        '%c[session_guard] Error ' + status + ' en ' + url,
                        'color:#dc2626;font-weight:bold;'
                    );
                    console.error('URL:', url);
                    console.error('Status:', status);
                    // Intentar parsear como JSON (el error handler devuelve JSON con traceback)
                    try {
                        const data = JSON.parse(txt);
                        console.error('Error:', data.error);
                        console.error('Path:', data.path);
                        if (data.traceback) console.error('Traceback:\n' + data.traceback);
                        else console.error('Response body:', data);
                    } catch (e) {
                        console.error('Body (no-JSON):', txt.slice(0, 2000));
                    }
                    console.groupEnd();
                }).catch(() => { /* silencioso */ });
            } catch (e) { /* clone puede fallar en algunos browsers */ }

            showToast('⚠ Error del servidor (' + status + '). Si persiste, avisá al equipo de TI.', 'error');
        }

        return response;
    };

    // ─── Keep-alive ───────────────────────────────────────────────────
    // Solo pinguear si hay sesión (no en /login ni /static)
    function shouldPing() {
        const p = location.pathname || '';
        if (p === '/login' || p === '/' || p.startsWith('/static/') || p.startsWith('/kb/')) return false;
        return true;
    }

    async function ping() {
        if (!shouldPing()) return;
        if (document.hidden) return; // no pinguear si la pestaña está oculta
        try {
            const r = await originalFetch('/api/session/ping', {method: 'GET', credentials: 'same-origin'});
            if (r.status === 401 && !window.__DESKELI_SG_dismissed) {
                showSessionExpiredModal();
            }
        } catch (e) { /* silencioso */ }
    }

    // Ping cada 5 min mientras la pestaña esté activa
    setInterval(ping, PING_INTERVAL_MS);

    // Ping al volver a la pestaña después de estar oculta
    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) ping();
    });

})();
