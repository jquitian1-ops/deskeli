"""Rate limiting sliding-window en memoria.

Implementación única para dos casos de uso:
  - Rate limit por API key (endpoints externos de Tendency/otros proveedores).
  - Rate limit por IP para endpoints públicos (/api/companies).

Trade-offs conscientes:
  * En memoria del proceso: con múltiples workers cada uno tiene su propio
    contador. Como Gunicorn usa 1 worker eventlet, no es problema hoy.
    Si algún día se pasa a Redis, mover los dicts allí.
  * No persiste entre restarts. OK — un attacker que espera un restart no
    va a tener mejor puerta.

Configurable por env: API_KEY_RATE_LIMIT_PER_MIN (default 100).
"""
from __future__ import annotations

import collections
import os
import time


# ── Rate limit por API key (endpoints externos) ─────────────────────────
API_KEY_RATE_LIMIT_PER_MIN = int(os.getenv('API_KEY_RATE_LIMIT_PER_MIN', '100'))
API_KEY_RATE_LIMIT_WINDOW_SEC = 60
_api_key_buckets = collections.defaultdict(collections.deque)


def check_api_key_rate_limit(api_key_id) -> tuple:
    """Devuelve (allowed, retry_after_seconds).
    Aplica un rate limit sliding-window por api_key_id.

    api_key_id: identificador único de la key (típicamente el int id de la
    tabla api_keys).
    """
    now = time.time()
    cutoff = now - API_KEY_RATE_LIMIT_WINDOW_SEC
    bucket = _api_key_buckets[api_key_id]
    # Purgar timestamps fuera del window (más antiguos que cutoff).
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= API_KEY_RATE_LIMIT_PER_MIN:
        retry_after = int(bucket[0] + API_KEY_RATE_LIMIT_WINDOW_SEC - now) + 1
        return False, max(1, retry_after)
    bucket.append(now)
    return True, 0


# ── Rate limit por IP para endpoints públicos ──────────────────────────
PUBLIC_COMPANY_RATE_LIMIT_PER_MIN = 30
_public_company_buckets = collections.defaultdict(collections.deque)


def check_public_company_rate_limit(client_ip: str) -> tuple:
    """Rate limit sliding-window por IP para endpoints públicos (/api/companies
    y /api/company/<code>).
    Retorna (allowed, retry_after_seconds).
    """
    now = time.time()
    cutoff = now - 60
    bucket = _public_company_buckets[client_ip]
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= PUBLIC_COMPANY_RATE_LIMIT_PER_MIN:
        retry_after = int(bucket[0] + 60 - now) + 1
        return False, max(1, retry_after)
    bucket.append(now)
    return True, 0
