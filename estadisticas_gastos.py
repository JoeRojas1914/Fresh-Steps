from collections import defaultdict
from datetime import date
from db import get_db
from estadisticas_ventas import generar_semanas_rango


def obtener_gastos_por_semana_y_proveedor(inicio: date, fin: date, id_negocio: str):
    semanas = generar_semanas_rango(inicio, fin)
    data_por_proveedor = defaultdict(lambda: [0] * len(semanas))

    with get_db() as (_, cursor):
        for i, s in enumerate(semanas):
            semana_inicio_real = max(s["inicio"], inicio)
            semana_fin_real    = min(s["fin"],    fin)

            sql = """
                SELECT proveedor, SUM(total) AS total
                FROM gastos
                WHERE fecha_registro >= %s
                  AND fecha_registro <= %s
            """
            params = [semana_inicio_real, semana_fin_real]

            if id_negocio != "all":
                sql += " AND id_negocio = %s"
                params.append(id_negocio)

            sql += " GROUP BY proveedor"
            cursor.execute(sql, params)

            for r in cursor.fetchall():
                proveedor = r["proveedor"] or "Sin proveedor"
                data_por_proveedor[proveedor][i] = float(r["total"] or 0)

    labels   = [s["label"] for s in semanas]
    datasets = [{"label": p, "data": v} for p, v in data_por_proveedor.items()]
    return {"labels": labels, "datasets": datasets}


def obtener_total_gastos(inicio: date, fin: date, id_negocio: str):
    sql = """
        SELECT COALESCE(SUM(total), 0) AS total
        FROM gastos
        WHERE fecha_registro >= %s
          AND fecha_registro <= %s
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND id_negocio = %s"
        params.append(id_negocio)

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return float(cursor.fetchone()["total"] or 0)


def obtener_gastos_por_mes(anio, id_negocio):
    sql = """
        SELECT MONTH(fecha_registro) AS mes, COALESCE(SUM(total), 0) AS total
        FROM gastos
        WHERE YEAR(fecha_registro) = %s AND activo = 1
    """
    params = [anio]
    if id_negocio != "all":
        sql += " AND id_negocio = %s"
        params.append(id_negocio)
    sql += " GROUP BY mes ORDER BY mes"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        rows = {r["mes"]: float(r["total"]) for r in cursor.fetchall()}
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    return [{"label": meses[i], "total": rows.get(i + 1, 0.0)} for i in range(12)]
