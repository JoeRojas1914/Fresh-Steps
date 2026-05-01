from decimal import Decimal
from db import get_connection
from datetime import datetime



def crear_venta(
    id_negocio,
    id_cliente,
    fecha_estimada,
    aplica_descuento,
    cantidad_descuento,
    articulos,
    id_usuario_creo 
):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            INSERT INTO venta (
                id_negocio,
                id_cliente,
                fecha_recibo,
                fecha_estimada,
                aplica_descuento,
                cantidad_descuento,
                total,
                id_usuario_creo
            )
            VALUES (%s, %s, %s, %s, %s, %s, 0, %s)
        """, (
            id_negocio,
            id_cliente,
            datetime.now(),
            fecha_estimada,
            aplica_descuento,
            cantidad_descuento,
            id_usuario_creo
        ))


        id_venta = cursor.lastrowid
        total = Decimal("0.00")

        tipos_por_negocio = {
            1: "calzado",
            2: "confeccion",
            3: "maquila"
        }

        for art in articulos:
            tipo_articulo = art["tipo_articulo"]
            tipo_esperado = tipos_por_negocio.get(id_negocio)

            if tipo_esperado and tipo_articulo != tipo_esperado:
                raise Exception(
                    f"Tipo de artículo inválido. Este negocio solo permite: {tipo_esperado}"
                )

            cursor.execute("""
                INSERT INTO articulo (id_venta, tipo_articulo, comentario)
                VALUES (%s, %s, %s)
            """, (
                id_venta,
                tipo_articulo,
                art.get("comentario")
            ))

            id_articulo = cursor.lastrowid


            if tipo_articulo == "calzado":
                d = art["datos"]

                cursor.execute("""
                    INSERT INTO articulo_calzado (
                        id_articulo,
                        tipo,
                        marca,
                        material,
                        color_base,
                        color_secundario,
                        color_agujetas
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    id_articulo,
                    d["tipo"],
                    d["marca"],
                    d["material"],
                    d["color_base"],
                    d.get("color_secundario"),
                    d.get("color_agujetas")
                ))

                if not art.get("servicios"):
                    raise Exception("Artículo de calzado sin servicios")

                for s in art["servicios"]:
                    id_servicio = int(s["id_servicio"])

                    try:
                        precio_aplicado = Decimal(str(s.get("precio_aplicado") or "0"))
                    except InvalidOperation:
                        precio_aplicado = Decimal("0")

                    if precio_aplicado <= 0:
                        cursor.execute(
                            "SELECT precio_base FROM servicio WHERE id_servicio = %s",
                            (id_servicio,)
                        )
                        row = cursor.fetchone()
                        precio_aplicado = (
                            Decimal(str(row["precio_base"])) if row else Decimal("0")
                        )

                    cursor.execute("""
                        INSERT INTO articulo_servicio (
                            id_articulo,
                            id_servicio,
                            precio_aplicado
                        )
                        VALUES (%s, %s, %s)
                    """, (id_articulo, id_servicio, precio_aplicado))

                    total += precio_aplicado


            elif tipo_articulo == "confeccion":
                d = art["datos"]

                cantidad = Decimal(str(d.get("cantidad", 1)))

                cursor.execute("""
                    INSERT INTO articulo_confeccion (
                        id_articulo,
                        tipo,
                        marca,
                        material,
                        color_base,
                        color_secundario,
                        cantidad,
                        agujetas
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    id_articulo,
                    d["tipo"],
                    d["marca"],
                    d["material"],
                    d["color_base"],
                    d.get("color_secundario"),
                    int(cantidad),
                    d["agujetas"]
                ))

                if not art.get("servicios"):
                    raise Exception("Artículo de confección sin servicios")

                for s in art["servicios"]:
                    id_servicio = int(s["id_servicio"])

                    try:
                        precio_aplicado = Decimal(str(s.get("precio_aplicado") or "0"))
                    except InvalidOperation:
                        precio_aplicado = Decimal("0")

                    if precio_aplicado <= 0:
                        cursor.execute(
                            "SELECT precio_base FROM servicio WHERE id_servicio = %s",
                            (id_servicio,)
                        )
                        row = cursor.fetchone()
                        precio_aplicado = (
                            Decimal(str(row["precio_base"])) if row else Decimal("0")
                        )

                    cursor.execute("""
                        INSERT INTO articulo_servicio (
                            id_articulo,
                            id_servicio,
                            precio_aplicado
                        )
                        VALUES (%s, %s, %s)
                    """, (id_articulo, id_servicio, precio_aplicado))

                    total += cantidad * precio_aplicado

            elif tipo_articulo == "maquila":
                d = art["datos"]

                cantidad = Decimal(str(d["cantidad"]))
                precio_unitario = Decimal(str(d["precio_unitario"]))

                cursor.execute("""
                    INSERT INTO articulo_maquila (
                        id_articulo,
                        tipo,
                        cantidad,
                        precio_unitario
                    )
                    VALUES (%s, %s, %s, %s)
                """, (
                    id_articulo,
                    d["tipo"],
                    int(cantidad),
                    precio_unitario
                ))

                total += cantidad * precio_unitario


        if aplica_descuento and cantidad_descuento:
            total -= Decimal(str(cantidad_descuento))
            if total < 0:
                total = Decimal("0.00")

        cursor.execute(
            "UPDATE venta SET total = %s WHERE id_venta = %s",
            (str(total), id_venta)
        )

        conn.commit()
        return id_venta

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()



def contar_entregas_listas(id_negocio=None):
    conn = get_connection()
    cursor = conn.cursor()

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
        {filtros}
    """, params)

    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return total




def marcar_entregada(id_venta, id_usuario):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE venta
            SET fecha_entrega = NOW(),
                id_usuario_entrego = %s
            WHERE id_venta = %s
              AND fecha_entrega IS NULL
        """, (id_usuario, id_venta))

        conn.commit()

        return cursor.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()





def obtener_detalles_venta(ids_venta):
    if not ids_venta:
        return {}

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

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

    cursor.execute(f"""
        SELECT * FROM articulo_calzado
        WHERE id_articulo IN ({format_art})
    """, ids_articulo)
    calzados = {c["id_articulo"]: c for c in cursor.fetchall()}

    cursor.execute(f"""
        SELECT * FROM articulo_confeccion
        WHERE id_articulo IN ({format_art})
    """, ids_articulo)
    confecciones = {c["id_articulo"]: c for c in cursor.fetchall()}

    cursor.execute(f"""
        SELECT * FROM articulo_maquila
        WHERE id_articulo IN ({format_art})
    """, ids_articulo)
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

    servicios_raw = cursor.fetchall()

    servicios_por_articulo = {}
    for s in servicios_raw:
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

    cursor.close()
    conn.close()

    return detalles_por_venta




def obtener_ventas_listas(id_negocio=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

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
    """

    params = []

    if id_negocio:
        query += " AND v.id_negocio = %s"
        params.append(id_negocio)

    query += " ORDER BY v.id_venta ASC"

    cursor.execute(query, params)
    ventas = cursor.fetchall()

    cursor.close()
    conn.close()
    return ventas



def obtener_venta(id_venta):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

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
        GROUP BY v.id_venta
    """, (id_venta,))

    venta = cursor.fetchone()

    cursor.close()
    conn.close()
    return venta



def contar_ventas_cliente(id_cliente, id_negocio=None, fecha_inicio=None, fecha_fin=None):
    conn = get_connection()
    cursor = conn.cursor()

    sql = "SELECT COUNT(*) FROM venta WHERE id_cliente=%s"
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
    total = cursor.fetchone()[0]

    cursor.close()
    conn.close()
    return total


def obtener_ventas_cliente(id_cliente, id_negocio, fecha_inicio, fecha_fin, limit, offset):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT v.id_venta, v.fecha_recibo, v.fecha_entrega,
               v.total, v.cantidad_descuento,
               n.nombre AS negocio
        FROM venta v
        LEFT JOIN negocio n ON v.id_negocio = n.id_negocio
        WHERE v.id_cliente = %s
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
    data = cursor.fetchall()

    cursor.close()
    conn.close()
    return data


def obtener_entregas_pendientes(id_negocio=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            v.id_venta,
            v.fecha_recibo,
            v.fecha_estimada,
            v.total,
            c.nombre,
            c.apellido,
            c.telefono,
            n.nombre AS negocio
        FROM venta v
        JOIN cliente c ON c.id_cliente = v.id_cliente
        JOIN negocio n ON n.id_negocio = v.id_negocio
        WHERE v.fecha_lista IS NULL
          AND v.fecha_entrega IS NULL
    """

    params = []

    if id_negocio:
        query += " AND v.id_negocio = %s"
        params.append(id_negocio)

    query += " ORDER BY v.fecha_estimada ASC"

    cursor.execute(query, params)
    ventas = cursor.fetchall()

    cursor.close()
    conn.close()
    return ventas


def contar_entregas_pendientes(id_negocio=None):
    conn = get_connection()
    cursor = conn.cursor()

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
        {filtros}
    """, params)

    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return total


def marcar_como_lista(id_venta):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE venta
            SET fecha_lista = NOW()
            WHERE id_venta = %s
              AND fecha_lista IS NULL
              AND fecha_entrega IS NULL
        """, (id_venta,))

        conn.commit()

        return cursor.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


def eliminar_venta(id_venta):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id_articulo
            FROM articulo
            WHERE id_venta = %s
        """, (id_venta,))
        
        articulos = cursor.fetchall()
        ids_articulos = [row[0] for row in articulos]

        if ids_articulos:
            format_strings = ','.join(['%s'] * len(ids_articulos))

            cursor.execute(f"""
                DELETE FROM articulo_servicio
                WHERE id_articulo IN ({format_strings})
            """, ids_articulos)

            cursor.execute(f"""
                DELETE FROM articulo_calzado
                WHERE id_articulo IN ({format_strings})
            """, ids_articulos)

            cursor.execute(f"""
                DELETE FROM articulo_confeccion
                WHERE id_articulo IN ({format_strings})
            """, ids_articulos)

            cursor.execute(f"""
                DELETE FROM articulo_maquila
                WHERE id_articulo IN ({format_strings})
            """, ids_articulos)

            cursor.execute(f"""
                DELETE FROM articulo
                WHERE id_articulo IN ({format_strings})
            """, ids_articulos)

        cursor.execute("""
            DELETE FROM pago_venta
            WHERE id_venta = %s
        """, (id_venta,))

        cursor.execute("""
            DELETE FROM venta
            WHERE id_venta = %s
        """, (id_venta,))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()