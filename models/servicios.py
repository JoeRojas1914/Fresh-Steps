from db import get_db
from utils import build_where, cond_in, construir_order_by, registrar_historial as _registrar_historial


def existe_servicio_activo(id_negocio, nombre, excluir_id=None):
    with get_db() as (_, cursor):
        sql = "SELECT id_servicio FROM servicio WHERE id_negocio=%s AND nombre=%s AND activo=1"
        params = [id_negocio, nombre]
        if excluir_id:
            sql += " AND id_servicio != %s"
            params.append(excluir_id)
        cursor.execute(sql, params)
        return cursor.fetchone() is not None


def crear_servicio(id_negocio, nombre, precio, id_usuario):
    with get_db() as (_, cursor):
        cursor.execute("""
            INSERT INTO servicio (id_negocio, nombre, precio)
            VALUES (%s, %s, %s)
        """, (id_negocio, nombre, precio))

        id_servicio = cursor.lastrowid
        despues = {"nombre": nombre, "precio": precio}
        registrar_historial(cursor, id_servicio, "CREADO", id_usuario, None, despues)


def actualizar_servicio(id_servicio, id_negocio, nombre, precio, id_usuario):
    with get_db() as (_, cursor):
        cursor.execute("SELECT * FROM servicio WHERE id_servicio=%s", (id_servicio,))
        antes = cursor.fetchone()

        cursor.execute("""
            UPDATE servicio
            SET id_negocio=%s, nombre=%s, precio=%s
            WHERE id_servicio=%s
        """, (id_negocio, nombre, precio, id_servicio))

        if antes and int(antes["id_negocio"]) != int(id_negocio):
            _quitar_default(cursor, id_servicio)

        despues = {"nombre": nombre, "precio": precio}
        registrar_historial(cursor, id_servicio, "EDITADO", id_usuario, antes, despues)


def eliminar_servicio(id_servicio, id_usuario):
    with get_db() as (_, cursor):
        cursor.execute("SELECT * FROM servicio WHERE id_servicio=%s", (id_servicio,))
        antes = cursor.fetchone()

        cursor.execute("""
            UPDATE servicio
            SET activo = 0
            WHERE id_servicio=%s
        """, (id_servicio,))
        _quitar_default(cursor, id_servicio)

        registrar_historial(cursor, id_servicio, "ELIMINADO", id_usuario, antes, None)
        return True


# ── Servicio predeterminado por negocio (negocio.id_servicio_default) ──

def _quitar_default(cursor, id_servicio):
    cursor.execute(
        "UPDATE negocio SET id_servicio_default = NULL WHERE id_servicio_default = %s",
        (id_servicio,),
    )


def alternar_servicio_default(id_servicio, id_usuario):
    """Marca el servicio como predeterminado de su negocio, o lo quita si ya lo era.

    Regresa True si quedó como predeterminado, False si se quitó y None si el
    servicio no existe o está eliminado."""
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT s.id_negocio, n.id_servicio_default
            FROM servicio s
            JOIN negocio n ON n.id_negocio = s.id_negocio
            WHERE s.id_servicio = %s AND s.activo = 1
        """, (id_servicio,))
        row = cursor.fetchone()
        if not row:
            return None

        era_default = row["id_servicio_default"] == id_servicio
        cursor.execute(
            "UPDATE negocio SET id_servicio_default = %s WHERE id_negocio = %s",
            (None if era_default else id_servicio, row["id_negocio"]),
        )
        # El que era predeterminado antes en ese negocio también queda en el historial
        anterior = row["id_servicio_default"]
        if anterior and not era_default:
            registrar_historial(cursor, anterior, "EDITADO", id_usuario,
                                {"predeterminado": "Sí"}, {"predeterminado": "No"})
        registrar_historial(cursor, id_servicio, "EDITADO", id_usuario,
                            {"predeterminado": "Sí" if era_default else "No"},
                            {"predeterminado": "No" if era_default else "Sí"})
        return not era_default


def contar_servicios(id_negocio=None, q=None, incluir_eliminados=False):
    where, params = build_where([
        cond_in("id_negocio", id_negocio),
        ("nombre LIKE %s", f"%{q}%" if q else None),
        ("activo = %s", None if incluir_eliminados else 1),
    ])
    with get_db() as (_, cursor):
        cursor.execute("SELECT COUNT(*) AS total FROM servicio " + where, params)
        return cursor.fetchone()["total"]


COLUMNAS_ORDEN_SERVICIOS = {
    "negocio": "n.nombre",
    "nombre":  "s.nombre",
    "precio":  "s.precio",
    "activo":  "s.activo",
}


def obtener_servicios(id_negocio=None, q=None, incluir_eliminados=False, limit=10, offset=0,
                      orden=None, direccion=None):
    where, params = build_where([
        cond_in("s.id_negocio", id_negocio),
        ("s.nombre LIKE %s", f"%{q}%" if q else None),
        ("s.activo = %s", None if incluir_eliminados else 1),
    ])
    params.extend([limit, offset])
    with get_db() as (_, cursor):
        sql = (
            "SELECT s.id_servicio, s.nombre, s.precio, s.id_negocio, s.activo, n.nombre AS negocio,"
            " (n.id_servicio_default <=> s.id_servicio) AS es_default,"
            " sd.nombre AS default_actual"   # predeterminado actual del negocio (para confirmar el cambio)
            " FROM servicio s"
            " JOIN negocio n ON n.id_negocio = s.id_negocio"
            " LEFT JOIN servicio sd ON sd.id_servicio = n.id_servicio_default "
            + where
            + construir_order_by(orden, direccion, "s.nombre ASC",
                                 COLUMNAS_ORDEN_SERVICIOS, "s.id_servicio")
            + " LIMIT %s OFFSET %s"
        )

        cursor.execute(sql, params)
        return cursor.fetchall()


def registrar_historial(cursor, id_servicio, accion, id_usuario, antes=None, despues=None):
    _registrar_historial(cursor, "servicios_historial", "id_servicio", id_servicio, accion, id_usuario, antes, despues)


def obtener_historial_servicio(id_servicio):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT h.*, u.usuario AS usuario
            FROM servicios_historial h
            JOIN usuario u ON u.id_usuario = h.id_usuario
            WHERE id_servicio=%s
            ORDER BY fecha DESC
        """, (id_servicio,))
        return cursor.fetchall()


def restaurar_servicio(id_servicio, id_usuario):
    with get_db() as (_, cursor):
        cursor.execute("SELECT * FROM servicio WHERE id_servicio=%s", (id_servicio,))
        antes = cursor.fetchone()

        cursor.execute("""
            UPDATE servicio
            SET activo = 1
            WHERE id_servicio=%s
        """, (id_servicio,))

        registrar_historial(cursor, id_servicio, "RESTAURADO", id_usuario, antes, None)
