import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
import models.usuario as usuario
from models.negocio import obtener_negocios
from validators import validar_correo, validar_telefono, validar_pin, validar_password


def _verificar_pin_unico(pin: str, excluir_id: int | None = None) -> None:
    for row in usuario.obtener_pines_caja(excluir_id=excluir_id):
        if check_password_hash(row["pin_hash"], pin):
            raise ValueError("Este PIN ya está en uso por otro usuario.")


def _validar_negocios(negocios) -> list[int]:
    """Valida la lista de negocios asignados a un usuario de caja."""
    validos = {n["id_negocio"] for n in obtener_negocios()}
    try:
        ids = sorted({int(n) for n in (negocios or [])})
    except (TypeError, ValueError):
        raise ValueError("Negocios inválidos.")
    if not ids:
        raise ValueError("Selecciona al menos un negocio para el usuario de caja.")
    if any(n not in validos for n in ids):
        raise ValueError("Negocio inválido.")
    return ids


ROLES_VALIDOS = {"admin", "caja"}

# Columnas que nunca deben quedar en el historial ni salir por la API
_CAMPOS_SECRETOS = ("password_hash", "pin_hash", "session_token")


def _snapshot_usuario(fila: dict | None) -> dict | None:
    """Copia de la fila del usuario sin hashes ni token de sesión."""
    if not fila:
        return fila
    return {k: v for k, v in fila.items() if k not in _CAMPOS_SECRETOS}


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
    negocios: list[int] | None = None,
) -> None:
    """Crea o edita un usuario.

    `negocios`: negocios que el usuario de caja puede ver. Obligatorio al crear;
    al editar, None significa "no cambiar los negocios asignados".
    Todo se valida antes de escribir y se guarda en una sola transacción."""
    admin = session.get("usuario")

    if not username or not username.strip():
        raise ValueError("El usuario es obligatorio")
    username = username.strip()

    telefono = validar_telefono(telefono)
    correo   = validar_correo(correo)

    if not id_usuario:
        rol = rol or "caja"
        if rol not in ROLES_VALIDOS:
            raise ValueError("Rol inválido.")

        validar_password(password, obligatorio=True)
        pin = validar_pin(pin)
        if not pin:
            raise ValueError("PIN obligatorio")
        _verificar_pin_unico(pin)

        ids_negocio = _validar_negocios(negocios) if rol == "caja" else []

        nuevo_id = usuario.crear_usuario_completo(
            username, generate_password_hash(password), rol, generate_password_hash(pin),
            ids_negocio, nombre, apellido, telefono, correo, cp,
        )

        usuario.registrar_historial_usuario(
            nuevo_id, "CREADO", None,
            {"usuario": username, "rol": rol, "nombre": nombre,
             "apellido": apellido, "telefono": telefono,
             "negocios": ids_negocio},
            admin
        )
        return

    antes = usuario.obtener_usuario_por_id(id_usuario)
    if not antes:
        raise ValueError(f"Usuario con id {id_usuario} no encontrado.")
    if antes["rol"] == "admin":
        raise ValueError("Los administradores no se pueden editar desde esta pantalla.")

    rol = rol or antes["rol"]
    if rol not in ROLES_VALIDOS:
        raise ValueError("Rol inválido.")

    # Validar todo ANTES de escribir para no dejar ediciones a medias
    password      = validar_password(password)
    pin           = validar_pin(pin)
    if pin:
        _verificar_pin_unico(pin, excluir_id=id_usuario)
    ids_negocio   = _validar_negocios(negocios) if negocios is not None else None

    antes = _snapshot_usuario(antes)
    antes["negocios"] = usuario.obtener_negocios_usuario(id_usuario)

    usuario.actualizar_usuario_completo(
        id_usuario, username, rol,
        nombre, apellido, telefono, correo, cp,
        password_hash=generate_password_hash(password) if password else None,
        pin_hash=generate_password_hash(pin) if pin else None,
        ids_negocio=ids_negocio,
    )

    despues = _snapshot_usuario(usuario.obtener_usuario_por_id(id_usuario))
    despues["negocios"] = usuario.obtener_negocios_usuario(id_usuario)
    if password:
        despues["password_cambiado"] = True
    if pin:
        despues["pin_cambiado"] = True

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
        id_usuario, "TOGGLE_ACTIVO", _snapshot_usuario(antes), _snapshot_usuario(despues), admin
    )
    return despues["activo"]


def listar_usuarios_service(
    q: str | None = None,
    rol: str | None = None,
    activo: int | None = None,
    pagina: int = 1,
    orden: str | None = None,
    direccion: str | None = None,
) -> dict:
    data = usuario.obtener_usuarios(q=q, rol=rol, activo=activo, pagina=pagina,
                                    orden=orden, direccion=direccion)
    negocios_map = usuario.obtener_negocios_usuarios([u["id_usuario"] for u in data["usuarios"]])
    for u in data["usuarios"]:
        u["negocios"] = negocios_map.get(u["id_usuario"], [])
    data["negocios"] = obtener_negocios()
    return data


def _limpiar_json_historial(texto):
    """Quita los campos secretos de un JSON de historial (registros antiguos los incluían)."""
    if not texto:
        return texto
    if isinstance(texto, dict):
        return json.dumps(_snapshot_usuario(texto), default=str)
    try:
        datos = json.loads(texto)
    except (TypeError, ValueError):
        return texto
    if isinstance(datos, dict):
        datos = _snapshot_usuario(datos)
    return json.dumps(datos, default=str)


def obtener_historial_usuario_service(id_usuario: int) -> list[dict]:
    filas = usuario.obtener_historial_usuario(id_usuario)
    for f in filas:
        f["datos_antes"]   = _limpiar_json_historial(f.get("datos_antes"))
        f["datos_despues"] = _limpiar_json_historial(f.get("datos_despues"))
    return filas


def obtener_mi_perfil_service(id_usuario: int) -> dict | None:
    """Datos del usuario en sesión para "Mi perfil" (sin hashes ni token)."""
    return _snapshot_usuario(usuario.obtener_usuario_por_id(id_usuario))
