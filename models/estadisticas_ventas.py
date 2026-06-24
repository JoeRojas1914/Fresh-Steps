from collections import defaultdict
from datetime import date, timedelta
from db import get_db

_COLS_FECHA: dict[str, str] = {
    "fecha_recibo":  "fecha_recibo",
    "fecha_entrega": "fecha_entrega",
}


def _col_v(col: str) -> str:
    return _COLS_FECHA.get(col, "fecha_recibo")


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


def contar_ventas_por_semana(inicio: date, fin: date, id_negocio: str, col: str = "fecha_recibo"):
    col = _col_v(col)
    semanas = generar_semanas_rango(inicio, fin)

    sql = f"""
        SELECT YEARWEEK({col}, 1) AS yw, COUNT(*) AS total
        FROM venta
        WHERE {col} >= %s
          AND {col} < DATE_ADD(%s, INTERVAL 1 DAY)
          AND eliminado = 0
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND id_negocio = %s"
        params.append(id_negocio)
    sql += " GROUP BY yw"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["yw"]: r["total"] for r in cursor.fetchall()}

    return [
        {
            "label": s["label"],
            "total": rows.get(s["inicio"].isocalendar()[0] * 100 + s["inicio"].isocalendar()[1], 0),
        }
        for s in semanas
    ]


def obtener_unidades_por_semana(inicio: date, fin: date, id_negocio: str, col: str = "fecha_recibo"):
    col = _col_v(col)
    semanas = generar_semanas_rango(inicio, fin)
    totals: defaultdict = defaultdict(int)

    with get_db() as (_, cursor):
        if id_negocio in ("1", "all"):
            cursor.execute(f"""
                SELECT YEARWEEK(v.{col}, 1) AS yw, COUNT(a.id_articulo) AS u
                FROM venta v
                JOIN articulo a          ON a.id_venta     = v.id_venta
                JOIN articulo_calzado ac ON ac.id_articulo = a.id_articulo
                WHERE v.{col} >= %s
                  AND v.{col} <  DATE_ADD(%s, INTERVAL 1 DAY)
                  AND v.id_negocio = 1
                  AND v.eliminado  = 0
                GROUP BY yw
            """, (inicio, fin))
            for r in cursor.fetchall():
                totals[r["yw"]] += int(r["u"] or 0)

        if id_negocio in ("2", "all"):
            cursor.execute(f"""
                SELECT YEARWEEK(v.{col}, 1) AS yw, COALESCE(SUM(ac2.cantidad), 0) AS u
                FROM venta v
                JOIN articulo a              ON a.id_venta      = v.id_venta
                JOIN articulo_confeccion ac2 ON ac2.id_articulo = a.id_articulo
                WHERE v.{col} >= %s
                  AND v.{col} <  DATE_ADD(%s, INTERVAL 1 DAY)
                  AND v.id_negocio = 2
                  AND v.eliminado  = 0
                GROUP BY yw
            """, (inicio, fin))
            for r in cursor.fetchall():
                totals[r["yw"]] += int(r["u"] or 0)

        if id_negocio in ("3", "all"):
            cursor.execute(f"""
                SELECT YEARWEEK(v.{col}, 1) AS yw, COALESCE(SUM(am.cantidad), 0) AS u
                FROM venta v
                JOIN articulo a          ON a.id_venta     = v.id_venta
                JOIN articulo_maquila am ON am.id_articulo = a.id_articulo
                WHERE v.{col} >= %s
                  AND v.{col} <  DATE_ADD(%s, INTERVAL 1 DAY)
                  AND v.id_negocio = 3
                  AND v.eliminado  = 0
                GROUP BY yw
            """, (inicio, fin))
            for r in cursor.fetchall():
                totals[r["yw"]] += int(r["u"] or 0)

    return [
        {
            "label": s["label"],
            "total": totals[s["inicio"].isocalendar()[0] * 100 + s["inicio"].isocalendar()[1]],
        }
        for s in semanas
    ]


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

    sql = """
        SELECT YEARWEEK(pv.fecha_pago, 1) AS yw, COALESCE(SUM(pv.monto), 0) AS total
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
    sql += " GROUP BY yw"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["yw"]: float(r["total"]) for r in cursor.fetchall()}

    return [
        {
            "label": s["label"],
            "total": rows.get(
                s["inicio"].isocalendar()[0] * 100 + s["inicio"].isocalendar()[1], 0.0
            ),
        }
        for s in semanas
    ]


def contar_ventas_por_hora(inicio: date, fin: date, id_negocio: str, col: str = "fecha_recibo"):
    col = _col_v(col)
    sql = f"""
        SELECT HOUR({col}) AS hora, COUNT(*) AS total
        FROM venta
        WHERE DATE({col}) BETWEEN %s AND %s
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


def obtener_unidades_por_hora(inicio: date, fin: date, id_negocio: str, col: str = "fecha_recibo"):
    col = _col_v(col)
    sql = f"""
        SELECT HOUR(v.{col}) AS hora, COUNT(a.id_articulo) AS total
        FROM venta v
        JOIN articulo a ON a.id_venta = v.id_venta
        WHERE DATE(v.{col}) BETWEEN %s AND %s
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


def contar_ventas_por_dia_rango(inicio: date, fin: date, id_negocio: str, col: str = "fecha_recibo"):
    col = _col_v(col)
    sql = f"""
        SELECT DATE({col}) AS dia, COUNT(*) AS total
        FROM venta
        WHERE DATE({col}) BETWEEN %s AND %s
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


def obtener_unidades_por_dia_rango(inicio: date, fin: date, id_negocio: str, col: str = "fecha_recibo"):
    col = _col_v(col)
    sql = f"""
        SELECT DATE(v.{col}) AS dia, COUNT(a.id_articulo) AS total
        FROM venta v
        JOIN articulo a ON a.id_venta = v.id_venta
        WHERE DATE(v.{col}) BETWEEN %s AND %s
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


def obtener_uso_servicios(inicio, fin, id_negocio, col: str = "fecha_recibo"):
    col = _col_v(col)
    sql = f"""
        SELECT s.nombre, COUNT(*) total
        FROM articulo_servicio aps
        JOIN servicio s ON s.id_servicio = aps.id_servicio
        JOIN articulo a ON a.id_articulo = aps.id_articulo
        JOIN venta v ON v.id_venta = a.id_venta
        WHERE DATE(v.{col}) BETWEEN %s AND %s
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


def obtener_ventas_con_y_sin_prepago(inicio, fin, id_negocio, col: str = "fecha_recibo"):
    col = _col_v(col)
    sql = f"""
        SELECT
            CASE WHEN pv_pre.id_venta IS NOT NULL THEN 'Con prepago' ELSE 'Sin prepago' END AS tipo,
            COUNT(*) AS total
        FROM venta v
        LEFT JOIN (
            SELECT DISTINCT id_venta
            FROM pago_venta
            WHERE tipo_pago_venta = 'prepago'
        ) pv_pre ON pv_pre.id_venta = v.id_venta
        WHERE DATE(v.{col}) BETWEEN %s AND %s
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


def obtener_ventas_por_dia(inicio, fin, id_negocio, col: str = "fecha_recibo"):
    col = _col_v(col)
    sql = f"""
        SELECT
            WEEKDAY({col}) AS dia,
            COUNT(*) AS total
        FROM venta
        WHERE DATE({col}) BETWEEN %s AND %s
          AND WEEKDAY({col}) BETWEEN 0 AND 5
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


def obtener_ticket_promedio(inicio, fin, id_negocio, col: str = "fecha_recibo"):
    col = _col_v(col)
    sql = f"""
        SELECT COALESCE(AVG(total), 0) AS promedio,
               COUNT(*)               AS num_ventas
        FROM venta
        WHERE DATE({col}) BETWEEN %s AND %s
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


def obtener_saldo_por_cobrar(inicio, fin, id_negocio, col: str = "fecha_recibo"):
    col = _col_v(col)
    sql = f"""
        SELECT COALESCE(
            SUM(v.total - COALESCE(p.pagado, 0)), 0
        ) AS saldo
        FROM venta v
        LEFT JOIN (
            SELECT id_venta, SUM(monto) AS pagado
            FROM pago_venta
            GROUP BY id_venta
        ) p ON p.id_venta = v.id_venta
        WHERE DATE(v.{col}) BETWEEN %s AND %s
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


def obtener_ingresos_por_negocio(inicio, fin, col: str = "fecha_recibo"):
    col = _col_v(col)
    with get_db() as (_, cursor):
        cursor.execute(f"""
            SELECT n.nombre, COALESCE(SUM(v.total), 0) AS total
            FROM venta v
            JOIN negocio n ON n.id_negocio = v.id_negocio
            WHERE DATE(v.{col}) BETWEEN %s AND %s
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
    meses_labels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    totals: defaultdict = defaultdict(int)

    with get_db() as (_, cursor):
        if id_negocio in ("1", "all"):
            cursor.execute("""
                SELECT MONTH(v.fecha_recibo) AS mes, COUNT(a.id_articulo) AS u
                FROM venta v
                JOIN articulo a          ON a.id_venta     = v.id_venta
                JOIN articulo_calzado ac ON ac.id_articulo = a.id_articulo
                WHERE YEAR(v.fecha_recibo) = %s AND v.eliminado = 0 AND v.id_negocio = 1
                GROUP BY mes
            """, [anio])
            for r in cursor.fetchall():
                totals[r["mes"]] += int(r["u"] or 0)

        if id_negocio in ("2", "all"):
            cursor.execute("""
                SELECT MONTH(v.fecha_recibo) AS mes, COALESCE(SUM(ac2.cantidad), 0) AS u
                FROM venta v
                JOIN articulo a              ON a.id_venta      = v.id_venta
                JOIN articulo_confeccion ac2 ON ac2.id_articulo = a.id_articulo
                WHERE YEAR(v.fecha_recibo) = %s AND v.eliminado = 0 AND v.id_negocio = 2
                GROUP BY mes
            """, [anio])
            for r in cursor.fetchall():
                totals[r["mes"]] += int(r["u"] or 0)

        if id_negocio in ("3", "all"):
            cursor.execute("""
                SELECT MONTH(v.fecha_recibo) AS mes, COALESCE(SUM(am.cantidad), 0) AS u
                FROM venta v
                JOIN articulo a          ON a.id_venta     = v.id_venta
                JOIN articulo_maquila am ON am.id_articulo = a.id_articulo
                WHERE YEAR(v.fecha_recibo) = %s AND v.eliminado = 0 AND v.id_negocio = 3
                GROUP BY mes
            """, [anio])
            for r in cursor.fetchall():
                totals[r["mes"]] += int(r["u"] or 0)

    return [{"label": meses_labels[i], "total": totals[i + 1]} for i in range(12)]


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


def contar_unidades_hoy(col: str = "fecha_recibo", id_negocio: str = "all") -> int:
    col = _col_v(col)
    sql = f"""
        SELECT COUNT(a.id_articulo) AS total
        FROM venta v
        JOIN articulo a ON a.id_venta = v.id_venta
        WHERE DATE(v.{col}) = CURDATE()
          AND v.eliminado = 0
    """
    params = []
    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)
    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return int(cursor.fetchone()["total"] or 0)
