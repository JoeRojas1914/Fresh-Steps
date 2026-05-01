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
    num_semana = 1

    while actual <= fin:
        semana_fin = actual + timedelta(days=6)

        label = [
            f"Semana {num_semana}",
            f"{fecha_bonita(actual)} - {fecha_bonita(semana_fin)}"
        ]

        semanas.append({
            "inicio": actual,
            "fin": semana_fin,
            "label": label
        })

        actual += timedelta(days=7)
        num_semana += 1

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
            semana_fin = min(s["fin"], fin)
            total_unidades = 0

            if id_negocio in ("1", "all"):
                cursor.execute("""
                    SELECT COUNT(a.id_articulo) AS total
                    FROM venta v
                    JOIN articulo a ON a.id_venta = v.id_venta
                    JOIN articulo_calzado aca ON aca.id_articulo = a.id_articulo
                    WHERE v.fecha_recibo >= %s
                      AND v.fecha_recibo < DATE_ADD(%s, INTERVAL 1 DAY)
                      AND v.id_negocio = 1
                      AND v.eliminado = 0
                """, [semana_inicio, semana_fin])
                total_unidades += cursor.fetchone()["total"]

            if id_negocio in ("2", "all"):
                cursor.execute("""
                    SELECT COALESCE(SUM(ac.cantidad), 0) AS total
                    FROM venta v
                    JOIN articulo a ON a.id_venta = v.id_venta
                    JOIN articulo_confeccion ac ON ac.id_articulo = a.id_articulo
                    WHERE v.fecha_recibo >= %s
                      AND v.fecha_recibo < DATE_ADD(%s, INTERVAL 1 DAY)
                      AND v.id_negocio = 2
                      AND v.eliminado = 0
                """, [semana_inicio, semana_fin])
                total_unidades += cursor.fetchone()["total"]

            if id_negocio in ("3", "all"):
                cursor.execute("""
                    SELECT COALESCE(SUM(am.cantidad), 0) AS total
                    FROM venta v
                    JOIN articulo a ON a.id_venta = v.id_venta
                    JOIN articulo_maquila am ON am.id_articulo = a.id_articulo
                    WHERE v.fecha_recibo >= %s
                      AND v.fecha_recibo < DATE_ADD(%s, INTERVAL 1 DAY)
                      AND v.id_negocio = 3
                      AND v.eliminado = 0
                """, [semana_inicio, semana_fin])
                total_unidades += cursor.fetchone()["total"]

            resultados.append({"label": s["label"], "total": int(total_unidades)})

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