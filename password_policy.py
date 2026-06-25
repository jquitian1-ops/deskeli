"""
Política de contraseñas de DeskEli.

Reglas:
- Longitud mínima 8 (configurable vía MIN_PASSWORD_LENGTH)
- Debe contener letras y dígitos
- No puede ser igual al username (que se usa como salt)
- No puede estar en la lista de contraseñas comunes/débiles

Uso:
    ok, error = validate_password(new_pw, username='jdoe')
    if not ok:
        return jsonify({'error': error}), 400
"""
from __future__ import annotations

import os
import re
from typing import Optional, Tuple

MIN_PASSWORD_LENGTH = int(os.getenv('MIN_PASSWORD_LENGTH', '8'))

# Top contraseñas filtradas/débiles. Lista corta y útil; cubre las más comunes.
# Fuente: NIST 800-63B, lista de SecLists.
_COMMON_PASSWORDS = frozenset({
    '12345678', '123456789', '1234567890', '11111111', '00000000',
    'password', 'password1', 'password12', 'password123', 'pass1234',
    'qwerty', 'qwerty123', 'qwertyui', 'qwertyuiop', 'qwerty12',
    'abc12345', 'abcd1234', 'abcdef1', 'abcd1234!',
    'admin', 'admin123', 'admin1234', 'administrator',
    'letmein', 'letmein1', 'welcome1', 'welcome123', 'welcome2024', 'welcome2025', 'welcome2026',
    'iloveyou', 'iloveyou1',
    'monkey123', 'dragon123', 'football',
    'sunshine', 'princess', 'master123',
    'superman', 'batman123',
    'changeme', 'changeme1', 'changeme123',
    'temporal', 'temporal1', 'temporal123',
    'soporte', 'soporte1', 'soporte123',
    'usuario1', 'usuario123', 'cliente1', 'cliente123',
    'p@ssw0rd', 'p@ssword1', 'pa$$word1',
    # Patrones obvios contextuales
    'deskeli', 'deskeli1', 'ticketdesk', 'ticketdesk1',
    'eliot123', 'pash1234', 'primatela1',
})


def validate_password(password: str, username: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Valida la contraseña contra la política.

    Devuelve (ok, error_message). Si ok=True, error_message=None.
    """
    if not password:
        return False, 'La contraseña no puede estar vacía.'

    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f'La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.'

    # Detectar mezcla mínima: al menos una letra Y al menos un dígito
    if not re.search(r'[A-Za-zÁÉÍÓÚáéíóúÑñ]', password):
        return False, 'La contraseña debe contener al menos una letra.'
    if not re.search(r'\d', password):
        return False, 'La contraseña debe contener al menos un dígito.'

    pwd_lower = password.lower().strip()

    if username and pwd_lower == username.lower().strip():
        return False, 'La contraseña no puede ser igual al nombre de usuario.'

    if pwd_lower in _COMMON_PASSWORDS:
        return False, 'Esta contraseña es demasiado común. Elegí otra menos predecible.'

    # Patrones extremadamente débiles
    if re.fullmatch(r'(.)\1+', password):
        return False, 'La contraseña no puede ser un único carácter repetido.'
    if password.lower() in {'abcdefgh', 'abcdefghi', 'abcdefghij'}:
        return False, 'Esta contraseña es demasiado predecible.'

    return True, None
