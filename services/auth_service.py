import secrets
from datetime import datetime
from werkzeug.security import check_password_hash
from flask import request

from models.login import (
    obtener_usuario_por_username,
    obtener_usuarios_caja_activos,
    registrar_login_log,
    obtener_intentos,
    registrar_fallo,
    limpiar_intentos
)
from config import MAX_INTENTOS_PIN, BLOQUEO_MIN_PIN
from models.usuario import actualizar_session_token


def _ua() -> str | None:
    return request.headers.get("User-Agent")


def _esta_bloqueado(username: str, ip: str, metodo: str, id_usuario: int | None = None) -> bool:
    intento = obtener_intentos(username, ip)

    if intento and intento["bloqueado_hasta"]:
        if datetime.now() < intento["bloqueado_hasta"]:

            registrar_login_log(
                username,
                f"{metodo}_locked",
                False,
                ip,
                id_usuario=id_usuario,
                user_agent=_ua()
            )
            return True

    return False


def _fallo(username: str, metodo: str, ip: str, max_intentos: int | None = None, bloqueo_min: int | None = None) -> None:
    kwargs = {}
    if max_intentos is not None:
        kwargs["max_intentos"] = max_intentos
    if bloqueo_min is not None:
        kwargs["bloqueo_min"] = bloqueo_min
    registrar_fallo(username, ip, **kwargs)

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

    if not usuario or not check_password_hash(usuario["password_hash"], password):
        _fallo(username, "password_admin", ip)
        return None

    _exito(usuario, "password_admin", ip)
    return usuario


def login_pin_service(pin: str, ip: str) -> dict | str | None:

    usuarios = obtener_usuarios_caja_activos()

    if not usuarios:
        return None

    for usuario in usuarios:
        username = usuario["usuario"]

        if _esta_bloqueado(username, ip, "pin_caja", usuario["id_usuario"]):
            continue

        if check_password_hash(usuario["pin_hash"], pin):
            _exito(usuario, "pin_caja", ip)
            return usuario

        _fallo(username, "pin_caja", ip, max_intentos=MAX_INTENTOS_PIN, bloqueo_min=BLOQUEO_MIN_PIN)

    for usuario in usuarios:
        if _esta_bloqueado(usuario["usuario"], ip, "pin_caja", usuario["id_usuario"]):
            return "LOCKED"

    return None


def invalidar_session_token_service(id_usuario: int) -> None:
    actualizar_session_token(id_usuario, None)
