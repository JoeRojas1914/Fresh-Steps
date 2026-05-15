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
