import json
from decimal import Decimal
from datetime import date, datetime


def to_json_safe(data):
    if not data:
        return None
    safe = {}
    for k, v in data.items():
        if isinstance(v, Decimal):
            safe[k] = float(v)
        elif isinstance(v, (date, datetime)):
            safe[k] = v.isoformat()
        else:
            safe[k] = v
    return safe


def build_where(filters):
    """Each filter: (condition_sql, val1, val2, ...) — included if val1 is not None."""
    clauses, params = [], []
    for item in filters:
        condition = item[0]
        values = item[1:]
        if values and values[0] is not None:
            clauses.append(condition)
            params.extend(values)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def cond_in(columna, valores):
    """Filtro para build_where: `columna IN (...)` con uno o varios valores.

    None, "" o una lista vacía = sin filtro."""
    if valores is None:
        return ("", None)
    if not isinstance(valores, (list, tuple, set)):
        valores = [valores]
    valores = [v for v in valores if v not in (None, "")]
    if not valores:
        return ("", None)
    return (f"{columna} IN ({', '.join(['%s'] * len(valores))})", *valores)


def filtro_negocios(id_negocio, columna="id_negocio"):
    """Filtro SQL por negocio: regresa (sql, params).

    "all" o None = sin filtro; un id o una lista de ids = `AND columna IN (...)`."""
    if id_negocio == "all" or id_negocio is None:
        return "", []
    ids = list(id_negocio) if isinstance(id_negocio, (list, tuple, set)) else [id_negocio]
    return f" AND {columna} IN ({', '.join(['%s'] * len(ids))})", ids


def sql_negocios(params, id_negocio, columna="id_negocio"):
    """Igual que filtro_negocios, pero agrega los valores a `params` y regresa solo el SQL."""
    sql, valores = filtro_negocios(id_negocio, columna)
    params.extend(valores)
    return sql


def ids_de_args(args, clave="id_negocio"):
    """Lista de IDs enteros de un parámetro repetible (?id_negocio=1&id_negocio=3)."""
    return [int(v) for v in args.getlist(clave) if str(v).strip().isdigit()]


def nombres_negocios(ids, negocios):
    """'Calzado, Maquila' para los IDs dados (para subtítulos de Excel)."""
    return ", ".join(n["nombre"] for n in negocios if n["id_negocio"] in (ids or []))


COLUMNAS_ORDEN_VENTAS = {
    "id":             "v.id_venta",
    "cliente":        "CONCAT(c.nombre, ' ', c.apellido)",
    "fecha_recibo":   "v.fecha_recibo",
    "fecha_estimada": "v.fecha_estimada",
    "fecha_lista":    "v.fecha_lista",
    "fecha_entrega":  "v.fecha_entrega",
    "negocio":        "n.nombre",
    "total":          "v.total",
}


def construir_order_by(
    orden,
    direccion,
    default: str,
    columnas: dict = COLUMNAS_ORDEN_VENTAS,
    desempate: str = "v.id_venta",
) -> str:
    """Devuelve la cláusula ORDER BY. `orden` solo se acepta si está en la lista
    blanca `columnas`; si no, se usa `default`. Los NULL van siempre al final y
    `desempate` (la PK) mantiene un orden estable entre páginas."""
    expr = columnas.get(orden)
    if not expr:
        return f" ORDER BY {default}"
    dir_sql = "DESC" if direccion == "desc" else "ASC"
    return f" ORDER BY {expr} IS NULL, {expr} {dir_sql}, {desempate} {dir_sql}"


def calcular_paginacion(total: int, pagina: int, por_pagina: int) -> tuple[int, int]:
    """Devuelve (offset, total_paginas). Garantiza mínimo 1 página."""
    offset        = (pagina - 1) * por_pagina
    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)
    return offset, total_paginas


def registrar_historial(
    cursor, tabla, campo_id, id_entidad, accion, id_usuario, antes=None, despues=None
):
    cursor.execute(
        f"INSERT INTO {tabla} ({campo_id}, accion, id_usuario, datos_antes, datos_despues)"
        " VALUES (%s, %s, %s, %s, %s)",
        (id_entidad, accion, id_usuario,
         json.dumps(to_json_safe(antes)) if antes else None,
         json.dumps(to_json_safe(despues)) if despues else None)
    )


# ── Formatos para las plantillas (registrados en app.py) ──────────────────────
_MESES_CORTOS = ("ene", "feb", "mar", "abr", "may", "jun",
                 "jul", "ago", "sep", "oct", "nov", "dic")


def dinero(valor):
    """$1,234.50 — siempre 2 decimales y separador de miles."""
    try:
        n = float(valor or 0)
    except (TypeError, ValueError):
        n = 0.0
    signo = "-" if n < 0 else ""
    return f"{signo}${abs(n):,.2f}"


def fecha(valor):
    """5 nov 2026 — o '—' si no hay fecha."""
    if not valor:
        return "—"
    return f"{valor.day} {_MESES_CORTOS[valor.month - 1]} {valor.year}"


def fecha_hora(valor, hoy=None):
    """5 nov 14:30 si es de este año; 5 nov 2025 14:30 si no. '—' si no hay fecha."""
    if not valor:
        return "—"
    hoy = hoy or date.today()
    base = f"{valor.day} {_MESES_CORTOS[valor.month - 1]}"
    if valor.year != hoy.year:
        base += f" {valor.year}"
    if isinstance(valor, datetime):
        base += f" {valor.hour:02d}:{valor.minute:02d}"
    return base
