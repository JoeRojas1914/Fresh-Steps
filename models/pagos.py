from db import get_db


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
            VALUES (%s, %s, %s, 'final', NOW(), %s)
        """, (id_venta, monto, metodo_pago, id_usuario))
