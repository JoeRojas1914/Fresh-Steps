from __future__ import annotations
from datetime import date
from typing import Any
from openpyxl import Workbook

from utils import calcular_paginacion
from models.negocio import obtener_negocios  # re-exportado para las rutas
from models.pagos import obtener_historial_pagos, contar_historial_pagos
from services.excel_helpers import (
    xl_titulo_hoja, xl_fila_headers, xl_cell,
    xl_fila_totales, xl_col_widths, xl_row_bg, fmt_dt,
)


def listar_pagos_service(
    id_negocio: str | None,
    tipo_pago: str | None,
    tipo_pago_venta: str | None,
    fecha_inicio: date | None,
    fecha_fin: date | None,
    pagina: int,
    por_pagina: int = 20,
    orden: str | None = None,
    direccion: str | None = None,
) -> dict[str, Any]:
    total = contar_historial_pagos(
        id_negocio, tipo_pago, tipo_pago_venta, fecha_inicio, fecha_fin
    )
    offset, total_paginas = calcular_paginacion(total, pagina, por_pagina)
    pagos = obtener_historial_pagos(
        id_negocio, tipo_pago, tipo_pago_venta, fecha_inicio, fecha_fin,
        limit=por_pagina, offset=offset,
        orden=orden, direccion=direccion,
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


def exportar_pagos_excel_service(
    id_negocio, tipo_pago, tipo_pago_venta, fecha_inicio, fecha_fin,
) -> Workbook:
    rows = exportar_pagos_service(id_negocio, tipo_pago, tipo_pago_venta, fecha_inicio, fecha_fin)

    wb = Workbook()
    ws = wb.active
    ws.title = "Historial de Pagos"

    ncols = 8
    xl_titulo_hoja(ws, "Historial de Pagos", ncols, "Fresh Steps")
    xl_fila_headers(ws, [
        "Fecha pago", "Negocio", "Cliente", "Recibo #",
        "Tipo", "Método", "Monto", "Cobrado por",
    ])

    for i, p in enumerate(rows, 1):
        r  = i + 3
        bg = xl_row_bg(i)
        xl_cell(ws, r, 1, fmt_dt(p["fecha_pago"]), fg=bg)
        xl_cell(ws, r, 2, p["negocio"] or "—", fg=bg)
        xl_cell(ws, r, 3, f"{p['cliente_nombre']} {p['cliente_apellido']}", fg=bg)
        xl_cell(ws, r, 4, f"#{p['id_venta']}", align="center", fg=bg)
        xl_cell(ws, r, 5, (p["tipo_pago_venta"] or "—").capitalize(), align="center", fg=bg)
        xl_cell(ws, r, 6, (p["tipo_pago"] or "—").capitalize(), align="center", fg=bg)
        xl_cell(ws, r, 7, float(p["monto"]), num_fmt='"$"#,##0.00', align="right", fg=bg)
        xl_cell(ws, r, 8, p["cobrado_por"] or "—", fg=bg)

    if rows:
        xl_fila_totales(ws, len(rows) + 4, ncols, [7])

    xl_col_widths(ws, [18, 14, 22, 10, 10, 14, 12, 16])
    return wb
