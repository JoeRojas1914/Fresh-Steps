from db import get_db
from utils import registrar_historial as _registrar_historial


def registrar_historial_venta(cursor, id_venta, accion, id_usuario, antes=None, despues=None):
    _registrar_historial(cursor, "venta_historial", "id_venta", id_venta, accion, id_usuario, antes, despues)


def obtener_historial_venta(id_venta):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT h.id_historial, h.accion, h.datos_antes,
                   h.datos_despues, h.fecha, u.usuario
            FROM venta_historial h
            JOIN usuario u ON u.id_usuario = h.id_usuario
            WHERE h.id_venta = %s
            ORDER BY h.fecha ASC
        """, (id_venta,))
        return cursor.fetchall()


def _aplicar_filtro_estado(sql, params, estado, mostrar_eliminadas):
    if estado == "pendiente":
        sql += " AND v.eliminado = 0 AND v.fecha_lista IS NULL AND v.fecha_entrega IS NULL"
    elif estado == "lista":
        sql += " AND v.eliminado = 0 AND v.fecha_lista IS NOT NULL AND v.fecha_entrega IS NULL"
    elif estado == "entregada":
        sql += " AND v.eliminado = 0 AND v.fecha_entrega IS NOT NULL"
    elif estado == "eliminada":
        sql += " AND v.eliminado = 1"
    elif not mostrar_eliminadas:
        sql += " AND v.eliminado = 0"
    return sql, params


def contar_historial_ventas(
    id_negocio=None,
    fecha_inicio=None,
    fecha_fin=None,
    mostrar_eliminadas=False,
    q=None,
    id_venta=None,
    estado=None,
):
    with get_db() as (_, cursor):
        sql = """
            SELECT COUNT(DISTINCT v.id_venta) AS total
            FROM venta v
            JOIN cliente c ON c.id_cliente = v.id_cliente
            WHERE 1=1
        """
        params = []
        sql, params = _aplicar_filtro_estado(sql, params, estado, mostrar_eliminadas)

        if id_negocio:
            sql += " AND v.id_negocio = %s"
            params.append(id_negocio)
        if fecha_inicio:
            sql += " AND DATE(v.fecha_recibo) >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            sql += " AND DATE(v.fecha_recibo) <= %s"
            params.append(fecha_fin)
        if q:
            sql += " AND (c.nombre LIKE %s OR c.apellido LIKE %s OR CONCAT(c.nombre,' ',c.apellido) LIKE %s)"
            like = f"%{q}%"
            params.extend([like, like, like])
        if id_venta:
            sql += " AND v.id_venta = %s"
            params.append(id_venta)

        cursor.execute(sql, params)
        return cursor.fetchone()["total"]


def obtener_historial_ventas(
    id_negocio=None,
    fecha_inicio=None,
    fecha_fin=None,
    limit=20,
    offset=0,
    mostrar_eliminadas=False,
    q=None,
    id_venta=None,
    estado=None,
):
    with get_db() as (_, cursor):
        sql = """
            SELECT
                v.id_venta,
                v.fecha_recibo,
                v.fecha_estimada,
                v.fecha_lista,
                v.fecha_entrega,
                v.eliminado,
                v.total,
                v.aplica_descuento,
                v.cantidad_descuento,
                c.nombre,
                c.apellido,
                c.telefono,
                n.nombre   AS negocio,
                n.id_negocio,
                u.usuario  AS usuario_creo,
                ue.usuario AS usuario_entrego,
                COALESCE(SUM(p.monto), 0) AS total_pagado
            FROM venta v
            JOIN cliente  c ON c.id_cliente  = v.id_cliente
            JOIN negocio  n ON n.id_negocio  = v.id_negocio
            LEFT JOIN usuario u  ON u.id_usuario  = v.id_usuario_creo
            LEFT JOIN usuario ue ON ue.id_usuario = v.id_usuario_entrego
            LEFT JOIN pago_venta p ON p.id_venta = v.id_venta
            WHERE 1=1
        """
        params = []
        sql, params = _aplicar_filtro_estado(sql, params, estado, mostrar_eliminadas)

        if id_negocio:
            sql += " AND v.id_negocio = %s"
            params.append(id_negocio)
        if fecha_inicio:
            sql += " AND DATE(v.fecha_recibo) >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            sql += " AND DATE(v.fecha_recibo) <= %s"
            params.append(fecha_fin)
        if q:
            sql += " AND (c.nombre LIKE %s OR c.apellido LIKE %s OR CONCAT(c.nombre,' ',c.apellido) LIKE %s)"
            like = f"%{q}%"
            params.extend([like, like, like])
        if id_venta:
            sql += " AND v.id_venta = %s"
            params.append(id_venta)

        sql += " GROUP BY v.id_venta ORDER BY v.id_venta DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        return cursor.fetchall()
