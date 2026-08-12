/**
 * DeskEli — smartInterval
 *
 * Reemplazo de setInterval con dos mejoras:
 *   1. Pausa automáticamente cuando la pestaña no está visible
 *      (document.hidden === true). Reanuda al volver a foco.
 *   2. Aplica un piso mínimo de 60 segundos para evitar polling agresivo
 *      que satura el backend con múltiples usuarios simultáneos.
 *
 * Uso:
 *   const stop = smartInterval(() => loadStuff(), 30000);   // se ajusta a 60000
 *   const stop = smartInterval(loadStuff, 90000);           // respeta 90s
 *   stop();                                                  // cancelar manualmente
 *
 * Override (para casos legítimos: monitoreo en vivo, etc):
 *   window.SMART_INTERVAL_MIN_MS = 30000;   // subir/bajar el piso globalmente
 *
 * Compat: es un drop-in de setInterval, retorna una función stop() en vez del
 * ID numérico. Si necesitás el ID (por integraciones legacy), pasá
 * {returnId: true} como tercer argumento.
 */
(function () {
    'use strict';

    if (typeof window === 'undefined') return;
    if (window.smartInterval) return;   // evitar redefinición

    // Piso mínimo por defecto. Override en window.SMART_INTERVAL_MIN_MS antes
    // de la primera llamada si tu caso lo justifica.
    const DEFAULT_MIN_MS = 60000;

    // Registro de tareas activas para pausar/reanudar en visibilitychange.
    const _tasks = [];

    function _minMs() {
        const override = Number(window.SMART_INTERVAL_MIN_MS);
        return Number.isFinite(override) && override > 0 ? override : DEFAULT_MIN_MS;
    }

    function _startTimer(task) {
        if (task.timerId != null) return;
        task.timerId = setInterval(() => {
            // Si la pestaña quedó oculta después de arrancar, cortamos el tick.
            if (document.hidden) return;
            try {
                task.fn();
            } catch (e) {
                // No dejamos que un error unitario detenga el ciclo.
                console.error('[smartInterval] tick error:', e);
            }
        }, task.ms);
    }

    function _stopTimer(task) {
        if (task.timerId != null) {
            clearInterval(task.timerId);
            task.timerId = null;
        }
    }

    function _onVisibility() {
        if (document.hidden) {
            // Pausar sin borrar la tarea: al volver a foco, arranca de nuevo.
            _tasks.forEach(_stopTimer);
        } else {
            _tasks.forEach(_startTimer);
        }
    }

    document.addEventListener('visibilitychange', _onVisibility);

    /**
     * @param {Function} fn      Función a ejecutar en cada tick.
     * @param {number}   ms      Intervalo pedido. Se ajusta a min(ms, piso).
     * @param {object=}  opts    { returnId?: boolean, immediate?: boolean }
     * @returns {Function|number} Función stop() por defecto; ID si opts.returnId.
     */
    function smartInterval(fn, ms, opts) {
        opts = opts || {};
        const effectiveMs = Math.max(Number(ms) || DEFAULT_MIN_MS, _minMs());

        const task = { fn: fn, ms: effectiveMs, timerId: null };
        _tasks.push(task);

        // Si la pestaña ya está oculta al registrarse, no arrancamos — quedará
        // en espera del próximo visibilitychange.
        if (!document.hidden) _startTimer(task);

        // Ejecutar inmediatamente si el caller lo pide, respetando visibilidad.
        if (opts.immediate && !document.hidden) {
            try { fn(); } catch (e) { console.error('[smartInterval] immediate error:', e); }
        }

        const stop = function () {
            _stopTimer(task);
            const i = _tasks.indexOf(task);
            if (i !== -1) _tasks.splice(i, 1);
        };

        return opts.returnId ? task.timerId : stop;
    }

    window.smartInterval = smartInterval;
})();
