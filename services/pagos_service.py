from __future__ import annotations
from datetime import date
from typing import Any
from utils import calcular_paginacion
from models.pagos import obtener_historial_pagos, contar_historial_pagos


def listar_pagos_service(
    id_negocio: str | None,
    tipo_pago: str | None,
    tipo_pago_venta: str | None,
    fecha_inicio: date | None,
    fecha_fin: date | None,
    pagina: int,
    por_pagina: int = 20,
) -> dict[str, Any]:
    total = contar_historial_pagos(
        id_negocio, tipo_pago, tipo_pago_venta, fecha_inicio, fecha_fin
    )
    offset, total_paginas = calcular_paginacion(total, pagina, por_pagina)
    pagos = obtener_historial_pagos(
        id_negocio, tipo_pago, tipo_pago_venta, fecha_inicio, fecha_fin,
        limit=por_pagina, offset=offset,
    )
    return {"pagos": pagos, "total": total, "total_paginas": total_paginas}


def exportar_pagos_service(
    id_negocio: str | None,
    tipo_pago: str | None,
    tipo_pago_venta: str | None,
    fecha_inicio: date | None,
    fecha_fin: date | None,
) -> list[dict[str, Any]]:
    return obtener_historial_pagos(
        id_negocio, tipo_pago, tipo_pago_venta, fecha_inicio, fecha_fin,
        limit=10_000, offset=0,
    )
