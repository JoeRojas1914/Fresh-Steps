from decimal import Decimal, InvalidOperation
from db import get_connection
from datetime import datetime

# Fuente única de verdad para el mapeo negocio → tipo de artículo.
# Importar desde aquí en cualquier módulo que lo necesite.
TIPOS_POR_NEGOCIO = {
    1: "calzado",
    2: "confeccion",
    3: "maquila",
}

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

        for art in articulos:
            tipo_articulo = art["tipo_articulo"]
            tipo_esperado = TIPOS_POR_NEGOCIO.get(id_negocio)

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

        registrar_historial_venta(cursor, id_venta, "CREADO", id_usuario_creo, None, {
            "id_negocio": id_negocio,
            "id_cliente": id_cliente,
            "fecha_estimada": str(fecha_estimada),
            "total": float(total),
        })

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

        total = cursor.fetchone()[0]
        return total
    finally:
        cursor.close()
        conn.close()




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

        afectadas = cursor.rowcount
        if afectadas > 0:
            registrar_historial_venta(cursor, id_venta, "ENTREGADO", id_usuario)

        conn.commit()

        return afectadas > 0

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
        ventas = cursor.fetchall()

        return ventas
    finally:
        cursor.close()
        conn.close()



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

        venta = cursor.fetchone()

        return venta
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
        total = cursor.fetchone()[0]

        return total
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
        data = cursor.fetchall()

        return data
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
        ventas = cursor.fetchall()

        return ventas
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

        total = cursor.fetchone()[0]
        return total
    finally:
        cursor.close()
        conn.close()


def marcar_como_lista(id_venta, id_usuario=None):
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

        afectadas = cursor.rowcount
        if afectadas > 0 and id_usuario:
            registrar_historial_venta(cursor, id_venta, "LISTA", id_usuario)

        conn.commit()

        return afectadas > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


def eliminar_venta(id_venta, id_usuario=None):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE venta
            SET eliminado = 1,
                fecha_eliminado = NOW()
            WHERE id_venta = %s
              AND eliminado = 0
        """, (id_venta,))

        afectadas = cursor.rowcount
        if afectadas > 0 and id_usuario:
            registrar_historial_venta(cursor, id_venta, "ELIMINADO", id_usuario)

        conn.commit()

        return afectadas > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

def contar_historial_ventas(id_negocio=None, fecha_inicio=None, fecha_fin=None, mostrar_eliminadas=False, q=None):
    """Cuenta el total de ventas para la paginacion del historial."""
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
        total = cursor.fetchone()[0]
        return total
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

def registrar_historial_venta(cursor, id_venta, accion, id_usuario, antes=None, despues=None):
    import json as _json
    from decimal import Decimal
    from datetime import date, datetime

    def safe(d):
        if not d:
            return None
        out = {}
        for k, v in d.items():
            if isinstance(v, Decimal):   out[k] = float(v)
            elif isinstance(v, (date, datetime)): out[k] = v.isoformat()
            else: out[k] = v
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