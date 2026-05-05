from werkzeug.security import generate_password_hash
from flask import session
import usuario


def guardar_usuario_service(id_usuario, username, password, rol, pin,
                             nombre=None, apellido=None, telefono=None,
                             correo=None, cp=None):
    admin = session.get("usuario")

    if not id_usuario:
        if not password:
            raise ValueError("Password obligatorio")
        if not pin:
            raise ValueError("PIN obligatorio")

        rol = rol or "caja"
        password_hash = generate_password_hash(password)
        pin_hash      = generate_password_hash(pin)

        nuevo_id = usuario.crear_usuario(
            username, password_hash, rol, pin_hash,
            nombre, apellido, telefono, correo, cp
        )

        usuario.registrar_historial_usuario(
            nuevo_id, "CREADO", None,
            {"usuario": username, "rol": rol, "nombre": nombre,
             "apellido": apellido, "telefono": telefono},
            admin
        )
        return

    antes = usuario.obtener_usuario_por_id(id_usuario)
    if not antes:
        raise ValueError(f"Usuario con id {id_usuario} no encontrado.")
    if antes["rol"] == "admin":
        return

    usuario.actualizar_usuario(
        id_usuario, username, rol,
        nombre, apellido, telefono, correo, cp
    )

    if password:
        usuario.actualizar_password(id_usuario, generate_password_hash(password))

    if pin:
        usuario.actualizar_pin(id_usuario, generate_password_hash(pin))

    despues = usuario.obtener_usuario_por_id(id_usuario)

    usuario.registrar_historial_usuario(
        id_usuario, "EDITADO", antes, despues, admin
    )


def toggle_usuario_service(id_usuario):
    admin = session.get("usuario")
    antes = usuario.obtener_usuario_por_id(id_usuario)
    if not antes:
        return None
    if antes["rol"] == "admin":
        return None
    usuario.toggle_activo(id_usuario)
    despues = usuario.obtener_usuario_por_id(id_usuario)
    usuario.registrar_historial_usuario(
        id_usuario, "TOGGLE_ACTIVO", antes, despues, admin
    )
    return despues["activo"]


def listar_usuarios_service(q=None, rol=None, activo=None):
    return usuario.obtener_usuarios(q=q, rol=rol, activo=activo)


def obtener_historial_usuario_service(id_usuario):
    return usuario.obtener_historial_usuario(id_usuario)