import json as _json
from decimal import Decimal
from datetime import date, datetime
from db import get_connection


def registrar_historial_venta(cursor, id_venta, accion, id_usuario, antes=None, despues=None):
    def safe(d):
        if not d:
            return None
        out = {}
        for k, v in d.items():
            if isinstance(v, Decimal):
                out[k] = float(v)
            elif isinstance(v, (date, datetime)):
                out[k] = v.isoformat()
            else:
                out[k] = v
        return out

    cursor.execute("""
        INSERT INTO venta_historial
            (id_venta, accion, id_usuario, datos_antes, datos_despues)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        id_venta, accion, id_usuario,
        _json.dumps(safe(antes)) if antes else None,
        _json.dumps(safe(despues)) if despues else None,
    ))


def obtener_historial_venta(id_venta):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT h.id_historial, h.accion, h.datos_antes,
                   h.datos_despues, h.fecha, u.usuario
            FROM venta_historial h
            JOIN usuario u ON u.id_usuario = h.id_usuario
            WHERE h.id_venta = %s
            ORDER BY h.fecha ASC
        """, (id_venta,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def contar_historial_ventas(id_negocio=None, fecha_inicio=None, fecha_fin=None, mostrar_eliminadas=False, q=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT COUNT(DISTINCT v.id_venta)
            FROM venta v
            JOIN cliente c ON c.id_cliente = v.id_cliente
            WHERE (1=1)
        """ + ("" if mostrar_eliminadas else " AND v.eliminado = 0")
        params = []
        if id_negocio:
            query += " AND v.id_negocio = %s"
            params.append(id_negocio)
        if fecha_inicio:
            query += " AND DATE(v.fecha_recibo) >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            query += " AND DATE(v.fecha_recibo) <= %s"
            params.append(fecha_fin)
        if q:
            query += " AND (c.nombre LIKE %s OR c.apellido LIKE %s OR CONCAT(c.nombre,' ',c.apellido) LIKE %s)"
            like = f"%{q}%"
            params.extend([like, like, like])
        cursor.execute(query, params)
        return cursor.fetchone()[0]
    finally:
        cursor.close()
        conn.close()


def obtener_historial_ventas(id_negocio=None, fecha_inicio=None, fecha_fin=None,
                             limit=20, offset=0, mostrar_eliminadas=False, q=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
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

    if not mostrar_eliminadas:
        query += " AND v.eliminado = 0"

    params = []

    if id_negocio:
        query += " AND v.id_negocio = %s"
        params.append(id_negocio)
    if fecha_inicio:
        query += " AND DATE(v.fecha_recibo) >= %s"
        params.append(fecha_inicio)
    if fecha_fin:
        query += " AND DATE(v.fecha_recibo) <= %s"
        params.append(fecha_fin)
    if q:
        query += " AND (c.nombre LIKE %s OR c.apellido LIKE %s OR CONCAT(c.nombre,' ',c.apellido) LIKE %s)"
        like = f"%{q}%"
        params.extend([like, like, like])

    query += " GROUP BY v.id_venta ORDER BY v.id_venta DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
