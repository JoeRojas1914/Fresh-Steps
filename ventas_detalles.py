from db import get_connection


def obtener_venta(id_venta):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                v.id_venta,
                v.id_negocio,
                v.fecha_recibo,
                v.fecha_estimada,
                v.total,
                v.aplica_descuento,
                v.cantidad_descuento,

                CONCAT(c.nombre, ' ', c.apellido) AS nombre_cliente,

                COALESCE(SUM(p.monto), 0) AS total_pagado,
                (v.total - COALESCE(SUM(p.monto), 0)) AS saldo_pendiente

            FROM venta v
            JOIN cliente c ON c.id_cliente = v.id_cliente
            LEFT JOIN pago_venta p ON p.id_venta = v.id_venta

            WHERE v.id_venta = %s
              AND v.eliminado = 0
            GROUP BY v.id_venta
        """, (id_venta,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def obtener_detalles_venta(ids_venta):
    if not ids_venta:
        return {}

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        format_strings = ','.join(['%s'] * len(ids_venta))

        cursor.execute(f"""
            SELECT *
            FROM articulo
            WHERE id_venta IN ({format_strings})
        """, ids_venta)
        articulos = cursor.fetchall()

        ids_articulo = [a["id_articulo"] for a in articulos]
        if not ids_articulo:
            return {}

        format_art = ','.join(['%s'] * len(ids_articulo))

        cursor.execute(f"SELECT * FROM articulo_calzado WHERE id_articulo IN ({format_art})", ids_articulo)
        calzados = {c["id_articulo"]: c for c in cursor.fetchall()}

        cursor.execute(f"SELECT * FROM articulo_confeccion WHERE id_articulo IN ({format_art})", ids_articulo)
        confecciones = {c["id_articulo"]: c for c in cursor.fetchall()}

        cursor.execute(f"SELECT * FROM articulo_maquila WHERE id_articulo IN ({format_art})", ids_articulo)
        maquilas = {m["id_articulo"]: m for m in cursor.fetchall()}

        cursor.execute(f"""
            SELECT
                asv.id_articulo,
                s.nombre,
                asv.precio_aplicado
            FROM articulo_servicio asv
            JOIN servicio s ON s.id_servicio = asv.id_servicio
            WHERE asv.id_articulo IN ({format_art})
        """, ids_articulo)
        servicios_por_articulo = {}
        for s in cursor.fetchall():
            servicios_por_articulo.setdefault(s["id_articulo"], []).append(s)

        detalles_por_venta = {}
        for art in articulos:
            id_venta = art["id_venta"]
            id_articulo = art["id_articulo"]
            tipo = art["tipo_articulo"]

            if tipo == "calzado":
                datos = calzados.get(id_articulo)
            elif tipo == "confeccion":
                datos = confecciones.get(id_articulo)
            else:
                datos = maquilas.get(id_articulo)

            detalle = {
                "tipo_articulo": tipo,
                "datos": datos,
                "servicios": servicios_por_articulo.get(id_articulo, []),
                "comentario": art["comentario"]
            }
            detalles_por_venta.setdefault(id_venta, []).append(detalle)

        return detalles_por_venta
    finally:
        cursor.close()
        conn.close()


def obtener_ventas_listas(id_negocio=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT
                v.id_venta,
                v.fecha_recibo,
                v.fecha_estimada,
                v.fecha_lista,
                v.total,
                c.nombre,
                c.apellido,
                c.telefono,
                n.nombre AS negocio
            FROM venta v
            JOIN cliente c ON c.id_cliente = v.id_cliente
            JOIN negocio n ON n.id_negocio = v.id_negocio
            WHERE v.fecha_lista IS NOT NULL
              AND v.fecha_entrega IS NULL
              AND v.eliminado = 0
        """
        params = []
        if id_negocio:
            query += " AND v.id_negocio = %s"
            params.append(id_negocio)
        query += " ORDER BY v.id_venta ASC"
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def obtener_entregas_pendientes(id_negocio=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT
                v.id_venta,
                v.fecha_recibo,
                v.fecha_estimada,
                v.total,
                c.nombre,
                c.apellido,
                c.telefono,
                n.nombre AS negocio,
                COALESCE(SUM(p.monto), 0) AS total_pagado,
                (v.total - COALESCE(SUM(p.monto), 0)) AS saldo_pendiente
            FROM venta v
            JOIN cliente c ON c.id_cliente = v.id_cliente
            JOIN negocio n ON n.id_negocio = v.id_negocio
            LEFT JOIN pago_venta p ON p.id_venta = v.id_venta
            WHERE v.fecha_lista IS NULL
              AND v.fecha_entrega IS NULL
              AND v.eliminado = 0
        """
        params = []
        if id_negocio:
            query += " AND v.id_negocio = %s"
            params.append(id_negocio)
        query += " GROUP BY v.id_venta ORDER BY v.fecha_estimada ASC"
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def contar_entregas_listas(id_negocio=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        filtros = ""
        params = []
        if id_negocio is not None:
            filtros = " AND id_negocio = %s"
            params.append(id_negocio)
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM venta
            WHERE fecha_lista IS NOT NULL
              AND fecha_entrega IS NULL
              AND eliminado = 0
            {filtros}
        """, params)
        return cursor.fetchone()[0]
    finally:
        cursor.close()
        conn.close()


def contar_entregas_pendientes(id_negocio=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        filtros = ""
        params = []
        if id_negocio is not None:
            filtros = " AND id_negocio = %s"
            params.append(id_negocio)
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM venta
            WHERE fecha_lista IS NULL
              AND fecha_entrega IS NULL
              AND eliminado = 0
            {filtros}
        """, params)
        return cursor.fetchone()[0]
    finally:
        cursor.close()
        conn.close()


def contar_ventas_cliente(id_cliente, id_negocio=None, fecha_inicio=None, fecha_fin=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql = "SELECT COUNT(*) FROM venta WHERE id_cliente=%s AND eliminado=0"
        params = [id_cliente]
        if id_negocio:
            sql += " AND id_negocio=%s"
            params.append(id_negocio)
        if fecha_inicio:
            sql += " AND fecha_recibo >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            sql += " AND fecha_recibo <= %s"
            params.append(fecha_fin)
        cursor.execute(sql, params)
        return cursor.fetchone()[0]
    finally:
        cursor.close()
        conn.close()


def obtener_ventas_cliente(id_cliente, id_negocio, fecha_inicio, fecha_fin, limit, offset):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT v.id_venta, v.fecha_recibo, v.fecha_estimada,
                   v.fecha_lista, v.fecha_entrega,
                   v.total, v.cantidad_descuento,
                   n.nombre AS negocio
            FROM venta v
            LEFT JOIN negocio n ON v.id_negocio = n.id_negocio
            WHERE v.id_cliente = %s
              AND v.eliminado = 0
        """
        params = [id_cliente]
        if id_negocio:
            sql += " AND v.id_negocio=%s"
            params.append(id_negocio)
        if fecha_inicio:
            sql += " AND v.fecha_recibo >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            sql += " AND v.fecha_recibo <= %s"
            params.append(fecha_fin)
        sql += " ORDER BY v.fecha_recibo DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
