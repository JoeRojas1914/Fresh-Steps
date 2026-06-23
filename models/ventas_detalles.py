from db import get_db


def obtener_venta(id_venta):
    with get_db() as (_, cursor):
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


def _extraer_datos(tipo, fila):
    if tipo == "calzado":
        return {
            "tipo": fila["c_tipo"], "marca": fila["c_marca"],
            "material": fila["c_material"], "color_base": fila["c_color_base"],
            "color_secundario": fila["c_color_secundario"],
            "color_agujetas": fila["c_color_agujetas"],
        }
    if tipo == "confeccion":
        return {
            "tipo": fila["cf_tipo"], "marca": fila["cf_marca"],
            "material": fila["cf_material"], "color_base": fila["cf_color_base"],
            "color_secundario": fila["cf_color_secundario"],
            "cantidad": fila["cf_cantidad"],
        }
    return {
        "tipo": fila["m_tipo"], "cantidad": fila["m_cantidad"],
        "precio_unitario": fila["m_precio_unitario"],
    }


def obtener_detalles_venta(ids_venta):
    if not ids_venta:
        return {}

    with get_db() as (_, cursor):
        ph = ','.join(['%s'] * len(ids_venta))
        cursor.execute(
            "SELECT"
            "  a.id_articulo, a.id_venta, a.tipo_articulo, a.comentario,"
            "  ac.tipo AS c_tipo, ac.marca AS c_marca, ac.material AS c_material,"
            "  ac.color_base AS c_color_base, ac.color_secundario AS c_color_secundario,"
            "  ac.color_agujetas AS c_color_agujetas,"
            "  acf.tipo AS cf_tipo, acf.marca AS cf_marca, acf.material AS cf_material,"
            "  acf.color_base AS cf_color_base, acf.color_secundario AS cf_color_secundario,"
            "  acf.cantidad AS cf_cantidad,"
            "  am.tipo AS m_tipo, am.cantidad AS m_cantidad, am.precio_unitario AS m_precio_unitario"
            " FROM articulo a"
            " LEFT JOIN articulo_calzado    ac  ON ac.id_articulo  = a.id_articulo"
            " LEFT JOIN articulo_confeccion acf ON acf.id_articulo = a.id_articulo"
            " LEFT JOIN articulo_maquila    am  ON am.id_articulo  = a.id_articulo"
            " WHERE a.id_venta IN (" + ph + ")",
            tuple(ids_venta),
        )
        filas = cursor.fetchall()
        if not filas:
            return {}

        ids_articulo = [f["id_articulo"] for f in filas]
        ph_art = ','.join(['%s'] * len(ids_articulo))
        cursor.execute(
            "SELECT asv.id_articulo, s.nombre, asv.precio_aplicado"
            " FROM articulo_servicio asv"
            " JOIN servicio s ON s.id_servicio = asv.id_servicio"
            " WHERE asv.id_articulo IN (" + ph_art + ")",
            tuple(ids_articulo),
        )
        servicios_por_articulo: dict = {}
        for s in cursor.fetchall():
            servicios_por_articulo.setdefault(s["id_articulo"], []).append(
                {"nombre": s["nombre"], "precio_aplicado": s["precio_aplicado"]}
            )

        detalles_por_venta: dict = {}
        for f in filas:
            detalles_por_venta.setdefault(f["id_venta"], []).append({
                "tipo_articulo": f["tipo_articulo"],
                "datos":         _extraer_datos(f["tipo_articulo"], f),
                "servicios":     servicios_por_articulo.get(f["id_articulo"], []),
                "comentario":    f["comentario"],
            })
        return detalles_por_venta


def obtener_ventas_listas(id_negocio=None, id_venta=None, q=None, limit=None, offset=0):
    with get_db() as (_, cursor):
        sql = """
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
            sql += " AND v.id_negocio = %s"
            params.append(id_negocio)
        if id_venta:
            sql += " AND CAST(v.id_venta AS CHAR) LIKE %s"
            params.append(f"{id_venta}%")
        if q:
            like = f"%{q}%"
            sql += " AND (c.nombre LIKE %s OR c.apellido LIKE %s"
            sql += " OR CONCAT(c.nombre, ' ', c.apellido) LIKE %s)"
            params.extend([like, like, like])
        sql += " ORDER BY v.id_negocio ASC, v.id_venta ASC"
        if limit is not None:
            sql += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])
        cursor.execute(sql, params)
        return cursor.fetchall()


def obtener_entregas_pendientes(id_negocio=None, id_venta=None, q=None, limit=None, offset=0):
    with get_db() as (_, cursor):
        sql = """
            SELECT
                v.id_venta,
                v.id_negocio,
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
            sql += " AND v.id_negocio = %s"
            params.append(id_negocio)
        if id_venta:
            sql += " AND CAST(v.id_venta AS CHAR) LIKE %s"
            params.append(f"{id_venta}%")
        if q:
            like = f"%{q}%"
            sql += " AND (c.nombre LIKE %s OR c.apellido LIKE %s"
            sql += " OR CONCAT(c.nombre, ' ', c.apellido) LIKE %s)"
            params.extend([like, like, like])
        sql += " GROUP BY v.id_venta ORDER BY v.fecha_estimada ASC, v.id_negocio ASC, v.id_venta ASC"
        if limit is not None:
            sql += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])
        cursor.execute(sql, params)
        return cursor.fetchall()


def contar_entregas_resumen(id_negocio=None, id_venta=None, q=None):
    sql = """
        SELECT
            SUM(CASE WHEN v.fecha_lista IS NOT NULL AND v.fecha_entrega IS NULL THEN 1 ELSE 0 END) AS listas,
            SUM(CASE WHEN v.fecha_lista IS NULL     AND v.fecha_entrega IS NULL THEN 1 ELSE 0 END) AS pendientes
        FROM venta v
        JOIN cliente c ON c.id_cliente = v.id_cliente
        WHERE v.eliminado = 0
    """
    params = []
    if id_negocio is not None:
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)
    if id_venta:
        sql += " AND CAST(v.id_venta AS CHAR) LIKE %s"
        params.append(f"{id_venta}%")
    if q:
        like = f"%{q}%"
        sql += " AND (c.nombre LIKE %s OR c.apellido LIKE %s"
        sql += " OR CONCAT(c.nombre, ' ', c.apellido) LIKE %s)"
        params.extend([like, like, like])
    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        row = cursor.fetchone()
    return int(row["listas"] or 0), int(row["pendientes"] or 0)


def contar_entregas_listas(id_negocio=None, id_venta=None, q=None):
    listas, _ = contar_entregas_resumen(id_negocio, id_venta, q)
    return listas


def contar_entregas_pendientes(id_negocio=None, id_venta=None, q=None):
    _, pendientes = contar_entregas_resumen(id_negocio, id_venta, q)
    return pendientes


def contar_ventas_cliente(id_cliente, id_negocio=None, fecha_inicio=None, fecha_fin=None):
    with get_db() as (_, cursor):
        sql = "SELECT COUNT(*) AS total FROM venta WHERE id_cliente=%s AND eliminado=0"
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
        return cursor.fetchone()["total"]


def obtener_ventas_cliente(id_cliente, id_negocio, fecha_inicio, fecha_fin, limit, offset):
    with get_db() as (_, cursor):
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


def obtener_kpis_cliente(id_cliente: int) -> dict:
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT
                COALESCE(SUM(v.total), 0) AS total_gastado,
                COALESCE((
                    SELECT SUM(pv.monto)
                    FROM pago_venta pv
                    JOIN venta v3 ON pv.id_venta = v3.id_venta
                    WHERE v3.id_cliente = %s AND v3.eliminado = 0
                ), 0) AS total_pagado
            FROM venta v
            WHERE v.id_cliente = %s AND v.eliminado = 0
        """, (id_cliente, id_cliente))
        row = cursor.fetchone()

    total_gastado = float(row["total_gastado"] or 0)
    total_pagado  = float(row["total_pagado"]  or 0)
    return {
        "total_gastado":         total_gastado,
        "saldo_pendiente_total": max(round(total_gastado - total_pagado, 2), 0),
    }
