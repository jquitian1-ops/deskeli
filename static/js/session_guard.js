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
 *
 * Timeout por inactividad: técnico/empleado 10 min, admin 30 min (se sabe
 * el rol vía el mismo /api/session/ping). La actividad se comparte entre
 * pestañas por localStorage para que una pestaña olvidada en segundo plano
 * no cierre la sesión de las demás antes de tiempo.
 */
(function () {
    'use strict';

    if (window.__DESKELI_SESSION_GUARD_LOADED) return;
    window.__DESKELI_SESSION_GUARD_LOADED = true;

    const PING_INTERVAL_MS = 5 * 60 * 1000; // 5 minutos
    const TOAST_TIMEOUT = 5000;

    // ─── Timeout por inactividad (técnico y empleado: 10 min · admin: 30 min) ──
    // Sin actividad del mouse/teclado/touch → logout automático, con aviso +
    // cuenta regresiva durante el último minuto. Antes esto solo existía en
    // una sola página (static/timeout.js, incluido nada más en
    // technician/ticket_detail.html); se mueve acá porque session_guard.js
    // ya se carga en todas las páginas autenticadas de las 3 empresas/roles.
    const IDLE_WARNING_SECONDS = 60;
    let IDLE_TIMEOUT_MINUTES = 10; // default hasta saber el rol (ver _loadIdleTimeoutForRole)

    function _idleTimeoutMs() { return IDLE_TIMEOUT_MINUTES * 60 * 1000; }
    function _idleWarningMs() { return _idleTimeoutMs() - (IDLE_WARNING_SECONDS * 1000); }

    // La actividad se comparte entre TODAS las pestañas/ventanas de la misma
    // sesión vía localStorage (mismo origin). Sin esto, una pestaña olvidada
    // en segundo plano (ej. un ticket abierto hace rato y no cerrado) llega a
    // su propio límite de inactividad ANTES de los 10/30 min reales y cierra
    // la sesión de TODAS las pestañas (es la misma cookie de servidor),
    // aunque el usuario esté activo en otra — se veía como "me saca en menos
    // del tiempo configurado".
    const IDLE_STORAGE_KEY = '__deskeli_last_activity';

    function _lastActivity() {
        try {
            const stored = parseInt(localStorage.getItem(IDLE_STORAGE_KEY), 10);
            if (!isNaN(stored)) return stored;
        } catch (e) { /* localStorage bloqueado (modo privado, etc.) */ }
        return _lastActivityFallback;
    }

    let _lastActivityFallback = Date.now();
    let _idleWarningShown = false;
    let _idleCountdownInterval = null;

    function _resetIdleTimer() {
        const now = Date.now();
        _lastActivityFallback = now;
        try { localStorage.setItem(IDLE_STORAGE_KEY, String(now)); } catch (e) {}
        // Si el usuario vuelve a interactuar mientras el aviso está visible,
        // se cuenta como "Continuar Trabajando" implícito.
        if (_idleWarningShown) hideIdleWarning();
    }

    // Rol conocido recién después de este fetch — hasta entonces se usa el
    // default de 10 min (más conservador) para no dejar a nadie sin timeout
    // mientras se resuelve.
    (function _loadIdleTimeoutForRole() {
        if (_idlePageExempt()) return;
        // Nota: usa el fetch nativo directamente (todavía no está reemplazado
        // acá abajo) — no depende de originalFetch, que se declara más abajo
        // en este mismo archivo y no está disponible todavía en este punto.
        window.fetch('/api/session/ping', {method: 'GET', credentials: 'same-origin'})
            .then(r => r.json())
            .then(data => {
                if (data && data.role === 'admin') IDLE_TIMEOUT_MINUTES = 30;
            })
            .catch(() => {});
    })();

    function _idlePageExempt() {
        // Mismo criterio que shouldPing(): no aplica en login ni páginas públicas.
        const p = location.pathname || '';
        return p === '/login' || p === '/' || p.startsWith('/static/') || p.startsWith('/kb/');
    }

    function showIdleWarning() {
        if (_idleWarningShown || _idlePageExempt()) return;
        _idleWarningShown = true;

        const backdrop = document.createElement('div');
        backdrop.id = '__deskeli_idle_modal';
        backdrop.style.cssText =
            'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:2147483001;' +
            'display:flex;align-items:center;justify-content:center;padding:20px;' +
            'font-family:"Segoe UI",Tahoma,sans-serif;';
        backdrop.innerHTML = `
            <div style="background:white;border-radius:12px;max-width:440px;width:100%;padding:40px 30px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.35);">
                <div style="font-size:56px;margin-bottom:14px;animation:__deskeli_idle_pulse 1s infinite;">⏰</div>
                <div style="font-size:22px;font-weight:800;color:#dc2626;margin-bottom:8px;">¡Tu sesión está por expirar!</div>
                <div style="color:#6b7280;font-size:14px;margin-bottom:18px;">Por seguridad, tu sesión se cerrará por inactividad en:</div>
                <div id="__deskeli_idle_countdown" style="font-size:48px;font-weight:800;color:#dc2626;font-family:'Courier New',monospace;letter-spacing:3px;margin-bottom:8px;">${IDLE_WARNING_SECONDS}</div>
                <div style="color:#9ca3af;font-size:13px;margin-bottom:22px;">segundos</div>
                <div style="display:flex;gap:10px;justify-content:center;">
                    <button onclick="window.__deskeliExtendSession()" style="padding:12px 24px;border:none;border-radius:8px;background:#10b981;color:white;font-weight:700;font-size:14px;cursor:pointer;">Continuar Trabajando</button>
                    <button onclick="location.href='/logout'" style="padding:12px 24px;border:none;border-radius:8px;background:#e5e7eb;color:#374151;font-weight:600;font-size:14px;cursor:pointer;">Cerrar Sesión</button>
                </div>
            </div>
            <style>@keyframes __deskeli_idle_pulse { 0%,100%{opacity:1;} 50%{opacity:0.5;} }</style>
        `;
        document.body.appendChild(backdrop);

        const display = document.getElementById('__deskeli_idle_countdown');
        _idleCountdownInterval = setInterval(() => {
            // Recalcula desde la actividad COMPARTIDA (localStorage) en cada
            // tick — si hubo actividad en OTRA pestaña mientras ésta mostraba
            // el aviso, se cancela solo en vez de cerrar sesión igual.
            const elapsed = Date.now() - _lastActivity();
            if (elapsed < _idleWarningMs()) {
                hideIdleWarning();
                return;
            }
            const remaining = Math.max(0, Math.ceil((_idleTimeoutMs() - elapsed) / 1000));
            if (display) display.textContent = remaining;
            if (remaining <= 0) {
                clearInterval(_idleCountdownInterval);
                location.href = '/logout';
            }
        }, 1000);
    }

    function hideIdleWarning() {
        _idleWarningShown = false;
        if (_idleCountdownInterval) {
            clearInterval(_idleCountdownInterval);
            _idleCountdownInterval = null;
        }
        const el = document.getElementById('__deskeli_idle_modal');
        if (el) el.remove();
    }

    // Expuesto para el botón "Continuar Trabajando" del modal.
    window.__deskeliExtendSession = _resetIdleTimer;

    function _checkIdle() {
        if (_idlePageExempt()) return;
        const elapsed = Date.now() - _lastActivity();
        if (elapsed >= _idleTimeoutMs()) {
            location.href = '/logout';
        } else if (elapsed >= _idleWarningMs()) {
            showIdleWarning();
        } else if (_idleWarningShown) {
            // Hubo actividad (en esta pestaña u otra) que bajó el elapsed
            // por debajo del umbral de aviso — cancelar el aviso mostrado.
            hideIdleWarning();
        }
    }

    document.addEventListener('mousedown', _resetIdleTimer);
    document.addEventListener('keydown', _resetIdleTimer);
    document.addEventListener('touchstart', _resetIdleTimer);
    // Otra pestaña/ventana registró actividad → si ésta está mostrando el
    // aviso de expiración, se cancela sin esperar al próximo tick.
    window.addEventListener('storage', (e) => {
        if (e.key === IDLE_STORAGE_KEY && _idleWarningShown) _checkIdle();
    });
    setInterval(_checkIdle, 5000);

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
    function showToast(msg, type, onClick) {
        // Reutilizar un solo toast
        if (toastEl) toastEl.remove();
        toastEl = document.createElement('div');
        const bgColor = type === 'error' ? '#dc2626' : (type === 'warn' ? '#f59e0b' : (type === 'info' ? '#2563eb' : '#374151'));
        toastEl.style.cssText =
            `position:fixed;bottom:24px;right:24px;background:${bgColor};color:white;` +
            'padding:14px 20px;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,0.25);' +
            'z-index:2147482999;font-family:"Segoe UI",Tahoma,sans-serif;font-size:14px;' +
            'max-width:400px;transition:opacity 0.3s;' +
            (onClick ? 'cursor:pointer;' : '');
        toastEl.textContent = msg;
        if (typeof onClick === 'function') {
            toastEl.addEventListener('click', onClick);
        }
        document.body.appendChild(toastEl);
        const localRef = toastEl;
        setTimeout(() => {
            if (localRef === toastEl) {
                localRef.style.opacity = '0';
                setTimeout(() => { if (localRef.parentNode) localRef.remove(); }, 300);
            }
        }, TOAST_TIMEOUT);
    }

    // Expuesto globalmente para que otras páginas (ej. el chat entre
    // especialistas) puedan reusar el mismo estilo de aviso.
    window.showToast = showToast;

    // ─── Wrapper del fetch ────────────────────────────────────────────
    const originalFetch = window.fetch.bind(window);

    // Cooldown para no spamear el toast "Sin conexion" en un burst
    let _lastNetworkToastAt = 0;
    const NETWORK_TOAST_COOLDOWN_MS = 15000;

    // Endpoints "silenciosos" que NUNCA muestran toast de red (ping keep-alive,
    // polling interno, etc.). Si el server esta reiniciando por 3 segundos y
    // justo cae el ping cada 5 min, el usuario no debe ver alerta.
    const SILENT_NETWORK_ENDPOINTS = [
        '/api/session/ping',
        '/api/admin/sidebar-counts',
        '/api/health',
    ];

    function isSilentUrl(url) {
        return SILENT_NETWORK_ENDPOINTS.some(p => url.indexOf(p) !== -1);
    }

    async function fetchWithRetry(input, init, url) {
        // Solo reintenta GET (metodos con side-effects no se reintentan)
        const method = (init && init.method) || (input && input.method) || 'GET';
        try {
            return await originalFetch(input, init);
        } catch (e1) {
            if (method.toUpperCase() !== 'GET') throw e1;
            // Esperar 500ms y reintentar 1 vez (transient blip por deploy)
            await new Promise(r => setTimeout(r, 500));
            try {
                return await originalFetch(input, init);
            } catch (e2) {
                throw e2;
            }
        }
    }

    window.fetch = async function (input, init) {
        const url = typeof input === 'string' ? input : (input && input.url) || '';
        let response;
        try {
            response = await fetchWithRetry(input, init, url);
        } catch (netErr) {
            // Log detallado en consola siempre (util para diagnostico)
            try {
                console.warn('[session_guard] Fetch fallo:',
                    url, '·', netErr.name, '·', netErr.message);
            } catch (e) {}

            const isApp = url.startsWith('/api/') || url.startsWith('/admin/') ||
                          url.startsWith('/technician/') || url.startsWith('/employee/');

            // No molestar con toast en endpoints silenciosos (ping, polls)
            if (isApp && !isSilentUrl(url)) {
                const now = Date.now();
                if (now - _lastNetworkToastAt > NETWORK_TOAST_COOLDOWN_MS) {
                    _lastNetworkToastAt = now;
                    showToast('🔌 Sin conexión con el servidor. Revisá tu red.', 'error');
                }
            }
            throw netErr;
        }

        // Analizar respuesta solo para llamadas a nuestra API
        // (BUG previo: `url` se volvía a declarar acá con `const`, mismo
        // nombre que arriba en la misma función — SyntaxError que hacía
        // fallar el parseo de TODO este archivo en el navegador, dejando
        // sin efecto el manejo de 401/429/500+ y el keep-alive de sesión
        // en todas las páginas.)
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
