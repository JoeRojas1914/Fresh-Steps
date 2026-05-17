from datetime import date
from db import get_db


def obtener_top_clientes(inicio, fin, id_negocio, limit=5):
    sql = """
        SELECT
            c.id_cliente,
            c.nombre,
            c.apellido,
            COUNT(v.id_venta)  AS visitas,
            SUM(v.total)       AS total_gastado
        FROM venta v
        JOIN cliente c ON c.id_cliente = v.id_cliente
        WHERE DATE(v.fecha_recibo) BETWEEN %s AND %s
          AND v.eliminado = 0
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)
    sql += " GROUP BY c.id_cliente ORDER BY visitas DESC, total_gastado DESC LIMIT %s"
    params.append(limit)

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return [
            {
                "nombre":        f"{r['nombre']} {r['apellido']}",
                "visitas":       int(r["visitas"] or 0),
                "total_gastado": float(r["total_gastado"] or 0),
            }
            for r in cursor.fetchall()
        ]


def obtener_clientes_unicos(inicio, fin, id_negocio):
    sql = """
        SELECT COUNT(DISTINCT id_cliente) AS total
        FROM venta
        WHERE DATE(fecha_recibo) BETWEEN %s AND %s
          AND eliminado = 0
          AND id_cliente IS NOT NULL
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND id_negocio = %s"
        params.append(id_negocio)

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return int(cursor.fetchone()["total"] or 0)


def obtener_clientes_nuevos(inicio, fin, id_negocio):
    sql = """
        SELECT COUNT(DISTINCT v.id_cliente) AS total
        FROM venta v
        WHERE DATE(v.fecha_recibo) BETWEEN %s AND %s
          AND v.eliminado = 0
          AND v.id_cliente IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM venta v2
              WHERE v2.id_cliente = v.id_cliente
                AND v2.eliminado  = 0
                AND v2.fecha_recibo < v.fecha_recibo
          )
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        return int(cursor.fetchone()["total"] or 0)


def obtener_tasa_retorno(inicio, fin, id_negocio):
    sql = """
        SELECT
            COUNT(DISTINCT v.id_cliente) AS total,
            COUNT(DISTINCT CASE
                WHEN EXISTS (
                    SELECT 1 FROM venta v2
                    WHERE v2.id_cliente = v.id_cliente
                      AND v2.eliminado  = 0
                      AND DATE(v2.fecha_recibo) < %s
                ) THEN v.id_cliente
            END) AS recurrentes
        FROM venta v
        WHERE DATE(v.fecha_recibo) BETWEEN %s AND %s
          AND v.eliminado = 0
          AND v.id_cliente IS NOT NULL
    """
    params = [inicio, inicio, fin]
    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        row = cursor.fetchone()
    total       = int(row["total"] or 0)
    recurrentes = int(row["recurrentes"] or 0)
    tasa = round(recurrentes / total * 100, 1) if total > 0 else 0
    return {"total": total, "recurrentes": recurrentes, "tasa": tasa}


def obtener_gasto_promedio_cliente(inicio, fin, id_negocio):
    sql = """
        SELECT
            COALESCE(SUM(v.total), 0)        AS total_ingresos,
            COUNT(DISTINCT v.id_cliente)      AS clientes_unicos
        FROM venta v
        WHERE DATE(v.fecha_recibo) BETWEEN %s AND %s
          AND v.eliminado = 0
          AND v.id_cliente IS NOT NULL
    """
    params = [inicio, fin]
    if id_negocio != "all":
        sql += " AND v.id_negocio = %s"
        params.append(id_negocio)

    with get_db() as (_, cursor):
        cursor.execute(sql, params)
        row = cursor.fetchone()
    total    = float(row["total_ingresos"] or 0)
    clientes = int(row["clientes_unicos"] or 0)
    return round(total / clientes, 2) if clientes > 0 else 0.0
