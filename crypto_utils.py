"""
Cifrado simétrico para secretos almacenados en BD (Fernet / AES-128-CBC + HMAC-SHA256).

Diseño:
- La clave se lee de la env var DB_ENCRYPTION_KEY (formato Fernet: base64 urlsafe de 32 bytes).
- Los valores cifrados se guardan en BD con el prefijo "enc:v1:" para distinguirlos
  de los valores legacy que aún están en texto plano.
- decrypt_secret() es idempotente: si el valor no tiene prefijo o no se puede
  descifrar (token corrupto, clave equivocada) devuelve el valor tal cual.
  Esto permite migración progresiva sin romper datos existentes.
- encrypt_secret() siempre devuelve "enc:v1:<token>".

Compatibilidad: si DB_ENCRYPTION_KEY no está definida, en producción aborta;
en desarrollo imprime un warning y usa modo pass-through (no cifra ni descifra).
"""

from __future__ import annotations

import os
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

_PREFIX = "enc:v1:"
_logger = logging.getLogger(__name__)

_fernet: Optional[Fernet] = None
_pass_through = False


def init_crypto(is_production: bool) -> None:
    """Inicializa el Fernet global. Llamar una vez al arrancar la app."""
    global _fernet, _pass_through

    key = os.getenv("DB_ENCRYPTION_KEY")
    if not key:
        if is_production:
            raise RuntimeError(
                "DB_ENCRYPTION_KEY no está definida en el entorno y FLASK_ENV=production. "
                "Generala con: python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\" y agregala al .env"
            )
        print("[WARN] DB_ENCRYPTION_KEY no definida — secretos en BD NO se cifrarán (modo dev pass-through).")
        _pass_through = True
        _fernet = None
        return

    try:
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        raise RuntimeError(
            f"DB_ENCRYPTION_KEY tiene formato inválido (debe ser Fernet base64): {e}"
        ) from e
    _pass_through = False


def generate_key() -> str:
    """Genera una nueva clave Fernet (útil para setup inicial)."""
    return Fernet.generate_key().decode()


def encrypt_secret(plain: Optional[str]) -> Optional[str]:
    """Cifra un secreto. Si plain es None o vacío, devuelve el valor tal cual.
    Si ya está cifrado (prefijo presente), no lo re-cifra."""
    if not plain:
        return plain
    if plain.startswith(_PREFIX):
        return plain  # ya cifrado
    if _pass_through or _fernet is None:
        return plain  # modo dev sin clave
    token = _fernet.encrypt(plain.encode("utf-8")).decode("ascii")
    return _PREFIX + token


def decrypt_secret(maybe_encrypted: Optional[str]) -> Optional[str]:
    """Descifra un secreto. Si no tiene prefijo, asume legacy plain text y lo devuelve tal cual.
    Si el token está corrupto o la clave no aplica, registra un warning y devuelve el valor tal cual
    (mejor degradar que romper toda la app)."""
    if not maybe_encrypted:
        return maybe_encrypted
    if not maybe_encrypted.startswith(_PREFIX):
        return maybe_encrypted  # legacy plain text
    if _pass_through or _fernet is None:
        # Hay datos cifrados pero perdimos la clave — no podemos descifrar.
        _logger.warning("Secreto cifrado encontrado pero DB_ENCRYPTION_KEY no está disponible.")
        return None
    token = maybe_encrypted[len(_PREFIX):]
    try:
        return _fernet.decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        _logger.error("Token Fernet inválido — la clave DB_ENCRYPTION_KEY puede haber cambiado.")
        return None


def is_encrypted(value: Optional[str]) -> bool:
    """True si el valor está marcado como cifrado (tiene prefijo)."""
    return bool(value) and value.startswith(_PREFIX)


def encrypt_bytes(plain: bytes) -> bytes:
    """Cifra bytes arbitrarios (uso: backups). Requiere DB_ENCRYPTION_KEY."""
    if _fernet is None:
        raise RuntimeError("Cifrado no disponible: DB_ENCRYPTION_KEY no inicializada.")
    return _fernet.encrypt(plain)


def decrypt_bytes(token: bytes) -> bytes:
    """Descifra bytes arbitrarios producidos por encrypt_bytes."""
    if _fernet is None:
        raise RuntimeError("Descifrado no disponible: DB_ENCRYPTION_KEY no inicializada.")
    return _fernet.decrypt(token)


def has_key() -> bool:
    """True si hay clave activa (no pass-through)."""
    return _fernet is not None
