from db import get_connection

def registrar_pago(id_venta, monto, tipo_pago, id_usuario_cobro):
    conn = get_connection()
    cursor = conn.cursor()

    try:
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


        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cursor.close()
        conn.close()


def obtener_pagos_venta(ids_venta):
    if not ids_venta:
        return {}

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        format_strings = ','.join(['%s'] * len(ids_venta))

        cursor.execute(f"""
            SELECT id_venta, monto, tipo_pago, tipo_pago_venta
            FROM pago_venta
            WHERE id_venta IN ({format_strings})
        """, ids_venta)

        pagos = cursor.fetchall()

        pagos_por_venta = {}
        for p in pagos:
            pagos_por_venta.setdefault(p["id_venta"], []).append(p)


        return pagos_por_venta
    finally:
        cursor.close()
        conn.close()


def obtener_pagos_por_venta(id_venta):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        cursor.execute("""
            SELECT tipo_pago_venta, tipo_pago, monto, fecha_pago
            FROM pago_venta
            WHERE id_venta=%s
            ORDER BY fecha_pago
        """, (id_venta,))

        data = cursor.fetchall()

        return data
    finally:
        cursor.close()
        conn.close()


def registrar_pago_final_db(id_venta, monto, metodo_pago, id_usuario):
    conn = get_connection()
    cursor = conn.cursor()

    try:
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
        """, (
            id_venta,
            monto,
            metodo_pago,
            id_usuario
        ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()