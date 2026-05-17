from collections import defaultdict
from datetime import date, timedelta
from db import get_db


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
        semana_fin = actual + timedelta(days=6)
        num_semana = actual.isocalendar()[1]
        anio       = actual.isocalendar()[0]
        semanas.append({
            "inicio": actual,
            "fin":    semana_fin,
            "label":  [
                f"Sem {num_semana} ({anio})",
                f"{fecha_bonita(actual)} - {fecha_bonita(semana_fin)}"
            ],
        })
        actual += timedelta(days=7)

    return semanas


_DIAS_CORTOS  = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
_MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun",
                 "jul", "ago", "sep", "oct", "nov", "dic"]


def _label_dia(d: date) -> str:
    return f"{_DIAS_CORTOS[d.weekday()]} {d.day} {_MESES_CORTOS[d.month - 1]}"


def contar_ventas_por_semana(inicio: date, fin: date, id_negocio: str):
    semanas = generar_semanas_rango(inicio, fin)
    resultados = []

    with get_db() as (_, cursor):
        for s in semanas:
            semana_inicio_real = max(s["inicio"], inicio)
            semana_fin_real    = min(s["fin"],    fin)

            sql = """
                SELECT COUNT(*) AS total
                FROM venta
                WHERE fecha_recibo >= %s
                  AND fecha_recibo < DATE_ADD(%s, INTERVAL 1 DAY)
                  AND eliminado = 0
            """
            params = [semana_inicio_real, semana_fin_real]

            if id_negocio != "all":
                sql += " AND id_negocio = %s"
                params.append(id_negocio)

            cursor.execute(sql, params)
            resultados.append({"label": s["label"], "total": cursor.fetchone()["total"]})

    return resultados


def obtener_unidades_por_semana(inicio: date, fin: date, id_negocio: str):
    """
    Suma unidades por semana ejecutando una query separada por tipo de negocio
    y acumulando los resultados en Python — evita el UNION ALL dinámico.
    """
    semanas = generar_semanas_rango(inicio, fin)
    resultados = []

    with get_db() as (_, cursor):
        for s in semanas:
            semana_inicio = max(s["inicio"], inicio)
            semana_fin    = min(s["fin"],    fin)
            total = 0

            if id_negocio in ("1", "all"):
                cursor.execute("""
                    SELECT COUNT(a.id_articulo) AS u
                    FROM venta v
                    JOIN articulo a           ON a.id_venta     = v.id_venta
                    JOIN articulo_calzado ac  ON ac.id_articulo = a.id_articulo
                    WHERE v.fecha_recibo >= %s
                      AND v.fecha_recibo <  DATE_ADD(%s, INTERVAL 1 DAY)
                      AND v.id_negocio = 1
                      AND v.eliminado  = 0
                """, (semana_inicio, semana_fin))
                total += int(cursor.fetchone()["u"] or 0)

            if id_negocio in ("2", "all"):
                cursor.execute("""
                    SELECT COALESCE(SUM(ac2.cantidad), 0) AS u
                    FROM venta v
                    JOIN articulo a               ON a.id_venta      = v.id_venta
                    JOIN articulo_confeccion ac2  ON ac2.id_articulo = a.id_articulo
                    WHERE v.fecha_recibo >= %s
                      AND v.fecha_recibo <  DATE_ADD(%s, INTERVAL 1 DAY)
                      AND v.id_negocio = 2
                      AND v.eliminado  = 0
                """, (semana_inicio, semana_fin))
                total += int(cursor.fetchone()["u"] or 0)

            if id_negocio in ("3", "all"):
                cursor.execute("""
                    SELECT COALESCE(SUM(am.cantidad), 0) AS u
                    FROM venta v
                    JOIN articulo a           ON a.id_venta     = v.id_venta
                    JOIN articulo_maquila am  ON am.id_articulo = a.id_articulo
                    WHERE v.fecha_recibo >= %s
                      AND v.fecha_recibo <  DATE_ADD(%s, INTERVAL 1 DAY)
                      AND v.id_negocio = 3
                      AND v.eliminado  = 0
                """, (semana_inicio, semana_fin))
                total += int(cursor.fetchone()["u"] or 0)

            resultados.append({"label": s["label"], "total": total})

    return resultados


def obtener_total_ingresos(inicio, fin, id_negocio):
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

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return float(cursor.fetchone()["total"] or 0)


def obtener_ingresos_por_semana(inicio, fin, id_negocio):
    semanas = generar_semanas_rango(inicio, fin)
    resultados = []

    with get_db() as (_, cursor):
        for s in semanas:
            semana_inicio = max(s["inicio"], inicio)
            semana_fin    = min(s["fin"],    fin)

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
            resultados.append({"label": s["label"], "total": float(cursor.fetchone()["total"] or 0)})

    return resultados


def contar_ventas_por_hora(inicio: date, fin: date, id_negocio: str):
    sql = """
        SELECT HOUR(fecha_recibo) AS hora, COUNT(*) AS total
        FROM venta
        WHERE DATE(fecha_recibo) BETWEEN %s AND %s
          AND eliminado = 0
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND id_negocio = %s"
        params.append(id_negocio)
    sql += " GROUP BY hora"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["hora"]: r["total"] for r in cursor.fetchall()}
    return [{"label": f"{h}:00", "total": rows.get(h, 0)} for h in range(7, 22)]


def obtener_ingresos_por_hora(inicio: date, fin: date, id_negocio: str):
    sql = """
        SELECT HOUR(pv.fecha_pago) AS hora, COALESCE(SUM(pv.monto), 0) AS total
        FROM pago_venta pv
        JOIN venta v ON v.id_venta = pv.id_venta
        WHERE DATE(pv.fecha_pago) BETWEEN %s AND %s
          AND v.eliminado = 0
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)
    sql += " GROUP BY hora"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["hora"]: float(r["total"]) for r in cursor.fetchall()}
    return [{"label": f"{h}:00", "total": rows.get(h, 0.0)} for h in range(7, 22)]


def obtener_unidades_por_hora(inicio: date, fin: date, id_negocio: str):
    sql = """
        SELECT HOUR(v.fecha_recibo) AS hora, COUNT(a.id_articulo) AS total
        FROM venta v
        JOIN articulo a ON a.id_venta = v.id_venta
        WHERE DATE(v.fecha_recibo) BETWEEN %s AND %s
          AND v.eliminado = 0
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)
    sql += " GROUP BY hora"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["hora"]: int(r["total"]) for r in cursor.fetchall()}
    return [{"label": f"{h}:00", "total": rows.get(h, 0)} for h in range(7, 22)]


def contar_ventas_por_dia_rango(inicio: date, fin: date, id_negocio: str):
    sql = """
        SELECT DATE(fecha_recibo) AS dia, COUNT(*) AS total
        FROM venta
        WHERE DATE(fecha_recibo) BETWEEN %s AND %s
          AND eliminado = 0
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND id_negocio = %s"
        params.append(id_negocio)
    sql += " GROUP BY dia"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["dia"]: r["total"] for r in cursor.fetchall()}

    resultado = []
    d = inicio
    while d <= fin:
        resultado.append({"label": _label_dia(d), "total": rows.get(d, 0)})
        d += timedelta(days=1)
    return resultado


def obtener_ingresos_por_dia_rango(inicio: date, fin: date, id_negocio: str):
    sql = """
        SELECT DATE(pv.fecha_pago) AS dia, COALESCE(SUM(pv.monto), 0) AS total
        FROM pago_venta pv
        JOIN venta v ON v.id_venta = pv.id_venta
        WHERE DATE(pv.fecha_pago) BETWEEN %s AND %s
          AND v.eliminado = 0
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)
    sql += " GROUP BY dia"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["dia"]: float(r["total"]) for r in cursor.fetchall()}

    resultado = []
    d = inicio
    while d <= fin:
        resultado.append({"label": _label_dia(d), "total": rows.get(d, 0.0)})
        d += timedelta(days=1)
    return resultado


def obtener_unidades_por_dia_rango(inicio: date, fin: date, id_negocio: str):
    sql = """
        SELECT DATE(v.fecha_recibo) AS dia, COUNT(a.id_articulo) AS total
        FROM venta v
        JOIN articulo a ON a.id_venta = v.id_venta
        WHERE DATE(v.fecha_recibo) BETWEEN %s AND %s
          AND v.eliminado = 0
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)
    sql += " GROUP BY dia"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["dia"]: int(r["total"]) for r in cursor.fetchall()}

    resultado = []
    d = inicio
    while d <= fin:
        resultado.append({"label": _label_dia(d), "total": rows.get(d, 0)})
        d += timedelta(days=1)
    return resultado


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

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return cursor.fetchall()


def obtener_ventas_con_y_sin_prepago(inicio, fin, id_negocio):
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

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return cursor.fetchall()


def obtener_ventas_por_dia(inicio, fin, id_negocio):
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

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    dias = [0, 0, 0, 0, 0, 0]
    for r in rows:
        dias[r["dia"]] = r["total"]
    return dias


def obtener_ticket_promedio(inicio, fin, id_negocio):
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

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return float(row["promedio"] or 0), int(row["num_ventas"] or 0)


def obtener_saldo_por_cobrar(inicio, fin, id_negocio):
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

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return float(cursor.fetchone()["saldo"] or 0)


def obtener_tiempo_promedio_entrega(inicio, fin, id_negocio):
    sql = """
        SELECT ROUND(AVG(DATEDIFF(fecha_lista, fecha_recibo)), 1) AS dias_promedio,
               COUNT(*) AS ventas_completadas
        FROM venta
        WHERE DATE(fecha_recibo) BETWEEN %s AND %s
          AND fecha_lista IS NOT NULL
          AND eliminado   = 0
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND id_negocio = %s"
        params.append(id_negocio)

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return {
            "dias":        float(row["dias_promedio"] or 0),
            "completadas": int(row["ventas_completadas"] or 0),
        }


def obtener_ingresos_por_negocio(inicio, fin):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT n.nombre, COALESCE(SUM(v.total), 0) AS total
            FROM venta v
            JOIN negocio n ON n.id_negocio = v.id_negocio
            WHERE DATE(v.fecha_recibo) BETWEEN %s AND %s
              AND v.eliminado = 0
            GROUP BY v.id_negocio
            ORDER BY total DESC
        """, [inicio, fin])
        return [{"nombre": r["nombre"], "total": float(r["total"])} for r in cursor.fetchall()]


def obtener_ventas_por_mes(anio, id_negocio):
    sql = """
        SELECT MONTH(fecha_recibo) AS mes, COUNT(*) AS total
        FROM venta
        WHERE YEAR(fecha_recibo) = %s AND eliminado = 0
    """
    params = [anio]
    if id_negocio != "all":
        sql += " AND id_negocio = %s"
        params.append(id_negocio)
    sql += " GROUP BY mes ORDER BY mes"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["mes"]: r["total"] for r in cursor.fetchall()}
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    return [{"label": meses[i], "total": rows.get(i + 1, 0)} for i in range(12)]


def obtener_ingresos_por_mes(anio, id_negocio):
    sql = """
        SELECT MONTH(pv.fecha_pago) AS mes, COALESCE(SUM(pv.monto), 0) AS total
        FROM pago_venta pv
        JOIN venta v ON v.id_venta = pv.id_venta
        WHERE YEAR(pv.fecha_pago) = %s AND v.eliminado = 0
    """
    params = [anio]
    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)
    sql += " GROUP BY mes ORDER BY mes"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["mes"]: float(r["total"]) for r in cursor.fetchall()}
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    return [{"label": meses[i], "total": rows.get(i + 1, 0.0)} for i in range(12)]


def obtener_unidades_por_mes(anio, id_negocio):
    sql = """
        SELECT MONTH(v.fecha_recibo) AS mes,
               COALESCE(
                   (SELECT COUNT(*) FROM articulo a
                    JOIN articulo_calzado ac ON ac.id_articulo = a.id_articulo
                    WHERE a.id_venta = v.id_venta) +
                   (SELECT COALESCE(SUM(ac2.cantidad),0) FROM articulo a2
                    JOIN articulo_confeccion ac2 ON ac2.id_articulo = a2.id_articulo
                    WHERE a2.id_venta = v.id_venta) +
                   (SELECT COALESCE(SUM(am.cantidad),0) FROM articulo a3
                    JOIN articulo_maquila am ON am.id_articulo = a3.id_articulo
                    WHERE a3.id_venta = v.id_venta)
               , 0) AS unidades
        FROM venta v
        WHERE YEAR(v.fecha_recibo) = %s AND v.eliminado = 0
    """
    params = [anio]
    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows_raw = cursor.fetchall()

    acumulado = {}
    for r in rows_raw:
        m = r["mes"]
        acumulado[m] = acumulado.get(m, 0) + int(r["unidades"] or 0)
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    return [{"label": meses[i], "total": acumulado.get(i + 1, 0)} for i in range(12)]


def obtener_metodos_pago(inicio, fin, id_negocio):
    sql = """
        SELECT pv.tipo_pago AS metodo, COUNT(*) AS total, COALESCE(SUM(pv.monto),0) AS monto
        FROM pago_venta pv
        JOIN venta v ON v.id_venta = pv.id_venta
        WHERE DATE(pv.fecha_pago) BETWEEN %s AND %s
          AND v.eliminado = 0
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)
    sql += " GROUP BY pv.tipo_pago ORDER BY total DESC"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return [
            {"metodo": r["metodo"] or "Otro", "total": int(r["total"]), "monto": float(r["monto"])}
            for r in cursor.fetchall()
        ]


def obtener_hora_pico_recepcion(inicio, fin, id_negocio):
    sql = """
        SELECT HOUR(fecha_recibo) AS hora, COUNT(*) AS total
        FROM venta
        WHERE DATE(fecha_recibo) BETWEEN %s AND %s
          AND eliminado = 0
          AND HOUR(fecha_recibo) BETWEEN 7 AND 21
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND id_negocio = %s"
        params.append(id_negocio)
    sql += " GROUP BY hora ORDER BY hora"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["hora"]: r["total"] for r in cursor.fetchall()}
    return [{"hora": f"{h}:00", "total": rows.get(h, 0)} for h in range(7, 22)]


def obtener_hora_pico_entrega(inicio, fin, id_negocio):
    sql = """
        SELECT HOUR(fecha_entrega) AS hora, COUNT(*) AS total
        FROM venta
        WHERE DATE(fecha_entrega) BETWEEN %s AND %s
          AND fecha_entrega IS NOT NULL
          AND eliminado = 0
          AND HOUR(fecha_entrega) BETWEEN 7 AND 21
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND id_negocio = %s"
        params.append(id_negocio)
    sql += " GROUP BY hora ORDER BY hora"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["hora"]: r["total"] for r in cursor.fetchall()}
    return [{"hora": f"{h}:00", "total": rows.get(h, 0)} for h in range(7, 22)]
