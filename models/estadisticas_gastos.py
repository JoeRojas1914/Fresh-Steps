from collections import defaultdict
from datetime import date
from db import get_db
from utils import sql_negocios
from .estadisticas_ventas import generar_periodos, _expr_periodo


def obtener_gastos_por_semana_y_proveedor(inicio: date, fin: date, id_negocio: str,
                                          periodo: str = "semana"):
    semanas = generar_periodos(inicio, fin, periodo)
    data_por_proveedor = defaultdict(lambda: [0.0] * len(semanas))

    yw_to_idx = {s["clave"]: i for i, s in enumerate(semanas)}

    sql = f"""
        SELECT {_expr_periodo("fecha_registro", periodo)} AS yw, proveedor, SUM(total) AS total
        FROM gastos
        WHERE fecha_registro >= %s
          AND fecha_registro <= %s
          AND activo = 1
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "id_negocio")
    sql += " GROUP BY yw, proveedor"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        for r in cursor.fetchall():
            idx = yw_to_idx.get(r["yw"])
            if idx is not None:
                proveedor = r["proveedor"] or "Sin proveedor"
                data_por_proveedor[proveedor][idx] = float(r["total"] or 0)

    return {
        "labels":   [s["label"] for s in semanas],
        "datasets": [{"label": p, "data": v} for p, v in data_por_proveedor.items()],
    }


def obtener_gastos_por_semana_y_categoria(inicio: date, fin: date, id_negocio: str,
                                          periodo: str = "semana"):
    semanas = generar_periodos(inicio, fin, periodo)
    data_por_cat = defaultdict(lambda: [0.0] * len(semanas))

    yw_to_idx = {s["clave"]: i for i, s in enumerate(semanas)}

    sql = f"""
        SELECT {_expr_periodo("g.fecha_registro", periodo)} AS yw,
               COALESCE(c.nombre, 'Sin categoría') AS categoria,
               SUM(g.total) AS total
        FROM gastos g
        LEFT JOIN categoria_gasto c ON g.id_categoria = c.id_categoria
        WHERE g.fecha_registro >= %s
          AND g.fecha_registro <= %s
          AND g.activo = 1
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "g.id_negocio")
    sql += " GROUP BY yw, c.id_categoria, c.nombre"

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        for r in cursor.fetchall():
            idx = yw_to_idx.get(r["yw"])
            if idx is not None:
                data_por_cat[r["categoria"]][idx] = float(r["total"] or 0)

    return {
        "labels":   [s["label"] for s in semanas],
        "datasets": [{"label": c, "data": v} for c, v in data_por_cat.items()],
    }


def obtener_total_gastos(inicio: date, fin: date, id_negocio: str):
    sql = """
        SELECT COALESCE(SUM(total), 0) AS total
        FROM gastos
        WHERE fecha_registro >= %s
          AND fecha_registro <= %s
          AND activo = 1
    """
    params = [inicio, fin]
    sql += sql_negocios(params, id_negocio, "id_negocio")

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return float(cursor.fetchone()["total"] or 0)


