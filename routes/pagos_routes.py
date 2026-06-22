import logging
from flask import Blueprint, render_template, request
from openpyxl import Workbook

from middleware.auth_middleware import admin_required
from models.negocio import obtener_negocios
from services.pagos_service import listar_pagos_service, exportar_pagos_service
from services.excel_helpers import (
    send_excel, xl_titulo_hoja, xl_fila_headers, xl_cell,
    xl_fila_totales, xl_col_widths, xl_row_bg, fmt_dt, C,
)
from config import METODOS_PAGO_VALIDOS

logger = logging.getLogger(__name__)

pagos_bp = Blueprint("pagos", __name__)

TIPOS_PAGO_VENTA = ["prepago", "final"]


def _filtros_request():
    return {
        "id_negocio":     request.args.get("id_negocio")     or None,
        "tipo_pago":      request.args.get("tipo_pago")       or None,
        "tipo_pago_venta": request.args.get("tipo_pago_venta") or None,
        "fecha_inicio":   request.args.get("fecha_inicio")    or None,
        "fecha_fin":      request.args.get("fecha_fin")        or None,
    }


@pagos_bp.route("/pagos")
@admin_required
def historial_pagos():
    f      = _filtros_request()
    pagina = request.args.get("pagina", 1, type=int)
    data   = listar_pagos_service(**f, pagina=pagina)

    ctx = dict(
        pagos         = data["pagos"],
        total         = data["total"],
        pagina        = pagina,
        total_paginas = data["total_paginas"],
        negocios      = obtener_negocios(),
        metodos_pago  = sorted(METODOS_PAGO_VALIDOS),
        tipos_pago_venta = TIPOS_PAGO_VENTA,
    )
    if request.args.get("partial") == "1":
        return render_template("admin/_pagos_partial.html", **ctx)
    return render_template("admin/pagos.html", **ctx)


@pagos_bp.route("/pagos/exportar-excel")
@admin_required
def exportar_pagos_excel():
    f    = _filtros_request()
    rows = exportar_pagos_service(**f)

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
        fecha = fmt_dt(p["fecha_pago"])
        xl_cell(ws, r, 1, fecha,                                    fg=bg)
        xl_cell(ws, r, 2, p["negocio"] or "—",                     fg=bg)
        xl_cell(ws, r, 3,
                f"{p['cliente_nombre']} {p['cliente_apellido']}",   fg=bg)
        xl_cell(ws, r, 4, f"#{p['id_venta']}",    align="center",  fg=bg)
        xl_cell(ws, r, 5,
                (p["tipo_pago_venta"] or "—").capitalize(),
                align="center", fg=bg)
        xl_cell(ws, r, 6,
                (p["tipo_pago"] or "—").capitalize(),
                align="center", fg=bg)
        xl_cell(ws, r, 7, float(p["monto"]),
                num_fmt='"$"#,##0.00', align="right", fg=bg)
        xl_cell(ws, r, 8, p["cobrado_por"] or "—",                 fg=bg)

    if rows:
        xl_fila_totales(ws, len(rows) + 4, ncols, [7])

    xl_col_widths(ws, [18, 14, 22, 10, 10, 14, 12, 16])
    return send_excel(wb, "historial_pagos")
