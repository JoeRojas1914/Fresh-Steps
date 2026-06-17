from db import get_db
from utils import build_where, registrar_historial as _registrar_historial


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


def contar_clientes(q=None, incluir_eliminados=False):
    q_like = f"%{q}%" if q else None
    where, params = build_where([
        ("activo = %s", None if incluir_eliminados else 1),
        ("(nombre LIKE %s OR apellido LIKE %s)", q_like, q_like),
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
              AND (c.nombre LIKE %s OR c.apellido LIKE %s)
            GROUP BY c.id_cliente
            ORDER BY c.nombre ASC
            LIMIT 50
        """, (f"%{q}%", f"%{q}%"))
        return cursor.fetchall()


def obtener_cliente_por_id(id_cliente):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT *,
                   DATE_FORMAT(fecha_registro, '%d/%m/%Y') as fecha_registro_fmt
            FROM cliente
            WHERE id_cliente = %s
        """, (id_cliente,))
        return cursor.fetchone()


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


def obtener_clientes(q=None, limit=10, offset=0, incluir_eliminados=False):
    q_like = f"%{q}%" if q else None
    where, params = build_where([
        ("activo = %s", None if incluir_eliminados else 1),
        ("(nombre LIKE %s OR apellido LIKE %s)", q_like, q_like),
    ])
    params.extend([limit, offset])
    with get_db() as (_, cursor):
        cursor.execute(f"""
            SELECT id_cliente, nombre, apellido, telefono, correo, direccion, activo
            FROM cliente
            {where}
            ORDER BY nombre ASC, apellido ASC LIMIT %s OFFSET %s
        """, params)
        return cursor.fetchall()


def contar_pedidos_por_cliente(ids_cliente: list) -> dict:
    if not ids_cliente:
        return {}
    placeholders = ",".join(["%s"] * len(ids_cliente))
    with get_db() as (_, cursor):
        cursor.execute(f"""
            SELECT id_cliente, COUNT(*) AS total
            FROM venta
            WHERE id_cliente IN ({placeholders})
              AND eliminado = 0
            GROUP BY id_cliente
        """, ids_cliente)
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
