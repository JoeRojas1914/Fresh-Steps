import secrets
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from flask import request

from models.login import (
    obtener_usuario_por_username,
    obtener_usuarios_caja_activos,
    registrar_login_log,
    obtener_intentos,
    registrar_fallo,
    limpiar_intentos
)
from config import MAX_INTENTOS_PIN, BLOQUEO_MIN_PIN, BLOQUEO_REINCIDENTE_MIN_PIN, CLAVE_PIN_TERMINAL
from models.usuario import actualizar_session_token


_HASH_FALSO = generate_password_hash(secrets.token_hex(16))


def _ua() -> str | None:
    return request.headers.get("User-Agent")


def _bloqueado(username: str, ip: str) -> bool:
    intento = obtener_intentos(username, ip)
    return bool(intento and intento["bloqueado_hasta"] and datetime.now() < intento["bloqueado_hasta"])


def _esta_bloqueado(username: str, ip: str, metodo: str, id_usuario: int | None = None) -> bool:
    """True si está bloqueado; además deja constancia en login_log."""
    if not _bloqueado(username, ip):
        return False
    registrar_login_log(username, f"{metodo}_locked", False, ip,
                        id_usuario=id_usuario, user_agent=_ua())
    return True


def _fallo(username: str, metodo: str, ip: str) -> None:
    registrar_fallo(username, ip)

    registrar_login_log(
        username,
        metodo,
        False,
        ip,
        user_agent=_ua()
    )


def _exito(usuario: dict, metodo: str, ip: str) -> None:
    token = secrets.token_hex(32)
    actualizar_session_token(usuario["id_usuario"], token)
    usuario["_session_token"] = token

    limpiar_intentos(usuario["usuario"], ip)

    registrar_login_log(
        usuario["usuario"],
        metodo,
        True,
        ip,
        id_usuario=usuario["id_usuario"],
        user_agent=_ua()
    )


def login_password_service(username: str, password: str, ip: str) -> dict | str | None:

    if _esta_bloqueado(username, ip, "password_admin"):
        return "LOCKED"

    usuario = obtener_usuario_por_username(username)

    # Siempre se compara contra un hash (uno falso si el usuario no existe) para
    # que el tiempo de respuesta no revele qué usuarios existen.
    hash_bd = (usuario or {}).get("password_hash") or _HASH_FALSO
    valido  = check_password_hash(hash_bd, password or "")
    if not usuario or not usuario.get("password_hash") or not valido:
        _fallo(username, "password_admin", ip)
        return None

    _exito(usuario, "password_admin", ip)
    if usuario.get("rol") == "admin":
        # Un admin en la terminal la desbloquea si quedó bloqueada por PIN incorrectos
        limpiar_intentos(CLAVE_PIN_TERMINAL, ip)
    return usuario


def login_pin_service(pin: str, ip: str) -> dict | str | None:
    """Acceso de caja por PIN.

    Los fallos se cuentan por terminal (IP), una vez por intento: antes cada PIN
    incorrecto sumaba un fallo a CADA cajero y unos pocos errores bloqueaban a todos.
    Regresa el usuario, None (PIN incorrecto), "LOCKED" o "DUPLICADO"
    (el PIN coincide con más de un usuario: nunca se entra con uno al azar)."""
    if not pin:
        return None

    if _esta_bloqueado(CLAVE_PIN_TERMINAL, ip, "pin_caja"):
        return "LOCKED"

    coincidencias = [
        u for u in obtener_usuarios_caja_activos()
        if u.get("pin_hash") and check_password_hash(u["pin_hash"], pin)
    ]

    if len(coincidencias) == 1:
        usuario = coincidencias[0]
        _exito(usuario, "pin_caja", ip)
        limpiar_intentos(CLAVE_PIN_TERMINAL, ip)
        return usuario

    if len(coincidencias) > 1:
        registrar_login_log(None, "pin_caja_duplicado", False, ip, user_agent=_ua())
        return "DUPLICADO"

    registrar_fallo(CLAVE_PIN_TERMINAL, ip, max_intentos=MAX_INTENTOS_PIN, bloqueo_min=BLOQUEO_MIN_PIN,
                    bloqueo_reincidente_min=BLOQUEO_REINCIDENTE_MIN_PIN)
    registrar_login_log(None, "pin_caja", False, ip, user_agent=_ua())
    return "LOCKED" if _bloqueado(CLAVE_PIN_TERMINAL, ip) else None


def registrar_logout_service(id_usuario: int, username: str, ip: str) -> None:
    registrar_login_log(username, "logout", True, ip, id_usuario=id_usuario)


def invalidar_session_token_service(id_usuario: int) -> None:
    actualizar_session_token(id_usuario, None)
