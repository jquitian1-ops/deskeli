/**
 * devtools_blocker.js — Portal de Empleados
 *
 * Barrera COSMETICA (no es seguridad real). Bloquea F12, Ctrl+Shift+I/J/C,
 * Ctrl+U y click derecho. Detecta si DevTools está abierto y muestra un
 * overlay de advertencia. Un usuario con conocimientos técnicos puede
 * bypasear esto — la seguridad real vive en el backend (auth, RBAC, JWT,
 * sanitización, audit log). Este script solo disuade la curiosidad casual.
 *
 * Para desactivar temporalmente en debug: window.__DESKELI_ALLOW_DEVTOOLS = true
 */
(function () {
    'use strict';

    // Escape hatch para debug del propio equipo TI
    if (window.__DESKELI_ALLOW_DEVTOOLS) return;

    // ── Bloquear atajos de teclado ──────────────────────────────────
    document.addEventListener('keydown', function (e) {
        // F12
        if (e.keyCode === 123) { e.preventDefault(); return false; }
        // Ctrl+Shift+I / J / C  (Inspector, Console, Selector)
        if (e.ctrlKey && e.shiftKey && (e.keyCode === 73 || e.keyCode === 74 || e.keyCode === 67)) {
            e.preventDefault();
            return false;
        }
        // Ctrl+U (ver código fuente)
        if (e.ctrlKey && e.keyCode === 85) { e.preventDefault(); return false; }
        // Ctrl+S (guardar página)
        if (e.ctrlKey && e.keyCode === 83) { e.preventDefault(); return false; }
    }, true);

    // ── Bloquear click derecho ──────────────────────────────────────
    document.addEventListener('contextmenu', function (e) {
        e.preventDefault();
        return false;
    }, true);

    // ── Overlay de advertencia ──────────────────────────────────────
    function showWarning() {
        if (document.getElementById('__deskeli_devtools_warn')) return;
        const overlay = document.createElement('div');
        overlay.id = '__deskeli_devtools_warn';
        overlay.style.cssText =
            'position:fixed;inset:0;background:rgba(30,30,40,0.98);z-index:999999;' +
            'display:flex;align-items:center;justify-content:center;color:white;' +
            'font-family:"Segoe UI",Tahoma,sans-serif;';
        overlay.innerHTML =
            '<div style="max-width:500px;padding:40px;text-align:center;">' +
            '<div style="font-size:72px;margin-bottom:20px;">🔒</div>' +
            '<h1 style="font-size:26px;margin-bottom:14px;font-weight:800;">Acceso restringido</h1>' +
            '<p style="font-size:15px;opacity:0.9;line-height:1.6;margin-bottom:20px;">' +
            'Por políticas de seguridad de la empresa, las herramientas de desarrollo ' +
            'no están permitidas en el portal de empleados. Cerrá DevTools y presioná ' +
            'el botón para continuar.</p>' +
            '<p style="font-size:12px;opacity:0.6;margin-bottom:20px;">' +
            'Este evento queda registrado en el log de auditoría.</p>' +
            '<button onclick="location.reload()" style="background:#7c3aed;color:white;border:none;' +
            'padding:12px 28px;border-radius:6px;font-size:14px;font-weight:700;cursor:pointer;">' +
            'Continuar</button>' +
            '</div>';
        document.body.appendChild(overlay);
    }

    // ── Detector: DevTools abierto ──────────────────────────────────
    // Método 1: diferencia entre outerWidth/innerWidth (heurística clásica)
    function checkDevToolsSize() {
        const threshold = 160;
        const widthDiff = window.outerWidth - window.innerWidth;
        const heightDiff = window.outerHeight - window.innerHeight;
        if (widthDiff > threshold || heightDiff > threshold) {
            showWarning();
        }
    }
    setInterval(checkDevToolsSize, 1000);

    // Método 2: debugger trap con tiempo (si DevTools está abierto, el debugger pausa)
    function debuggerTrap() {
        const start = performance.now();
        // eslint-disable-next-line no-debugger
        debugger;
        const elapsed = performance.now() - start;
        if (elapsed > 100) {
            showWarning();
            reportDevtoolsToAudit();
        }
    }
    setInterval(debuggerTrap, 2000);

    // ── Reportar al audit log del servidor (best-effort) ────────────
    let __reported = false;
    function reportDevtoolsToAudit() {
        if (__reported) return;
        __reported = true;
        try {
            fetch('/api/security/devtools-detected', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    url: location.pathname,
                    ua: navigator.userAgent,
                    ts: new Date().toISOString()
                })
            }).catch(() => {});
        } catch (e) { /* silent */ }
    }

    // ── Deshabilitar selección + drag de imágenes ───────────────────
    document.addEventListener('dragstart', function (e) { e.preventDefault(); return false; }, true);
    document.addEventListener('selectstart', function (e) {
        // Permitir seleccionar en inputs y textareas (para que se pueda escribir)
        const tag = (e.target.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea') return true;
        e.preventDefault();
        return false;
    }, true);
})();
