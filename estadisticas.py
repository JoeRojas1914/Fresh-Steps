from collections import defaultdict
from datetime import date, timedelta
from db import get_connection

def generar_semanas_rango(inicio: date, fin: date):
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    def fecha_bonita(d: date):
        return f"{d.day} {meses[d.month - 1]}"

    inicio_lunes = inicio - timedelta(days=inicio.weekday())

    semanas = []
    actual = inicio_lunes

    while actual <= fin:
        semana_fin  = actual + timedelta(days=6)
        num_semana  = actual.isocalendar()[1]  
        anio        = actual.isocalendar()[0]

        label = [
            f"Sem {num_semana} ({anio})",
            f"{fecha_bonita(actual)} - {fecha_bonita(semana_fin)}"
        ]

        semanas.append({
            "inicio": actual,
            "fin":    semana_fin,
            "label":  label
        })

        actual += timedelta(days=7)

    return semanas



def contar_ventas_por_semana(inicio: date, fin: date, id_negocio: str):
    semanas = generar_semanas_rango(inicio, fin)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    resultados = []

    try:
        for s in semanas:
            semana_inicio_real = max(s["inicio"], inicio)
            semana_fin_real = min(s["fin"], fin)

            query = """
                SELECT COUNT(*) AS total
                FROM venta
                WHERE fecha_recibo >= %s
                AND fecha_recibo < DATE_ADD(%s, INTERVAL 1 DAY)
                AND eliminado = 0
            """
            params = [semana_inicio_real, semana_fin_real]

            if id_negocio != "all":
                query += " AND id_negocio = %s"
                params.append(id_negocio)

            cursor.execute(query, params)
            total = cursor.fetchone()["total"]

            resultados.append({"label": s["label"], "total": total})

    finally:
        cursor.close()
        conn.close()

    return resultados


def obtener_gastos_por_semana_y_proveedor(inicio: date, fin: date, id_negocio: str):
    semanas = generar_semanas_rango(inicio, fin)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    data_por_proveedor = defaultdict(lambda: [0] * len(semanas))

    try:
        for i, s in enumerate(semanas):
            semana_inicio_real = max(s["inicio"], inicio)
            semana_fin_real = min(s["fin"], fin)

            query = """
                SELECT proveedor, SUM(total) AS total
                FROM gastos
                WHERE fecha_registro >= %s
                  AND fecha_registro <= %s
            """
            params = [semana_inicio_real, semana_fin_real]

            if id_negocio != "all":
                query += " AND id_negocio = %s"
                params.append(id_negocio)

            query += " GROUP BY proveedor"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            for r in rows:
                proveedor = r["proveedor"] or "Sin proveedor"
                data_por_proveedor[proveedor][i] = float(r["total"] or 0)

    finally:
        cursor.close()
        conn.close()

    labels = [s["label"] for s in semanas]
    datasets = [{"label": p, "data": v} for p, v in data_por_proveedor.items()]

    return {"labels": labels, "datasets": datasets}



def obtener_total_gastos(inicio: date, fin: date, id_negocio: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT COALESCE(SUM(total), 0) AS total
        FROM gastos
        WHERE fecha_registro >= %s
          AND fecha_registro <= %s
    """
    params = [inicio, fin]

    if id_negocio != "all":
        query += " AND id_negocio = %s"
        params.append(id_negocio)

    try:
        cursor.execute(query, params)
        total = cursor.fetchone()["total"] or 0
    finally:
        cursor.close()
        conn.close()

    return float(total)



def obtener_unidades_por_semana(inicio: date, fin: date, id_negocio: str):
    semanas = generar_semanas_rango(inicio, fin)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    resultados = []

    try:
        for s in semanas:
            semana_inicio = max(s["inicio"], inicio)
            semana_fin    = min(s["fin"],    fin)
            partes  = []
            params  = []

            if id_negocio in ("1", "all"):
                partes.append("""
                    SELECT COUNT(a.id_articulo) AS u
                    FROM venta v
                    JOIN articulo a          ON a.id_venta    = v.id_venta
                    JOIN articulo_calzado ac ON ac.id_articulo = a.id_articulo
                    WHERE v.fecha_recibo >= %s
                      AND v.fecha_recibo <  DATE_ADD(%s, INTERVAL 1 DAY)
                      AND v.id_negocio = 1
                      AND v.eliminado  = 0
                """)
                params += [semana_inicio, semana_fin]

            if id_negocio in ("2", "all"):
                partes.append("""
                    SELECT COALESCE(SUM(ac2.cantidad), 0) AS u
                    FROM venta v
                    JOIN articulo a            ON a.id_venta      = v.id_venta
                    JOIN articulo_confeccion ac2 ON ac2.id_articulo = a.id_articulo
                    WHERE v.fecha_recibo >= %s
                      AND v.fecha_recibo <  DATE_ADD(%s, INTERVAL 1 DAY)
                      AND v.id_negocio = 2
                      AND v.eliminado  = 0
                """)
                params += [semana_inicio, semana_fin]

            if id_negocio in ("3", "all"):
                partes.append("""
                    SELECT COALESCE(SUM(am.cantidad), 0) AS u
                    FROM venta v
                    JOIN articulo a          ON a.id_venta    = v.id_venta
                    JOIN articulo_maquila am ON am.id_articulo = a.id_articulo
                    WHERE v.fecha_recibo >= %s
                      AND v.fecha_recibo <  DATE_ADD(%s, INTERVAL 1 DAY)
                      AND v.id_negocio = 3
                      AND v.eliminado  = 0
                """)
                params += [semana_inicio, semana_fin]

            if partes:
                sql = "SELECT SUM(u) AS total FROM (" + " UNION ALL ".join(partes) + ") t"
                cursor.execute(sql, params)
                row = cursor.fetchone()
                total = int(row["total"] or 0)
            else:
                total = 0

            resultados.append({"label": s["label"], "total": total})

    finally:
        cursor.close()
        conn.close()

    return resultados



def obtener_total_ingresos(inicio, fin, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT COALESCE(SUM(pv.monto), 0) AS total
        FROM pago_venta pv
        JOIN venta v ON v.id_venta = pv.id_venta
        WHERE pv.fecha_pago >= %s
          AND pv.fecha_pago < DATE_ADD(%s, INTERVAL 1 DAY)
          AND v.eliminado = 0
    """
    params = [inicio, fin]

    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)

    try:
        cursor.execute(sql, params)
        total = cursor.fetchone()["total"] or 0
    finally:
        cursor.close()
        conn.close()

    return float(total)




def obtener_ingresos_por_semana(inicio, fin, id_negocio):
    semanas = generar_semanas_rango(inicio, fin)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    resultados = []

    try:
        for s in semanas:
            semana_inicio = max(s["inicio"], inicio)
            semana_fin = min(s["fin"], fin)

            sql = """
                SELECT COALESCE(SUM(pv.monto), 0) AS total
                FROM pago_venta pv
                JOIN venta v ON v.id_venta = pv.id_venta
                WHERE pv.fecha_pago >= %s
                  AND pv.fecha_pago < DATE_ADD(%s, INTERVAL 1 DAY)
                  AND v.eliminado = 0
            """
            params = [semana_inicio, semana_fin]

            if id_negocio != "all":
                sql += " AND v.id_negocio = %s"
                params.append(id_negocio)

            cursor.execute(sql, params)
            total = cursor.fetchone()["total"] or 0

            resultados.append({"label": s["label"], "total": float(total)})

    finally:
        cursor.close()
        conn.close()

    return resultados



def ejecutar_query(sql, params=None):
    """Abre su propia conexión. Usar solo para queries simples de una sola llamada."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or [])
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def obtener_uso_servicios(inicio, fin, id_negocio):
    sql = """
        SELECT s.nombre, COUNT(*) total
        FROM articulo_servicio aps
        JOIN servicio s ON s.id_servicio = aps.id_servicio
        JOIN articulo a ON a.id_articulo = aps.id_articulo
        JOIN venta v ON v.id_venta = a.id_venta
        WHERE DATE(v.fecha_recibo) BETWEEN %s AND %s
          AND v.eliminado = 0
    """
    params = [inicio, fin]

    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)

    sql += " GROUP BY s.id_servicio ORDER BY total DESC"

    return ejecutar_query(sql, params)


def obtener_ventas_con_y_sin_prepago(inicio, fin, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT
            CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM pago_venta pv
                    WHERE pv.id_venta = v.id_venta
                      AND pv.tipo_pago_venta = 'prepago'
                )
                THEN 'Con prepago'
                ELSE 'Sin prepago'
            END AS tipo,
            COUNT(*) AS total
        FROM venta v
        WHERE DATE(v.fecha_recibo) BETWEEN %s AND %s
          AND v.eliminado = 0
    """
    params = [inicio, fin]

    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)

    sql += " GROUP BY tipo"

    try:
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def obtener_ventas_por_dia(inicio, fin, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT
            WEEKDAY(fecha_recibo) AS dia,
            COUNT(*) AS total
        FROM venta
        WHERE DATE(fecha_recibo) BETWEEN %s AND %s
          AND WEEKDAY(fecha_recibo) BETWEEN 0 AND 5
          AND eliminado = 0
    """
    params = [inicio, fin]

    if id_negocio != "all":
        sql += " AND id_negocio = %s"
        params.append(id_negocio)

    sql += " GROUP BY dia"

    try:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    dias = [0, 0, 0, 0, 0, 0]
    for r in rows:
        dias[r["dia"]] = r["total"]

    return dias


def obtener_ticket_promedio(inicio, fin, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT COALESCE(AVG(total), 0) AS promedio,
               COUNT(*)               AS num_ventas
        FROM venta
        WHERE DATE(fecha_recibo) BETWEEN %s AND %s
          AND eliminado = 0
    """
    params = [inicio, fin]

    if id_negocio != "all":
        sql += " AND id_negocio = %s"
        params.append(id_negocio)

    try:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return float(row["promedio"] or 0), int(row["num_ventas"] or 0)
    finally:
        cursor.close()
        conn.close()


def obtener_saldo_por_cobrar(inicio, fin, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT COALESCE(
            SUM(v.total - COALESCE(p.pagado, 0)), 0
        ) AS saldo
        FROM venta v
        LEFT JOIN (
            SELECT id_venta, SUM(monto) AS pagado
            FROM pago_venta
            GROUP BY id_venta
        ) p ON p.id_venta = v.id_venta
        WHERE DATE(v.fecha_recibo) BETWEEN %s AND %s
          AND v.eliminado = 0
          AND (v.total - COALESCE(p.pagado, 0)) > 0
    """
    params = [inicio, fin]

    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)

    try:
        cursor.execute(sql, params)
        return float(cursor.fetchone()["saldo"] or 0)
    finally:
        cursor.close()
        conn.close()