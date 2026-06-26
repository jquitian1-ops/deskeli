"""
Autenticación LDAP/Active Directory para DeskEli.

Estrategia simple y robusta:
- Cada empresa puede tener su propia configuración LDAP (modelo Company).
- En login: si la empresa tiene `ldap_server` configurado, se intenta bind LDAP
  con (username, password). Si tiene éxito → usuario autenticado.
- Si LDAP no responde (red, server caído): se cae a hash local automáticamente.
- Si LDAP responde pero credenciales son incorrectas: se rechaza (NO cae a local
  para evitar bypass).

Soporta:
- LDAP plano (puerto 389)
- LDAPS (puerto 636 con SSL)
- StartTLS (puerto 389 + upgrade a TLS)

Modos de auth contra AD:
- `simple`: bind con DN o UPN completo
- `negotiate` (placeholder; en realidad usa simple con UPN — Kerberos requiere
  configuración adicional del SO)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

try:
    from ldap3 import Server, Connection, ALL, NTLM, SIMPLE, SUBTREE, Tls
    from ldap3.core.exceptions import (
        LDAPException, LDAPBindError, LDAPSocketOpenError,
        LDAPInvalidCredentialsResult,
    )
    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False

import ssl

_logger = logging.getLogger(__name__)


@dataclass
class LdapConfig:
    """Configuración de un proveedor LDAP."""
    server: str               # host o IP (ej. "192.168.20.20" o "ad.empresa.local")
    port: int = 389           # 389 (plain/StartTLS) o 636 (LDAPS)
    use_ssl: bool = False     # True para LDAPS (puerto 636)
    use_start_tls: bool = False  # True para StartTLS sobre puerto 389
    base_dn: str = ""         # ej. "DC=empresa,DC=local"
    bind_user: str = ""       # service account (UPN o DN)
    bind_password: str = ""   # contraseña del service account (descifrada)
    auth_mode: str = "simple"  # 'simple' o 'ntlm'

    @classmethod
    def from_company(cls, company, decrypt_func) -> Optional["LdapConfig"]:
        """Construye LdapConfig desde el modelo Company. Devuelve None si no está configurado."""
        if not company or not (company.ldap_server or "").strip():
            return None
        # Detectar puerto y SSL del esquema ldap:// vs ldaps://
        server = company.ldap_server.strip()
        port = 389
        use_ssl = False
        if server.lower().startswith("ldaps://"):
            server = server[len("ldaps://"):].rstrip("/")
            port = 636
            use_ssl = True
        elif server.lower().startswith("ldap://"):
            server = server[len("ldap://"):].rstrip("/")
        # Si el host trae ":puerto" explícito, parsearlo
        if ":" in server:
            host, port_str = server.rsplit(":", 1)
            try:
                port = int(port_str)
                server = host
            except ValueError:
                pass

        return cls(
            server=server,
            port=port,
            use_ssl=use_ssl,
            use_start_tls=False,  # no se infiere del esquema; flag aparte si querés soportarlo
            base_dn=(company.ldap_base_dn or "").strip(),
            bind_user=(company.ldap_bind_user or "").strip(),
            bind_password=decrypt_func(company.ldap_bind_password) or "",
        )


def _build_connection(cfg: LdapConfig, user: str, password: str) -> Connection:
    """Crea una conexión LDAP usando la config dada."""
    tls = None
    if cfg.use_ssl or cfg.use_start_tls:
        tls = Tls(validate=ssl.CERT_NONE)  # En prod podrías validar CA específica
    server_obj = Server(cfg.server, port=cfg.port, use_ssl=cfg.use_ssl, tls=tls, get_info=ALL)
    authentication = NTLM if cfg.auth_mode == "ntlm" else SIMPLE
    conn = Connection(
        server_obj,
        user=user,
        password=password,
        authentication=authentication,
        auto_bind=False,
        receive_timeout=10,
    )
    if cfg.use_start_tls:
        conn.start_tls()
    return conn


def test_ldap_connection(cfg: LdapConfig) -> Tuple[bool, str]:
    """Prueba que se puede hacer bind con las credenciales del service account.
    Devuelve (ok, mensaje)."""
    if not LDAP_AVAILABLE:
        return False, "Librería ldap3 no instalada en el servidor."
    if not cfg.bind_user or not cfg.bind_password:
        return False, "Faltan credenciales del service account (bind user/password)."
    try:
        conn = _build_connection(cfg, cfg.bind_user, cfg.bind_password)
        bound = conn.bind()
        if not bound:
            return False, f"Bind falló: {conn.last_error or 'credenciales rechazadas'}"
        # Si tiene base_dn, intentamos un search rápido para validar acceso
        if cfg.base_dn:
            ok_search = conn.search(cfg.base_dn, "(objectClass=*)", search_scope=SUBTREE, attributes=[], size_limit=1)
            if not ok_search:
                conn.unbind()
                return False, f"Bind OK pero no se puede buscar en {cfg.base_dn}: {conn.last_error}"
        conn.unbind()
        return True, f"Conexión exitosa a {cfg.server}:{cfg.port}"
    except LDAPSocketOpenError as e:
        return False, f"No se puede conectar a {cfg.server}:{cfg.port} — {e}"
    except LDAPBindError as e:
        return False, f"Credenciales rechazadas por el servidor: {e}"
    except LDAPException as e:
        return False, f"Error LDAP: {e}"
    except Exception as e:
        return False, f"Error inesperado: {type(e).__name__}: {e}"


def authenticate_user(cfg: LdapConfig, username: str, password: str) -> Tuple[Optional[str], Optional[str], str]:
    """Autentica un usuario contra LDAP.

    Devuelve (status, full_name, message):
    - status='ok': autenticado correctamente. full_name puede tener el displayName.
    - status='bad_credentials': bind LDAP rechazó (NO hacer fallback a local).
    - status='unreachable': servidor no responde (PUEDE hacer fallback a local).
    - status='not_configured': la empresa no tiene LDAP (debe usar local).
    """
    if not LDAP_AVAILABLE:
        return "unreachable", None, "ldap3 no instalada"
    if not cfg.bind_user or not cfg.bind_password:
        return "not_configured", None, "LDAP sin service account configurado"
    if not password:
        return "bad_credentials", None, "Contraseña vacía"

    # 1) Bind con el service account para BUSCAR al usuario por username/email
    try:
        admin_conn = _build_connection(cfg, cfg.bind_user, cfg.bind_password)
        if not admin_conn.bind():
            return "unreachable", None, f"Bind con service account falló: {admin_conn.last_error}"
    except LDAPSocketOpenError as e:
        return "unreachable", None, f"Servidor no responde: {e}"
    except LDAPException as e:
        return "unreachable", None, f"Error LDAP: {e}"

    # 2) Buscar usuario por sAMAccountName o userPrincipalName o mail
    user_dn = None
    full_name = None
    if cfg.base_dn:
        ldap_filter = (
            f"(&(objectClass=user)"
            f"(|(sAMAccountName={username})(userPrincipalName={username})(mail={username})))"
        )
        try:
            admin_conn.search(
                cfg.base_dn, ldap_filter, search_scope=SUBTREE,
                attributes=["cn", "displayName", "distinguishedName"],
                size_limit=1,
            )
            if admin_conn.entries:
                entry = admin_conn.entries[0]
                user_dn = str(entry.distinguishedName) if "distinguishedName" in entry else None
                full_name = str(entry.displayName or entry.cn or "")
        except LDAPException as e:
            _logger.warning("LDAP search error: %s", e)

    admin_conn.unbind()

    # 3) Si no se encontró DN, intentar bind directo como UPN (username@domain) en algunos AD
    bind_id = user_dn or username

    # 4) Intentar bind como el usuario
    try:
        user_conn = _build_connection(cfg, bind_id, password)
        if user_conn.bind():
            user_conn.unbind()
            return "ok", full_name, "Autenticado por LDAP"
        else:
            return "bad_credentials", None, f"Credenciales incorrectas: {user_conn.last_error}"
    except LDAPInvalidCredentialsResult:
        return "bad_credentials", None, "Credenciales incorrectas"
    except LDAPSocketOpenError as e:
        return "unreachable", None, f"Servidor no responde durante bind: {e}"
    except LDAPException as e:
        return "unreachable", None, f"Error LDAP en bind: {e}"
