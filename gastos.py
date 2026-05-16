from db import get_db
from utils import build_where, registrar_historial as _registrar_historial


def crear_gasto(
    id_negocio,
    descripcion,
    proveedor,
    total,
    fecha_registro,
    tipo_comprobante,
    tipo_pago,
    id_usuario,
):
    with get_db() as (_, cursor):
        cursor.execute("""
            INSERT INTO gastos
            (id_negocio, descripcion, proveedor, total, fecha_registro,
             tipo_comprobante, tipo_pago, id_usuario)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id_negocio, descripcion, proveedor, total,
            fecha_registro, tipo_comprobante, tipo_pago, id_usuario,
        ))

        id_gasto = cursor.lastrowid

        despues = {
            "descripcion": descripcion,
            "proveedor": proveedor,
            "total": total,
            "tipo_comprobante": tipo_comprobante,
            "tipo_pago": tipo_pago,
        }

        registrar_historial(cursor, id_gasto, "CREADO", id_usuario, None, despues)


def actualizar_gasto(
    id_gasto,
    id_negocio,
    descripcion,
    proveedor,
    total,
    fecha_registro,
    tipo_comprobante,
    tipo_pago,
    id_usuario,
):
    with get_db() as (_, cursor):
        cursor.execute("SELECT * FROM gastos WHERE id_gasto=%s", (id_gasto,))
        antes = cursor.fetchone()

        cursor.execute("""
            UPDATE gastos
            SET id_negocio=%s,
                descripcion=%s,
                proveedor=%s,
                total=%s,
                fecha_registro=%s,
                tipo_comprobante=%s,
                tipo_pago=%s
            WHERE id_gasto=%s
        """, (
            id_negocio, descripcion, proveedor, total,
            fecha_registro, tipo_comprobante, tipo_pago, id_gasto,
        ))

        despues = {
            "descripcion": descripcion,
            "proveedor": proveedor,
            "total": total,
            "tipo_comprobante": tipo_comprobante,
            "tipo_pago": tipo_pago,
        }

        registrar_historial(cursor, id_gasto, "EDITADO", id_usuario, antes, despues)


def eliminar_gasto(id_gasto, id_usuario):
    with get_db() as (_, cursor):
        cursor.execute("SELECT * FROM gastos WHERE id_gasto=%s", (id_gasto,))
        antes = cursor.fetchone()

        cursor.execute("""
            UPDATE gastos
            SET activo = 0
            WHERE id_gasto=%s
        """, (id_gasto,))

        registrar_historial(cursor, id_gasto, "ELIMINADO", id_usuario, antes, None)


def obtener_gastos(
    id_negocio=None,
    fecha_inicio=None,
    fecha_fin=None,
    limit=10,
    offset=0,
    incluir_eliminados=False,
):
    where, params = build_where([
        ("g.id_negocio = %s", id_negocio),
        ("g.fecha_registro >= %s", fecha_inicio),
        ("g.fecha_registro <= %s", fecha_fin),
        ("g.activo = %s", None if incluir_eliminados else 1),
    ])
    params.extend([limit, offset])
    with get_db() as (_, cursor):
        cursor.execute(f"""
            SELECT
                g.id_gasto, g.id_negocio, n.nombre AS negocio,
                g.descripcion, g.proveedor, g.total, g.fecha_registro,
                g.tipo_comprobante, g.tipo_pago, u.usuario AS creado_por, g.activo
            FROM gastos g
            JOIN negocio n ON g.id_negocio = n.id_negocio
            JOIN usuario u ON g.id_usuario = u.id_usuario
            {where}
            ORDER BY g.fecha_registro DESC LIMIT %s OFFSET %s
        """, params)
        return cursor.fetchall()


def obtener_gastos_por_proveedor(id_negocio, fecha_inicio, fecha_fin):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT proveedor, SUM(total) AS total
            FROM gastos
            WHERE id_negocio = %s
              AND fecha_registro BETWEEN %s AND %s
            GROUP BY proveedor
            ORDER BY total DESC
        """, (id_negocio, fecha_inicio, fecha_fin))
        return cursor.fetchall()


def contar_gastos(
    id_negocio=None,
    fecha_inicio=None,
    fecha_fin=None,
    incluir_eliminados=False,
):
    where, params = build_where([
        ("activo = %s", None if incluir_eliminados else 1),
        ("id_negocio = %s", id_negocio),
        ("fecha_registro >= %s", fecha_inicio),
        ("fecha_registro <= %s", fecha_fin),
    ])
    with get_db() as (_, cursor):
        cursor.execute(f"SELECT COUNT(*) AS total FROM gastos {where}", params)
        return cursor.fetchone()["total"]


def registrar_historial(cursor, id_gasto, accion, id_usuario, antes=None, despues=None):
    _registrar_historial(cursor, "gastos_historial", "id_gasto", id_gasto, accion, id_usuario, antes, despues)


def obtener_historial_gasto(id_gasto):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT h.*, u.usuario AS usuario
            FROM gastos_historial h
            JOIN usuario u ON h.id_usuario = u.id_usuario
            WHERE id_gasto=%s
            ORDER BY fecha DESC
        """, (id_gasto,))
        return cursor.fetchall()


def restaurar_gasto(id_gasto, id_usuario):
    with get_db() as (_, cursor):
        cursor.execute("SELECT * FROM gastos WHERE id_gasto=%s", (id_gasto,))
        antes = cursor.fetchone()

        cursor.execute("""
            UPDATE gastos
            SET activo = 1
            WHERE id_gasto=%s
        """, (id_gasto,))

        registrar_historial(cursor, id_gasto, "RESTAURADO", id_usuario, antes, None)
