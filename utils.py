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
