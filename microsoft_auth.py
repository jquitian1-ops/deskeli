"""
Autenticación con Microsoft Entra ID (Azure AD) usando OAuth 2.0 + OIDC.

Flujo:
1. Usuario hace click en "Iniciar con Microsoft" en /login → /auth/microsoft/login
2. Nuestra app redirige a Microsoft con state + scopes
3. Usuario autentica en Microsoft (SSO, MFA, etc.)
4. Microsoft redirige de vuelta a /auth/microsoft/callback con code + state
5. Intercambiamos code por access_token + id_token
6. Con id_token obtenemos: email, nombre, oid (object_id), tenant
7. Buscamos user por microsoft_object_id → si no existe, buscamos por email → si no, creamos
8. Creamos sesión de Flask y redirigimos según role

Requiere msal >= 1.24.0
"""
from __future__ import annotations

import logging
import secrets
from typing import Optional, Tuple, Dict

try:
    import msal
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False

_logger = logging.getLogger(__name__)

# Scopes que pedimos a Microsoft Graph
DEFAULT_SCOPES = ['User.Read']  # openid/profile/email se incluyen automáticamente

# Endpoints Microsoft OAuth
AUTHORITY_TEMPLATE = 'https://login.microsoftonline.com/{tenant_id}'


def _build_msal_app(tenant_id: str, client_id: str, client_secret: str):
    """Construye una instancia ConfidentialClientApplication de MSAL."""
    if not MSAL_AVAILABLE:
        raise RuntimeError("msal no está instalado. Ejecutá 'pip install msal'.")
    if not tenant_id or not client_id:
        raise ValueError("tenant_id y client_id son obligatorios")

    return msal.ConfidentialClientApplication(
        client_id=client_id,
        authority=AUTHORITY_TEMPLATE.format(tenant_id=tenant_id),
        client_credential=client_secret,
    )


def build_auth_url(tenant_id: str, client_id: str, client_secret: str,
                   redirect_uri: str, state: Optional[str] = None) -> Tuple[str, str]:
    """Construye la URL para redirigir al usuario a Microsoft.
    Devuelve (auth_url, state_generado)."""
    app = _build_msal_app(tenant_id, client_id, client_secret)
    state = state or secrets.token_urlsafe(24)
    auth_url = app.get_authorization_request_url(
        scopes=DEFAULT_SCOPES,
        state=state,
        redirect_uri=redirect_uri,
    )
    return auth_url, state


def exchange_code_for_token(tenant_id: str, client_id: str, client_secret: str,
                            code: str, redirect_uri: str) -> Dict:
    """Cambia el código de autorización por access_token + id_token.
    Devuelve el dict de token o {'error': '...'} en caso de fallo."""
    app = _build_msal_app(tenant_id, client_id, client_secret)
    result = app.acquire_token_by_authorization_code(
        code=code,
        scopes=DEFAULT_SCOPES,
        redirect_uri=redirect_uri,
    )
    return result


def get_user_info(access_token: str) -> Optional[Dict]:
    """Llama a Microsoft Graph /me para obtener info del usuario autenticado.
    Devuelve dict con 'id' (object_id), 'displayName', 'mail', 'userPrincipalName',
    'givenName', 'surname', o None si falla."""
    import requests
    try:
        r = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
        _logger.warning("Microsoft Graph /me devolvió %s: %s", r.status_code, r.text[:200])
    except Exception as e:
        _logger.warning("Error consultando Microsoft Graph: %s", e)
    return None


def extract_user_data_from_token(token_result: Dict) -> Optional[Dict]:
    """Extrae información del usuario desde id_token_claims (más rápido que llamar Graph)."""
    claims = token_result.get('id_token_claims') or {}
    if not claims:
        return None
    return {
        'id': claims.get('oid') or claims.get('sub'),  # OID es único global; sub es único en el app
        'displayName': claims.get('name') or '',
        'mail': claims.get('email') or claims.get('preferred_username') or '',
        'userPrincipalName': claims.get('preferred_username') or claims.get('upn') or '',
        'givenName': claims.get('given_name') or '',
        'surname': claims.get('family_name') or '',
        'tenant_id': claims.get('tid') or '',
    }
