"""Hash de passwords — Argon2id con retrocompat PBKDF2.

Historia: originalmente los passwords se hasheaban con PBKDF2-SHA256 usando
el username como salt (100 000 iteraciones). Esto es funcional pero tiene 2
problemas serios:
  1. Salt determinístico → dos usuarios con mismo username+password en
     distintas empresas producen hashes idénticos. Vulnerable a ataques de
     diccionario pre-computado si la BD se filtra.
  2. PBKDF2 es memory-hard limitado — inferior a Argon2id ante GPUs y ASICs.

Solución: migración transparente a Argon2id.
  - `hash_password()` siempre produce Argon2id (formato $argon2id$v=19$...).
  - `verify_password()` acepta AMBOS formatos:
      * Argon2id ($argon2id$...) → verifica con argon2-cffi.
      * PBKDF2 legacy (hex de 64 chars) → verifica con hashlib + username.
    Retorna (is_valid, needs_rehash). Si needs_rehash, el caller debe
    re-hashear y persistir. Los usuarios se migran solos al loguearse.

Parámetros Argon2id (OWASP 2024 baseline):
    time_cost=2, memory_cost=19 MiB, parallelism=1. Verificación ~50-100ms.
"""
from __future__ import annotations

import hashlib
import hmac as _hmac


try:
    from argon2 import PasswordHasher as _Argon2PasswordHasher
    from argon2.exceptions import (
        VerifyMismatchError as _Argon2VerifyMismatchError,
        InvalidHash as _Argon2InvalidHash,
        VerificationError as _Argon2VerificationError,
    )
    _argon2_hasher = _Argon2PasswordHasher(
        time_cost=2,
        memory_cost=19456,   # KiB
        parallelism=1,
        hash_len=32,
        salt_len=16,
    )
    ARGON2_AVAILABLE = True
except ImportError:
    _argon2_hasher = None
    ARGON2_AVAILABLE = False
    print('[WARN] argon2-cffi no está instalado. Los passwords seguirán usando PBKDF2 legacy. '
          'Instalá con `pip install argon2-cffi==23.1.0` para migrar a Argon2id.')


def _hash_password_pbkdf2_legacy(password: str, username: str) -> str:
    """Hash PBKDF2-SHA256 con username como salt (100 000 iters).

    LEGACY: solo para verificar hashes ya en BD. Nunca usar para nuevos hashes.
    """
    return hashlib.pbkdf2_hmac(
        'sha256',
        (password or '').encode(),
        (username or '').encode(),
        100000
    ).hex()


def hash_password(password: str, username: str = '') -> str:
    """Genera un hash de password. Preferentemente Argon2id; si la lib no está
    disponible, cae a PBKDF2 legacy (retrocompat).

    El `username` solo se usa como salt en el modo legacy. En Argon2id el salt
    es aleatorio (interno al hash).
    """
    if ARGON2_AVAILABLE:
        return _argon2_hasher.hash(password or '')
    return _hash_password_pbkdf2_legacy(password, username)


def verify_password(password: str, stored_hash: str, username: str = '') -> tuple:
    """Verifica un password contra el hash almacenado.

    Retorna (is_valid, needs_rehash):
        - is_valid: True si el password coincide con el hash.
        - needs_rehash: True cuando el hash usa formato legacy o parámetros
          Argon2 obsoletos. El caller debe re-hashear + persistir.

    Formatos aceptados:
        - $argon2id$... (Argon2, moderno)
        - hex de 64 chars (PBKDF2-SHA256 legacy)
    """
    if not stored_hash or password is None:
        return False, False

    # ── Argon2 (moderno) ──
    if stored_hash.startswith('$argon2'):
        if not ARGON2_AVAILABLE:
            return False, False
        try:
            _argon2_hasher.verify(stored_hash, password)
            needs = _argon2_hasher.check_needs_rehash(stored_hash)
            return True, needs
        except (_Argon2VerifyMismatchError, _Argon2VerificationError, _Argon2InvalidHash):
            return False, False

    # ── PBKDF2 legacy (hex 64) ──
    if len(stored_hash) == 64 and all(c in '0123456789abcdefABCDEF' for c in stored_hash):
        if not username:
            return False, False
        calc = _hash_password_pbkdf2_legacy(password, username)
        # Comparación en tiempo constante para evitar timing attacks.
        try:
            if _hmac.compare_digest(calc, stored_hash.lower()):
                return True, True   # rehash SIEMPRE en el próximo login
        except Exception:
            if calc == stored_hash.lower():
                return True, True

    return False, False
