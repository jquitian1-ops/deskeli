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
 *
 * v2 (2026-07-09): Reducidos falsos positivos:
 * - Threshold subido de 160 a 260 px
 * - Requiere 3 detecciones consecutivas antes de mostrar overlay
 * - Removido el "debugger trap" (causaba falsos positivos por GC/pestañas)
 * - Grace period de 5 seg al arranque
 * - Ignora dispositivos con touch (móviles/tablets)
 */
(function () {
    'use strict';

    // Escape hatch para debug del propio equipo TI
    if (window.__DESKELI_ALLOW_DEVTOOLS) return;

    // No aplicar en dispositivos táctiles (móvil/tablet — no tienen DevTools típicamente)
    const isTouchDevice = ('ontouchstart' in window) ||
                          (navigator.maxTouchPoints > 0) ||
                          (window.matchMedia && window.matchMedia('(pointer:coarse)').matches);

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
    let __overlayShown = false;
    function showWarning() {
        if (__overlayShown) return;
        if (document.getElementById('__deskeli_devtools_warn')) return;
        __overlayShown = true;
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

    // ── Detector: DevTools abierto (heurística de tamaño de ventana) ──
    // Solo se activa tras 5 seg de grace period, requiere 3 detecciones
    // consecutivas y threshold generoso para evitar falsos positivos
    // por extensiones, zoom del navegador, barras de bookmarks, etc.
    const THRESHOLD_PX = 260;          // subido de 160 (falsos positivos con extensiones)
    const CONSECUTIVE_REQUIRED = 3;    // ~3 seg de detección continua
    const GRACE_PERIOD_MS = 5000;      // no chequear durante el arranque
    let consecutiveDetections = 0;
    let startupTime = Date.now();

    function checkDevToolsSize() {
        if (__overlayShown) return;
        if (isTouchDevice) return;
        if (Date.now() - startupTime < GRACE_PERIOD_MS) return;
        // Requiere que el navegador reporte outerWidth/innerWidth validos
        if (!window.outerWidth || !window.innerWidth) return;

        const widthDiff = window.outerWidth - window.innerWidth;
        const heightDiff = window.outerHeight - window.innerHeight;

        // DevTools abierto a un costado o abajo generalmente resta ancho o alto
        // significativamente. Con threshold de 260 filtramos extensiones y
        // barras de bookmarks (que rara vez ocupan mas de 200 px).
        if (widthDiff > THRESHOLD_PX || heightDiff > THRESHOLD_PX) {
            consecutiveDetections++;
            if (consecutiveDetections >= CONSECUTIVE_REQUIRED) {
                showWarning();
                reportDevtoolsToAudit();
            }
        } else {
            consecutiveDetections = 0;  // reset si vuelve a la normalidad
        }
    }
    setInterval(checkDevToolsSize, 1000);

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

    // ── Deshabilitar drag de imágenes (solo eso — la selección de texto queda) ──
    document.addEventListener('dragstart', function (e) {
        const tag = (e.target && e.target.tagName || '').toLowerCase();
        if (tag === 'img') { e.preventDefault(); return false; }
    }, true);
})();
