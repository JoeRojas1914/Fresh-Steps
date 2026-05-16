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
        num_semana  = actual.isocalendar()[1]   # semana ISO del año (1–53)
        anio        = actual.isocalendar()[0]   # año ISO (puede diferir en sem 52/53)

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

            # Una sola query que suma las unidades de los 3 negocios
            # según el filtro activo, usando UNION ALL internamente
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




_DIAS_CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
_MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun",
                 "jul", "ago", "sep", "oct", "nov", "dic"]

def _label_dia(d: date) -> str:
    return f"{_DIAS_CORTOS[d.weekday()]} {d.day} {_MESES_CORTOS[d.month - 1]}"


def contar_ventas_por_hora(inicio: date, fin: date, id_negocio: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT HOUR(fecha_recibo) AS hora, COUNT(*) AS total
            FROM venta
            WHERE DATE(fecha_recibo) BETWEEN %s AND %s
              AND eliminado = 0
        """
        params = [inicio, fin]
        if id_negocio != "all":
            query += " AND id_negocio = %s"
            params.append(id_negocio)
        query += " GROUP BY hora"
        cursor.execute(query, params)
        rows = {r["hora"]: r["total"] for r in cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()
    return [{"label": f"{h}:00", "total": rows.get(h, 0)} for h in range(7, 22)]


def obtener_ingresos_por_hora(inicio: date, fin: date, id_negocio: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
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
        cursor.execute(sql, params)
        rows = {r["hora"]: float(r["total"]) for r in cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()
    return [{"label": f"{h}:00", "total": rows.get(h, 0.0)} for h in range(7, 22)]


def obtener_unidades_por_hora(inicio: date, fin: date, id_negocio: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
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
        cursor.execute(sql, params)
        rows = {r["hora"]: int(r["total"]) for r in cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()
    return [{"label": f"{h}:00", "total": rows.get(h, 0)} for h in range(7, 22)]


def contar_ventas_por_dia_rango(inicio: date, fin: date, id_negocio: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT DATE(fecha_recibo) AS dia, COUNT(*) AS total
            FROM venta
            WHERE DATE(fecha_recibo) BETWEEN %s AND %s
              AND eliminado = 0
        """
        params = [inicio, fin]
        if id_negocio != "all":
            query += " AND id_negocio = %s"
            params.append(id_negocio)
        query += " GROUP BY dia"
        cursor.execute(query, params)
        rows = {r["dia"]: r["total"] for r in cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()
    resultado = []
    d = inicio
    while d <= fin:
        resultado.append({"label": _label_dia(d), "total": rows.get(d, 0)})
        d += timedelta(days=1)
    return resultado


def obtener_ingresos_por_dia_rango(inicio: date, fin: date, id_negocio: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
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
        cursor.execute(sql, params)
        rows = {r["dia"]: float(r["total"]) for r in cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()
    resultado = []
    d = inicio
    while d <= fin:
        resultado.append({"label": _label_dia(d), "total": rows.get(d, 0.0)})
        d += timedelta(days=1)
    return resultado


def obtener_unidades_por_dia_rango(inicio: date, fin: date, id_negocio: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
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
        cursor.execute(sql, params)
        rows = {r["dia"]: int(r["total"]) for r in cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()
    resultado = []
    d = inicio
    while d <= fin:
        resultado.append({"label": _label_dia(d), "total": rows.get(d, 0)})
        d += timedelta(days=1)
    return resultado


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

def obtener_top_clientes(inicio, fin, id_negocio, limit=5):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

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

    try:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [
            {
                "nombre":        f"{r['nombre']} {r['apellido']}",
                "visitas":       int(r["visitas"] or 0),
                "total_gastado": float(r["total_gastado"] or 0),
            }
            for r in rows
        ]
    finally:
        cursor.close()
        conn.close()


def obtener_tiempo_promedio_entrega(inicio, fin, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

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

    try:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return {
            "dias":      float(row["dias_promedio"] or 0),
            "completadas": int(row["ventas_completadas"] or 0),
        }
    finally:
        cursor.close()
        conn.close()


def obtener_ingresos_por_negocio(inicio, fin):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT n.nombre, COALESCE(SUM(v.total), 0) AS total
            FROM venta v
            JOIN negocio n ON n.id_negocio = v.id_negocio
            WHERE DATE(v.fecha_recibo) BETWEEN %s AND %s
              AND v.eliminado = 0
            GROUP BY v.id_negocio
            ORDER BY total DESC
        """, [inicio, fin])
        rows = cursor.fetchall()
        return [{"nombre": r["nombre"], "total": float(r["total"])} for r in rows]
    finally:
        cursor.close()
        conn.close()


def obtener_ventas_por_mes(anio, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
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
    try:
        cursor.execute(sql, params)
        rows = {r["mes"]: r["total"] for r in cursor.fetchall()}
        meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        return [{"label": meses[i], "total": rows.get(i+1, 0)} for i in range(12)]
    finally:
        cursor.close()
        conn.close()


def obtener_ingresos_por_mes(anio, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
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
    try:
        cursor.execute(sql, params)
        rows = {r["mes"]: float(r["total"]) for r in cursor.fetchall()}
        meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        return [{"label": meses[i], "total": rows.get(i+1, 0.0)} for i in range(12)]
    finally:
        cursor.close()
        conn.close()


def obtener_gastos_por_mes(anio, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
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
    try:
        cursor.execute(sql, params)
        rows = {r["mes"]: float(r["total"]) for r in cursor.fetchall()}
        meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        return [{"label": meses[i], "total": rows.get(i+1, 0.0)} for i in range(12)]
    finally:
        cursor.close()
        conn.close()


def obtener_unidades_por_mes(anio, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
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

    try:
        cursor.execute(sql, params)
        rows_raw = cursor.fetchall()
        acumulado = {}
        for r in rows_raw:
            m = r["mes"]
            acumulado[m] = acumulado.get(m, 0) + int(r["unidades"] or 0)
        meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        return [{"label": meses[i], "total": acumulado.get(i+1, 0)} for i in range(12)]
    finally:
        cursor.close()
        conn.close()


def obtener_metodos_pago(inicio, fin, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
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
    try:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [{"metodo": r["metodo"] or "Otro", "total": int(r["total"]), "monto": float(r["monto"])} for r in rows]
    finally:
        cursor.close()
        conn.close()


def obtener_hora_pico_recepcion(inicio, fin, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
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
    try:
        cursor.execute(sql, params)
        rows = {r["hora"]: r["total"] for r in cursor.fetchall()}
        return [{"hora": f"{h}:00", "total": rows.get(h, 0)} for h in range(7, 22)]
    finally:
        cursor.close()
        conn.close()


def obtener_hora_pico_entrega(inicio, fin, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
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
    try:
        cursor.execute(sql, params)
        rows = {r["hora"]: r["total"] for r in cursor.fetchall()}
        return [{"hora": f"{h}:00", "total": rows.get(h, 0)} for h in range(7, 22)]
    finally:
        cursor.close()
        conn.close()


def obtener_clientes_unicos(inicio, fin, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
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
    try:
        cursor.execute(sql, params)
        return int(cursor.fetchone()["total"] or 0)
    finally:
        cursor.close()
        conn.close()


def obtener_clientes_nuevos(inicio, fin, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
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
    try:
        cursor.execute(sql, params)
        return int(cursor.fetchone()["total"] or 0)
    finally:
        cursor.close()
        conn.close()


def obtener_tasa_retorno(inicio, fin, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
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
    try:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        total      = int(row["total"] or 0)
        recurrentes = int(row["recurrentes"] or 0)
        tasa = round(recurrentes / total * 100, 1) if total > 0 else 0
        return {"total": total, "recurrentes": recurrentes, "tasa": tasa}
    finally:
        cursor.close()
        conn.close()


def obtener_gasto_promedio_cliente(inicio, fin, id_negocio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
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
    try:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        total    = float(row["total_ingresos"] or 0)
        clientes = int(row["clientes_unicos"] or 0)
        return round(total / clientes, 2) if clientes > 0 else 0.0
    finally:
        cursor.close()
        conn.close()