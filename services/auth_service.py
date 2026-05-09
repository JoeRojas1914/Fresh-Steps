from datetime import datetime
from werkzeug.security import check_password_hash
from flask import request

from login import (
    obtener_usuario_por_username,
    obtener_usuario_caja_activo,
    obtener_usuarios_caja_activos,
    registrar_login_log,
    obtener_intentos,
    registrar_fallo,
    limpiar_intentos
)



def _ua():
    return request.headers.get("User-Agent")


def _esta_bloqueado(username, ip, metodo, id_usuario=None):
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


def _fallo(username, metodo, ip):
    registrar_fallo(username, ip)

    registrar_login_log(
        username,
        metodo,
        False,
        ip,
        user_agent=_ua()
    )


def _exito(usuario, metodo, ip):
    limpiar_intentos(usuario["usuario"], ip)

    registrar_login_log(
        usuario["usuario"],
        metodo,
        True,
        ip,
        id_usuario=usuario["id_usuario"],
        user_agent=_ua()
    )


def login_password_service(username, password, ip):

    if _esta_bloqueado(username, ip, "password_admin"):
        return "LOCKED"

    usuario = obtener_usuario_por_username(username)

    if not usuario or not check_password_hash(usuario["password_hash"], password):
        _fallo(username, "password_admin", ip)
        return None

    _exito(usuario, "password_admin", ip)
    return usuario


def login_pin_service(pin, ip):

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

        _fallo(username, "pin_caja", ip)

    # Verificar si todos están bloqueados
    for usuario in usuarios:
        if _esta_bloqueado(usuario["usuario"], ip, "pin_caja", usuario["id_usuario"]):
            return "LOCKED"

    return None