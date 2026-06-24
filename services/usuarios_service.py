from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
import models.usuario as usuario
from validators import validar_correo, validar_telefono, validar_pin, validar_password


def _verificar_pin_unico(pin: str, excluir_id: int | None = None) -> None:
    for row in usuario.obtener_pines_caja_activos(excluir_id=excluir_id):
        if check_password_hash(row["pin_hash"], pin):
            raise ValueError("Este PIN ya está en uso por otro usuario.")


def guardar_usuario_service(
    id_usuario: int | None,
    username: str,
    password: str | None,
    rol: str | None,
    pin: str | None,
    nombre: str | None = None,
    apellido: str | None = None,
    telefono: str | None = None,
    correo: str | None = None,
    cp: str | None = None,
) -> None:
    admin = session.get("usuario")

    telefono = validar_telefono(telefono)
    correo   = validar_correo(correo)

    if not id_usuario:
        validar_password(password, obligatorio=True)
        if not pin:
            raise ValueError("PIN obligatorio")
        validar_pin(pin)
        _verificar_pin_unico(pin)

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
        validar_password(password)
        usuario.actualizar_password(id_usuario, generate_password_hash(password))

    if pin:
        validar_pin(pin)
        _verificar_pin_unico(pin, excluir_id=id_usuario)
        usuario.actualizar_pin(id_usuario, generate_password_hash(pin))

    despues = usuario.obtener_usuario_por_id(id_usuario)

    usuario.registrar_historial_usuario(
        id_usuario, "EDITADO", antes, despues, admin
    )


def toggle_usuario_service(id_usuario: int) -> int | None:
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


def listar_usuarios_service(
    q: str | None = None,
    rol: str | None = None,
    activo: int | None = None,
    pagina: int = 1,
) -> dict:
    return usuario.obtener_usuarios(q=q, rol=rol, activo=activo, pagina=pagina)


def obtener_historial_usuario_service(id_usuario: int) -> list[dict]:
    return usuario.obtener_historial_usuario(id_usuario)
