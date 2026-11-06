import json
from db import get_db
from utils import calcular_paginacion, construir_order_by

COLUMNAS_ORDEN_USUARIOS = {
    "usuario":   "usuario",
    "nombre":    "CONCAT(COALESCE(nombre, ''), ' ', COALESCE(apellido, ''))",
    "telefono":  "telefono",
    "correo":    "correo",
    "rol":       "rol",
    "activo":    "activo",
    "creado_en": "creado_en",
}


def obtener_usuarios(q=None, rol=None, activo=None, pagina=1, por_pagina=20,
                     orden=None, direccion=None):
    with get_db() as (_, cursor):
        where = "FROM usuario WHERE 1=1"
        params = []

        if q:
            where += " AND (usuario LIKE %s OR nombre LIKE %s OR apellido LIKE %s OR telefono LIKE %s OR CONCAT(nombre, ' ', apellido) LIKE %s)"
            like = f"%{q}%"
            params += [like, like, like, like, like]

        if rol:
            where += " AND rol = %s"
            params.append(rol)

        if activo is not None:
            where += " AND activo = %s"
            params.append(activo)

        cursor.execute(f"SELECT COUNT(*) AS cnt {where}", params)
        total = cursor.fetchone()["cnt"]
        offset, total_paginas = calcular_paginacion(total, pagina, por_pagina)
        cursor.execute(
            f"""SELECT id_usuario, usuario, nombre, apellido,
                       telefono, correo, cp, rol, activo, creado_en
                {where}
                {construir_order_by(orden, direccion,
                                    "CASE WHEN rol = 'admin' THEN 0 ELSE 1 END, creado_en DESC",
                                    COLUMNAS_ORDEN_USUARIOS, "id_usuario")}
                LIMIT %s OFFSET %s""",
            params + [por_pagina, offset],
        )
        return {"usuarios": cursor.fetchall(), "total": total, "total_paginas": total_paginas}


def obtener_usuario_por_id(id_usuario):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT * FROM usuario
            WHERE id_usuario = %s
        """, (id_usuario,))
        return cursor.fetchone()


def toggle_activo(id_usuario):
    """Activa/desactiva al usuario. Al desactivarlo se invalida su sesión abierta.

    MySQL evalúa las asignaciones de izquierda a derecha: en el IF, `activo`
    ya tiene el valor nuevo."""
    with get_db() as (_, cursor):
        cursor.execute("""
            UPDATE usuario
            SET activo = NOT activo,
                session_token = IF(activo = 0, NULL, session_token)
            WHERE id_usuario=%s
        """, (id_usuario,))


def _reemplazar_negocios(cursor, id_usuario, ids_negocio):
    cursor.execute("DELETE FROM usuario_negocio WHERE id_usuario=%s", (id_usuario,))
    for id_negocio in ids_negocio:
        cursor.execute("""
            INSERT INTO usuario_negocio (id_usuario, id_negocio) VALUES (%s, %s)
        """, (id_usuario, id_negocio))


def crear_usuario_completo(usuario_nombre, password_hash, rol, pin_hash, ids_negocio,
                           nombre=None, apellido=None, telefono=None, correo=None, cp=None):
    """Crea el usuario y sus negocios en UNA transacción. Regresa el id."""
    with get_db() as (_, cursor):
        cursor.execute("""
            INSERT INTO usuario
                (usuario, password_hash, rol, pin_hash,
                 nombre, apellido, telefono, correo, cp)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (usuario_nombre, password_hash, rol, pin_hash,
              nombre, apellido, telefono, correo, cp))
        nuevo_id = cursor.lastrowid
        if ids_negocio:
            _reemplazar_negocios(cursor, nuevo_id, ids_negocio)
        return nuevo_id


def actualizar_usuario_completo(id_usuario, usuario_nombre, rol,
                                nombre=None, apellido=None, telefono=None,
                                correo=None, cp=None,
                                password_hash=None, pin_hash=None, ids_negocio=None):
    """Actualiza datos, password/PIN (si vienen) y negocios (si no es None) en UNA transacción."""
    with get_db() as (_, cursor):
        cursor.execute("""
            UPDATE usuario
            SET usuario=%s, rol=%s,
                nombre=%s, apellido=%s,
                telefono=%s, correo=%s, cp=%s
            WHERE id_usuario=%s
        """, (usuario_nombre, rol, nombre, apellido, telefono, correo, cp, id_usuario))
        if password_hash:
            cursor.execute("UPDATE usuario SET password_hash=%s WHERE id_usuario=%s",
                           (password_hash, id_usuario))
        if pin_hash:
            cursor.execute("UPDATE usuario SET pin_hash=%s WHERE id_usuario=%s",
                           (pin_hash, id_usuario))
        if ids_negocio is not None:
            _reemplazar_negocios(cursor, id_usuario, ids_negocio)


def registrar_historial_usuario(id_usuario, accion, antes, despues, admin):
    with get_db() as (_, cursor):
        cursor.execute("""
            INSERT INTO historial_usuario
            (id_usuario, accion, datos_antes, datos_despues, usuario_admin)
            VALUES (%s,%s,%s,%s,%s)
        """, (
            id_usuario, accion,
            json.dumps(antes, default=str) if antes else None,
            json.dumps(despues, default=str) if despues else None,
            admin,
        ))


def obtener_pines_caja(excluir_id=None):
    """PIN (hash) de TODOS los usuarios de caja, activos e inactivos.

    Incluye inactivos para que al reactivar un usuario su PIN no choque con otro."""
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT pin_hash FROM usuario
            WHERE rol = 'caja' AND pin_hash IS NOT NULL
              AND id_usuario != %s
        """, (excluir_id or 0,))
        return cursor.fetchall()


def actualizar_session_token(id_usuario, token):
    with get_db() as (_, cursor):
        cursor.execute("""
            UPDATE usuario SET session_token=%s WHERE id_usuario=%s
        """, (token, id_usuario))


def obtener_session_token(id_usuario):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT session_token FROM usuario WHERE id_usuario=%s
        """, (id_usuario,))
        row = cursor.fetchone()
        return row["session_token"] if row else None


def obtener_negocios_usuario(id_usuario):
    """IDs de los negocios asignados a un usuario (tabla usuario_negocio)."""
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT id_negocio FROM usuario_negocio
            WHERE id_usuario=%s
            ORDER BY id_negocio
        """, (id_usuario,))
        return [r["id_negocio"] for r in cursor.fetchall()]


def obtener_negocios_usuarios(ids_usuario):
    """{id_usuario: [id_negocio, ...]} para varios usuarios en una sola consulta."""
    if not ids_usuario:
        return {}
    with get_db() as (_, cursor):
        ph = ",".join(["%s"] * len(ids_usuario))
        cursor.execute(f"""
            SELECT id_usuario, id_negocio FROM usuario_negocio
            WHERE id_usuario IN ({ph})
            ORDER BY id_negocio
        """, tuple(ids_usuario))
        resultado = {}
        for r in cursor.fetchall():
            resultado.setdefault(r["id_usuario"], []).append(r["id_negocio"])
        return resultado


def obtener_historial_usuario(id_usuario):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT * FROM historial_usuario
            WHERE id_usuario=%s
            ORDER BY fecha DESC
        """, (id_usuario,))
        return cursor.fetchall()
