from db import get_db
from config import TIPO_PAGO_FINAL
from utils import build_where, construir_order_by


def registrar_pago(id_venta, monto, tipo_pago, id_usuario_cobro):
    with get_db() as (_, cursor):
        cursor.execute("""
            INSERT INTO pago_venta (
                id_venta,
                fecha_pago,
                monto,
                tipo_pago,
                id_usuario_cobro
            )
            VALUES (%s, NOW(), %s, %s, %s)
        """, (id_venta, monto, tipo_pago, id_usuario_cobro))


def obtener_pagos_venta(ids_venta):
    if not ids_venta:
        return {}

    with get_db() as (_, cursor):
        placeholders = ','.join(['%s'] * len(ids_venta))
        sql = (
            "SELECT id_venta, monto, tipo_pago, tipo_pago_venta"
            " FROM pago_venta"
            " WHERE id_venta IN (" + placeholders + ")"
        )
        cursor.execute(sql, tuple(ids_venta))

        pagos_por_venta = {}
        for p in cursor.fetchall():
            pagos_por_venta.setdefault(p["id_venta"], []).append(p)

        return pagos_por_venta


def obtener_pagos_por_venta(id_venta):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT tipo_pago_venta, tipo_pago, monto, fecha_pago
            FROM pago_venta
            WHERE id_venta=%s
            ORDER BY fecha_pago
        """, (id_venta,))
        return cursor.fetchall()


def registrar_pago_final_db(id_venta, monto, metodo_pago, id_usuario):
    with get_db() as (_, cursor):
        cursor.execute("""
            INSERT INTO pago_venta (
                id_venta,
                monto,
                tipo_pago,
                tipo_pago_venta,
                fecha_pago,
                id_usuario_cobro
            )
            VALUES (%s, %s, %s, %s, NOW(), %s)
        """, (id_venta, monto, metodo_pago, TIPO_PAGO_FINAL, id_usuario))


def _filtros_historial(id_negocio, tipo_pago, tipo_pago_venta, fecha_inicio, fecha_fin):
    return build_where([
        ("v.eliminado = %s",          0),
        ("v.id_negocio = %s",         id_negocio),
        ("pv.tipo_pago = %s",         tipo_pago),
        ("pv.tipo_pago_venta = %s",   tipo_pago_venta),
        ("DATE(pv.fecha_pago) >= %s", fecha_inicio),
        ("DATE(pv.fecha_pago) <= %s", fecha_fin),
    ])


COLUMNAS_ORDEN_PAGOS = {
    "negocio":         "n.nombre",
    "recibo":          "pv.id_venta",
    "cliente":         "CONCAT(c.nombre, ' ', c.apellido)",
    "fecha_pago":      "pv.fecha_pago",
    "tipo_pago_venta": "pv.tipo_pago_venta",
    "tipo_pago":       "pv.tipo_pago",
    "monto":           "pv.monto",
    "cobrado_por":     "u.usuario",
}


def obtener_historial_pagos(id_negocio, tipo_pago, tipo_pago_venta,
                             fecha_inicio, fecha_fin, limit, offset,
                             orden=None, direccion=None):
    where, params = _filtros_historial(
        id_negocio, tipo_pago, tipo_pago_venta, fecha_inicio, fecha_fin
    )
    params.extend([limit, offset])
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT
                pv.id_venta, pv.fecha_pago,
                pv.monto, pv.tipo_pago, pv.tipo_pago_venta,
                c.nombre   AS cliente_nombre,
                c.apellido AS cliente_apellido,
                c.id_cliente,
                n.nombre   AS negocio,
                u.usuario  AS cobrado_por
            FROM pago_venta pv
            JOIN venta   v ON v.id_venta    = pv.id_venta
            JOIN cliente c ON c.id_cliente  = v.id_cliente
            JOIN negocio n ON n.id_negocio  = v.id_negocio
            LEFT JOIN usuario u ON u.id_usuario = pv.id_usuario_cobro
            """ + where
            + construir_order_by(orden, direccion, "pv.fecha_pago DESC",
                                 COLUMNAS_ORDEN_PAGOS, "pv.id_pago")
            + " LIMIT %s OFFSET %s", params)
        return cursor.fetchall()


def contar_historial_pagos(id_negocio, tipo_pago, tipo_pago_venta,
                            fecha_inicio, fecha_fin):
    where, params = _filtros_historial(
        id_negocio, tipo_pago, tipo_pago_venta, fecha_inicio, fecha_fin
    )
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM pago_venta pv
            JOIN venta   v ON v.id_venta   = pv.id_venta
            JOIN cliente c ON c.id_cliente = v.id_cliente
            JOIN negocio n ON n.id_negocio = v.id_negocio
            """ + where, params)
        return int(cursor.fetchone()["total"] or 0)
