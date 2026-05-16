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
