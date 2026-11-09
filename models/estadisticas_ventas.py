from collections import defaultdict
from datetime import date, timedelta
from db import get_db
from utils import filtro_negocios, sql_negocios

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


def generar_periodos(inicio: date, fin: date, periodo: str = "semana"):
    """Cubetas del rango: [{"inicio", "label", "clave"}].

    `clave` coincide con `_expr_periodo` en SQL: año*100+semana ISO para "semana",
    año*100+mes para "mes".
    """
    if periodo == "mes":
        meses = []
        actual = inicio.replace(day=1)
        while actual <= fin:
            meses.append({
                "inicio": actual,
                "label":  f"{_MESES_CORTOS[actual.month - 1]} {actual.year}",
                "clave":  actual.year * 100 + actual.month,
            })
            actual = date(actual.year + (actual.month == 12), actual.month % 12 + 1, 1)
        return meses

    return [
        {**s, "clave": s["inicio"].isocalendar()[0] * 100 + s["inicio"].isocalendar()[1]}
        for s in generar_semanas_rango(inicio, fin)
    ]


def _expr_periodo(col: str, periodo: str = "semana") -> str:
    """Expresión SQL de la clave de cubeta (ver `generar_periodos`). `col` ya validada."""
    if periodo == "mes":
        return f"EXTRACT(YEAR_MONTH FROM {col})"
    return f"YEARWEEK({col}, 1)"


def contar_ventas_por_semana(inicio: date, fin: date, id_negocio: str, col: str = "fecha_recibo",
                             periodo: str = "semana"):
    col = _col_v(col)
    semanas = generar_periodos(inicio, fin, periodo)

    sql = f"""
        SELECT {_expr_periodo(col, periodo)} AS yw, COUNT(*) AS total
        FROM venta
        WHERE {col} >= %s
          AND {col} < DATE_ADD(%s, INTERVAL 1 DAY)
          AND eliminado = 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "id_negocio")
    sql += " GROUP BY yw"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["yw"]: r["total"] for r in cursor.fetchall()}

    return [{"label": s["label"], "total": rows.get(s["clave"], 0)} for s in semanas]


def obtener_unidades_por_semana(inicio: date, fin: date, id_negocio: str, col: str = "fecha_recibo",
                                periodo: str = "semana"):
    col = _col_v(col)
    semanas = generar_periodos(inicio, fin, periodo)
    expr    = _expr_periodo(f"v.{col}", periodo)
    totals: defaultdict = defaultdict(int)

    with get_db() as (_, cursor):
        if id_negocio in ("1", "all"):
            cursor.execute(f"""
                SELECT {expr} AS yw, COUNT(a.id_articulo) AS u
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
                SELECT {expr} AS yw, COALESCE(SUM(ac2.cantidad), 0) AS u
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
                SELECT {expr} AS yw, COALESCE(SUM(am.cantidad), 0) AS u
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

    return [{"label": s["label"], "total": totals[s["clave"]]} for s in semanas]


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
    sql += sql_negocios(params, id_negocio, "v.id_negocio")

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return float(cursor.fetchone()["total"] or 0)


def obtener_ingresos_por_semana(inicio, fin, id_negocio, periodo: str = "semana"):
    semanas = generar_periodos(inicio, fin, periodo)

    sql = f"""
        SELECT {_expr_periodo("pv.fecha_pago", periodo)} AS yw, COALESCE(SUM(pv.monto), 0) AS total
        FROM pago_venta pv
        JOIN venta v ON v.id_venta = pv.id_venta
        WHERE pv.fecha_pago >= %s
          AND pv.fecha_pago < DATE_ADD(%s, INTERVAL 1 DAY)
          AND v.eliminado = 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "v.id_negocio")
    sql += " GROUP BY yw"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["yw"]: float(r["total"]) for r in cursor.fetchall()}

    return [{"label": s["label"], "total": rows.get(s["clave"], 0.0)} for s in semanas]


def contar_ventas_por_hora(inicio: date, fin: date, id_negocio: str, col: str = "fecha_recibo"):
    col = _col_v(col)
    sql = f"""
        SELECT HOUR({col}) AS hora, COUNT(*) AS total
        FROM venta
        WHERE {col} >= %s AND {col} < DATE_ADD(%s, INTERVAL 1 DAY)
          AND eliminado = 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "id_negocio")
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
        WHERE pv.fecha_pago >= %s AND pv.fecha_pago < DATE_ADD(%s, INTERVAL 1 DAY)
          AND v.eliminado = 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "v.id_negocio")
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
        WHERE v.{col} >= %s AND v.{col} < DATE_ADD(%s, INTERVAL 1 DAY)
          AND v.eliminado = 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "v.id_negocio")
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
        WHERE {col} >= %s AND {col} < DATE_ADD(%s, INTERVAL 1 DAY)
          AND eliminado = 0
    """
    sql_neg, params_neg = filtro_negocios(id_negocio)
    sql += sql_neg
    params = [inicio, fin] + params_neg
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


def contar_unidades_por_dia_rango(inicio: date, fin: date, id_negocio="all"):
    """Artículos recibidos por día (por fecha de recibo), con los días vacíos en 0."""
    sql = """
        SELECT DATE(v.fecha_recibo) AS dia, COUNT(a.id_articulo) AS total
        FROM venta v
        JOIN articulo a ON a.id_venta = v.id_venta
        WHERE v.fecha_recibo >= %s AND v.fecha_recibo < DATE_ADD(%s, INTERVAL 1 DAY)
          AND v.eliminado = 0
    """
    sql_neg, params_neg = filtro_negocios(id_negocio, "v.id_negocio")
    sql += sql_neg + " GROUP BY dia"

    with get_db() as (_, cursor):
        cursor.execute(sql, [inicio, fin] + params_neg)
        rows = {r["dia"]: int(r["total"]) for r in cursor.fetchall()}

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
        WHERE pv.fecha_pago >= %s AND pv.fecha_pago < DATE_ADD(%s, INTERVAL 1 DAY)
          AND v.eliminado = 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "v.id_negocio")
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
        WHERE v.{col} >= %s AND v.{col} < DATE_ADD(%s, INTERVAL 1 DAY)
          AND v.eliminado = 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "v.id_negocio")
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
        WHERE v.{col} >= %s AND v.{col} < DATE_ADD(%s, INTERVAL 1 DAY)
          AND v.eliminado = 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "v.id_negocio")
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
        WHERE v.{col} >= %s AND v.{col} < DATE_ADD(%s, INTERVAL 1 DAY)
          AND v.eliminado = 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "v.id_negocio")
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
        WHERE {col} >= %s AND {col} < DATE_ADD(%s, INTERVAL 1 DAY)
          AND WEEKDAY({col}) BETWEEN 0 AND 5
          AND eliminado = 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "id_negocio")
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
        WHERE {col} >= %s AND {col} < DATE_ADD(%s, INTERVAL 1 DAY)
          AND eliminado = 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "id_negocio")

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
        WHERE v.{col} >= %s AND v.{col} < DATE_ADD(%s, INTERVAL 1 DAY)
          AND v.eliminado = 0
          AND (v.total - COALESCE(p.pagado, 0)) > 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "v.id_negocio")

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return float(cursor.fetchone()["saldo"] or 0)


def obtener_tiempo_promedio_entrega(inicio, fin, id_negocio):
    sql = """
        SELECT ROUND(AVG(DATEDIFF(fecha_lista, fecha_recibo)), 1) AS dias_promedio,
               COUNT(*) AS ventas_completadas
        FROM venta
        WHERE fecha_recibo >= %s AND fecha_recibo < DATE_ADD(%s, INTERVAL 1 DAY)
          AND fecha_lista IS NOT NULL
          AND eliminado   = 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "id_negocio")

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return {
            "dias":        float(row["dias_promedio"] or 0),
            "completadas": int(row["ventas_completadas"] or 0),
        }


# `venta.total` se guarda con el descuento ya restado (ver crear_venta); el precio
# original de la venta es total + descuento.
_DESCUENTO_SQL = "CASE WHEN {t}aplica_descuento = 1 THEN {t}cantidad_descuento ELSE 0 END"


def obtener_ventas_brutas(inicio, fin, id_negocio):
    """Total de ventas antes de descuentos y total de descuentos de las ventas recibidas
    en el rango: {"total_ventas", "descuentos"}.

    Si un descuento fue mayor que el precio, la venta quedó en $0 y aquí se cuenta el
    descuento completo (no se guarda el subtotal para recortarlo)."""
    descuento = _DESCUENTO_SQL.format(t="")
    sql = f"""
        SELECT COALESCE(SUM(total + {descuento}), 0) AS total_ventas,
               COALESCE(SUM({descuento}), 0)         AS descuentos
        FROM venta
        WHERE fecha_recibo >= %s AND fecha_recibo < DATE_ADD(%s, INTERVAL 1 DAY)
          AND eliminado = 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "id_negocio")

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return {"total_ventas": float(row["total_ventas"] or 0),
                "descuentos":   float(row["descuentos"] or 0)}


def obtener_vendido_serie(inicio: date, fin: date, id_negocio, granularidad: str = "semana"):
    """Total de ventas (antes de descuentos) en el tiempo, por fecha de recibo:
    [{"label", "total"}] con las mismas cubetas y etiquetas que las demás series
    (hora 7–21, día, semana ISO o mes)."""
    if granularidad == "hora":
        clave = "HOUR(fecha_recibo)"
    elif granularidad == "dia":
        clave = "DATE(fecha_recibo)"
    else:
        clave = _expr_periodo("fecha_recibo", "mes" if granularidad == "mes" else "semana")

    sql = f"""
        SELECT {clave} AS clave, COALESCE(SUM(total + {_DESCUENTO_SQL.format(t="")}), 0) AS total
        FROM venta
        WHERE fecha_recibo >= %s AND fecha_recibo < DATE_ADD(%s, INTERVAL 1 DAY)
          AND eliminado = 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "id_negocio")
    sql += " GROUP BY clave"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["clave"]: float(r["total"]) for r in cursor.fetchall()}

    if granularidad == "hora":
        return [{"label": f"{h}:00", "total": rows.get(h, 0.0)} for h in range(7, 22)]
    if granularidad == "dia":
        dias = [inicio + timedelta(days=i) for i in range((fin - inicio).days + 1)]
        return [{"label": _label_dia(d), "total": rows.get(d, 0.0)} for d in dias]
    periodos = generar_periodos(inicio, fin, "mes" if granularidad == "mes" else "semana")
    return [{"label": p["label"], "total": rows.get(p["clave"], 0.0)} for p in periodos]


def obtener_ingresos_por_negocio(inicio, fin, col: str = "fecha_recibo"):
    """Total vendido por negocio, antes de descuentos (mismo criterio que "Total de ventas")."""
    col = _col_v(col)
    with get_db() as (_, cursor):
        cursor.execute(f"""
            SELECT v.id_negocio, n.nombre,
                   COALESCE(SUM(v.total + {_DESCUENTO_SQL.format(t="v.")}), 0) AS total
            FROM venta v
            JOIN negocio n ON n.id_negocio = v.id_negocio
            WHERE v.{col} >= %s AND v.{col} < DATE_ADD(%s, INTERVAL 1 DAY)
              AND v.eliminado = 0
            GROUP BY v.id_negocio
            ORDER BY total DESC
        """, [inicio, fin])
        return [
            {"id_negocio": int(r["id_negocio"]), "nombre": r["nombre"], "total": float(r["total"])}
            for r in cursor.fetchall()
        ]


def obtener_metodos_pago(inicio, fin, id_negocio):
    sql = """
        SELECT pv.tipo_pago AS metodo, COUNT(*) AS total, COALESCE(SUM(pv.monto),0) AS monto
        FROM pago_venta pv
        JOIN venta v ON v.id_venta = pv.id_venta
        WHERE pv.fecha_pago >= %s AND pv.fecha_pago < DATE_ADD(%s, INTERVAL 1 DAY)
          AND v.eliminado = 0
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "v.id_negocio")
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
        WHERE fecha_recibo >= %s AND fecha_recibo < DATE_ADD(%s, INTERVAL 1 DAY)
          AND eliminado = 0
          AND HOUR(fecha_recibo) BETWEEN 7 AND 21
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "id_negocio")
    sql += " GROUP BY hora ORDER BY hora"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["hora"]: r["total"] for r in cursor.fetchall()}
    return [{"hora": f"{h}:00", "total": rows.get(h, 0)} for h in range(7, 22)]


def obtener_hora_pico_entrega(inicio, fin, id_negocio):
    sql = """
        SELECT HOUR(fecha_entrega) AS hora, COUNT(*) AS total
        FROM venta
        WHERE fecha_entrega >= %s AND fecha_entrega < DATE_ADD(%s, INTERVAL 1 DAY)
          AND fecha_entrega IS NOT NULL
          AND eliminado = 0
          AND HOUR(fecha_entrega) BETWEEN 7 AND 21
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "id_negocio")
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
        WHERE v.{col} >= %s AND v.{col} < DATE_ADD(%s, INTERVAL 1 DAY)
          AND v.eliminado = 0
    """
    hoy = date.today()
    sql_neg, params_neg = filtro_negocios(id_negocio, "v.id_negocio")
    sql += sql_neg
    params = [hoy, hoy] + params_neg
    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return int(cursor.fetchone()["total"] or 0)


def contar_ventas_entregadas_hoy(id_negocio: str = "all") -> int:
    sql = """
        SELECT COUNT(*) AS total
        FROM venta v
        WHERE v.fecha_entrega >= %s AND v.fecha_entrega < DATE_ADD(%s, INTERVAL 1 DAY)
          AND v.eliminado = 0
    """
    hoy = date.today()
    sql_neg, params_neg = filtro_negocios(id_negocio, "v.id_negocio")
    sql += sql_neg
    params = [hoy, hoy] + params_neg
    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return int(cursor.fetchone()["total"] or 0)


_CAMPOS_CALZADO = {"marca": "Sin marca", "tipo": "Sin tipo"}


def obtener_top_calzado(inicio: date, fin: date, campo: str, limit: int | None = None):
    """Marcas o tipos de calzado que más llegan en el rango: [{"nombre", "total"}].

    Sin `limit` devuelve todos los nombres, para que el servicio pueda unir las
    variantes mal escritas antes de recortar el top.
    """
    if campo not in _CAMPOS_CALZADO:
        raise ValueError(f"campo no permitido: {campo}")
    sql = f"""
        SELECT COALESCE(NULLIF(TRIM(ac.{campo}), ''), %s) AS nombre, COUNT(*) AS total
        FROM articulo_calzado ac
        JOIN articulo a ON a.id_articulo = ac.id_articulo
        JOIN venta v    ON v.id_venta    = a.id_venta
        WHERE v.fecha_recibo >= %s AND v.fecha_recibo < DATE_ADD(%s, INTERVAL 1 DAY)
          AND v.id_negocio = 1
          AND v.eliminado  = 0
        GROUP BY nombre
        ORDER BY total DESC, nombre
    """
    params = [_CAMPOS_CALZADO[campo], inicio, fin]
    if limit is not None:
        sql += " LIMIT %s"
        params.append(int(limit))
    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return [{"nombre": r["nombre"], "total": int(r["total"])} for r in cursor.fetchall()]


def obtener_primer_anio_ventas():
    """Año de la venta más antigua, o None si no hay ventas."""
    with get_db() as (_, cursor):
        cursor.execute("SELECT YEAR(MIN(fecha_recibo)) AS anio FROM venta WHERE eliminado = 0")
        row = cursor.fetchone()
        return int(row["anio"]) if row and row["anio"] else None
