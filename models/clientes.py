import re

from db import get_db
from utils import build_where, construir_order_by, registrar_historial as _registrar_historial
from models.ventas_detalles import como_lista


def _cond_busqueda(q):
    """Filtro para build_where: nombre, apellido o teléfono.

    El teléfono se compara sin espacios, guiones, paréntesis ni '+'."""
    q = (q or "").strip()
    if not q:
        return ("", None)
    like = f"%{q}%"
    sql = "nombre LIKE %s OR apellido LIKE %s OR CONCAT(nombre, ' ', apellido) LIKE %s"
    valores = [like, like, like]
    digitos = re.sub(r"[\s\-\(\)\+]", "", q)
    if digitos.isdigit():
        sql += " OR telefono LIKE %s"
        valores.append(f"%{digitos}%")
    return (f"({sql})", *valores)


def _cond_negocios(id_negocio):
    """Filtro para build_where: clientes con al menos una venta activa en esos negocios.

    None / lista vacía = sin filtro (admin)."""
    ids = como_lista(id_negocio)
    if not ids:
        return ("", None)
    ph = ", ".join(["%s"] * len(ids))
    return (
        "EXISTS (SELECT 1 FROM venta vn WHERE vn.id_cliente = cliente.id_cliente"
        f" AND vn.eliminado = 0 AND vn.id_negocio IN ({ph}))",
        *ids,
    )


def crear_cliente(nombre, apellido, correo, telefono, direccion, id_usuario):
    with get_db() as (_, cursor):
        cursor.execute("""
            INSERT INTO cliente
            (nombre, apellido, correo, telefono, direccion, activo, id_usuario)
            VALUES (%s,%s,%s,%s,%s,1,%s)
        """, (nombre, apellido, correo, telefono, direccion, id_usuario))

        id_cliente = cursor.lastrowid

        despues = {
            "nombre": nombre,
            "apellido": apellido,
            "correo": correo,
            "telefono": telefono,
            "direccion": direccion,
        }

        registrar_historial(cursor, id_cliente, "CREADO", id_usuario, None, despues)
        return id_cliente


def eliminar_cliente(id_cliente, id_usuario):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM venta
            WHERE id_cliente=%s
              AND eliminado = 0
        """, (id_cliente,))

        if cursor.fetchone()["total"] > 0:
            return False

        cursor.execute("SELECT * FROM cliente WHERE id_cliente=%s", (id_cliente,))
        antes = cursor.fetchone()

        cursor.execute("""
            UPDATE cliente
            SET activo = 0
            WHERE id_cliente=%s
        """, (id_cliente,))

        registrar_historial(cursor, id_cliente, "ELIMINADO", id_usuario, antes, None)
        return True


def actualizar_cliente(id_cliente, nombre, apellido, correo, telefono, direccion, id_usuario):
    with get_db() as (_, cursor):
        cursor.execute("SELECT * FROM cliente WHERE id_cliente=%s", (id_cliente,))
        antes = cursor.fetchone()

        cursor.execute("""
            UPDATE cliente
            SET nombre=%s,
                apellido=%s,
                correo=%s,
                telefono=%s,
                direccion=%s
            WHERE id_cliente=%s
        """, (nombre, apellido, correo, telefono, direccion, id_cliente))

        despues = {
            "nombre": nombre,
            "apellido": apellido,
            "correo": correo,
            "telefono": telefono,
            "direccion": direccion,
        }

        registrar_historial(cursor, id_cliente, "EDITADO", id_usuario, antes, despues)


def contar_clientes(q=None, incluir_eliminados=False, id_negocio=None):
    where, params = build_where([
        ("activo = %s", None if incluir_eliminados else 1),
        _cond_busqueda(q),
        _cond_negocios(id_negocio),
    ])
    with get_db() as (_, cursor):
        cursor.execute("SELECT COUNT(*) AS total FROM cliente " + where, params)
        return cursor.fetchone()["total"]


def buscar_clientes_por_nombre(texto):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT *
            FROM cliente
            WHERE activo = 1
              AND (nombre LIKE %s OR apellido LIKE %s)
            LIMIT 50
        """, (f"%{texto}%", f"%{texto}%"))
        return cursor.fetchall()


def buscar_clientes(q):
    q_like = f"%{q}%"
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT
                c.id_cliente,
                c.nombre,
                c.apellido,
                c.telefono,
                COUNT(v.id_venta) AS total_ventas
            FROM cliente c
            LEFT JOIN venta v ON v.id_cliente = c.id_cliente AND v.eliminado = 0
            WHERE c.activo = 1
              AND (
                    c.nombre LIKE %s
                 OR c.apellido LIKE %s
                 OR CONCAT(c.nombre, ' ', c.apellido) LIKE %s
                 OR c.telefono LIKE %s
              )
            GROUP BY c.id_cliente
            ORDER BY c.nombre ASC
            LIMIT 50
        """, (q_like, q_like, q_like, q_like))
        return cursor.fetchall()


def obtener_cliente_por_telefono(telefono, excluir_id=None):
    with get_db() as (_, cursor):
        if excluir_id:
            cursor.execute("""
                SELECT id_cliente, nombre, apellido
                FROM cliente
                WHERE telefono = %s AND activo = 1 AND id_cliente != %s
                LIMIT 1
            """, (telefono, excluir_id))
        else:
            cursor.execute("""
                SELECT id_cliente, nombre, apellido
                FROM cliente
                WHERE telefono = %s AND activo = 1
                LIMIT 1
            """, (telefono,))
        return cursor.fetchone()


def obtener_cliente_por_id(id_cliente):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT *,
                   DATE_FORMAT(fecha_registro, '%d/%m/%Y') as fecha_registro_fmt
            FROM cliente
            WHERE id_cliente = %s
        """, (id_cliente,))
        return cursor.fetchone()


def cliente_visible(id_cliente, id_negocio):
    """True si el cliente está activo y tiene alguna venta activa en esos negocios."""
    where, params = build_where([
        ("id_cliente = %s", id_cliente),
        ("activo = %s", 1),
        _cond_negocios(id_negocio),
    ])
    with get_db() as (_, cursor):
        cursor.execute("SELECT 1 AS ok FROM cliente " + where, params)
        return cursor.fetchone() is not None


def registrar_historial(cursor, id_cliente, accion, id_usuario, antes=None, despues=None):
    _registrar_historial(cursor, "clientes_historial", "id_cliente", id_cliente, accion, id_usuario, antes, despues)


def restaurar_cliente(id_cliente, id_usuario):
    with get_db() as (_, cursor):
        cursor.execute("SELECT * FROM cliente WHERE id_cliente=%s", (id_cliente,))
        antes = cursor.fetchone()

        cursor.execute("""
            UPDATE cliente
            SET activo = 1
            WHERE id_cliente=%s
        """, (id_cliente,))

        registrar_historial(cursor, id_cliente, "RESTAURADO", id_usuario, antes, None)


COLUMNAS_ORDEN_CLIENTES = {
    "nombre":         "CONCAT(nombre, ' ', apellido)",
    "telefono":       "telefono",
    "direccion":      "direccion",
    "pedidos":        "(SELECT COUNT(*) FROM venta vp"
                      " WHERE vp.id_cliente = cliente.id_cliente AND vp.eliminado = 0)",
    "activo":         "activo",
    "fecha_registro": "fecha_registro",
}


def obtener_clientes(q=None, limit=10, offset=0, incluir_eliminados=False,
                     orden=None, direccion=None, id_negocio=None):
    where, params = build_where([
        ("activo = %s", None if incluir_eliminados else 1),
        _cond_busqueda(q),
        _cond_negocios(id_negocio),
    ])
    params.extend([limit, offset])
    with get_db() as (_, cursor):
        cursor.execute(f"""
            SELECT id_cliente, nombre, apellido, telefono, correo, direccion, activo,
                   fecha_registro
            FROM cliente
            {where}
            {construir_order_by(orden, direccion, "nombre ASC, apellido ASC",
                                COLUMNAS_ORDEN_CLIENTES, "id_cliente")}
            LIMIT %s OFFSET %s
        """, params)
        return cursor.fetchall()


def contar_pedidos_por_cliente(ids_cliente: list, id_negocio=None) -> dict:
    if not ids_cliente:
        return {}
    placeholders = ",".join(["%s"] * len(ids_cliente))
    negocios = como_lista(id_negocio)
    sql_neg  = f" AND id_negocio IN ({', '.join(['%s'] * len(negocios))})" if negocios else ""
    with get_db() as (_, cursor):
        cursor.execute(f"""
            SELECT id_cliente, COUNT(*) AS total
            FROM venta
            WHERE id_cliente IN ({placeholders})
              AND eliminado = 0
              {sql_neg}
            GROUP BY id_cliente
        """, list(ids_cliente) + list(negocios))
        return {r["id_cliente"]: int(r["total"]) for r in cursor.fetchall()}


def obtener_historial_cliente(id_cliente):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT
                h.*,
                u.usuario AS usuario
            FROM clientes_historial h
            JOIN usuario u ON u.id_usuario = h.id_usuario
            WHERE h.id_cliente = %s
            ORDER BY h.fecha DESC
        """, (id_cliente,))
        return cursor.fetchall()
