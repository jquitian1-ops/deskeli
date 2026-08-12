"""Decoradores de autenticación/autorización.

Reemplazan los 230 checks de auth inline copiados a mano en app.py.
Uso:

    from security.decorators import require_role, require_login

    @app.route('/api/admin/foo')
    @require_role('admin')                    # solo admins
    def api_admin_foo():
        ...

    @app.route('/api/technician/bar')
    @require_role('technician', 'admin')      # técnicos o admins
    def api_technician_bar():
        ...

    @app.route('/api/session/baz')
    @require_login                            # cualquier user logueado
    def api_session_baz():
        ...

Detalles importantes:
  * El comportamiento es idéntico al patrón viejo:
        if 'user_id' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'error': 'No autorizado'}), 401
    …excepto que ahora los errores llevan `error_code` estable (útil para
    Tendency y para tests que aserten el motivo del rechazo).
  * `require_login` NO valida rol — solo que hay sesión activa.
  * `require_role` implícitamente ya requiere login (si no hay `user_id`,
    rechaza antes de mirar rol).
  * Siempre se retorna JSON. Endpoints que renderizan HTML deben seguir
    usando el patrón viejo con `redirect(url_for('login'))` hasta que
    creemos un decorador específico para páginas.

No importa Flask.session directamente para evitar dependencia circular en
tests que mockean `session`. Se resuelve dinámicamente vía `from flask import
session as _session` dentro de la función.
"""
from __future__ import annotations

import functools
from typing import Callable


def _make_json_error(message: str, error_code: str, http_status: int):
    """Helper para armar la respuesta de error uniforme.
    Se importa jsonify tarde para no requerir Flask context en el import."""
    from flask import jsonify
    return jsonify({
        'success': False,
        'error': message,
        'error_code': error_code,
    }), http_status


def require_login(fn: Callable) -> Callable:
    """Requiere una sesión activa (cualquier rol). 401 si no hay `user_id`."""
    @functools.wraps(fn)
    def _wrapper(*args, **kwargs):
        from flask import session
        if 'user_id' not in session:
            return _make_json_error('No autorizado', 'unauthenticated', 401)
        return fn(*args, **kwargs)
    return _wrapper


def require_role(*allowed_roles: str) -> Callable:
    """Requiere que la sesión tenga rol en `allowed_roles`.

    - 401 si no hay sesión.
    - 403 si hay sesión pero el rol no está permitido.
    """
    if not allowed_roles:
        raise ValueError('require_role necesita al menos un rol permitido')

    _roles_set = frozenset(allowed_roles)

    def _decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def _wrapper(*args, **kwargs):
            from flask import session
            if 'user_id' not in session:
                return _make_json_error('No autorizado', 'unauthenticated', 401)
            if session.get('role') not in _roles_set:
                return _make_json_error(
                    'Sin permisos para esta operación',
                    'forbidden_role',
                    403,
                )
            return fn(*args, **kwargs)
        return _wrapper
    return _decorator


def require_admin(fn: Callable) -> Callable:
    """Atajo semántico. Equivalente a @require_role('admin')."""
    return require_role('admin')(fn)


def require_technician_or_admin(fn: Callable) -> Callable:
    """Atajo semántico. Equivalente a @require_role('technician', 'admin')."""
    return require_role('technician', 'admin')(fn)
