import logging
from flask import Blueprint, render_template, request
from middleware.auth_middleware import admin_required
from services.pagos_service import (
    listar_pagos_service,
    exportar_pagos_excel_service,
    obtener_negocios,
)
from services.excel_helpers import send_excel
from config import METODOS_PAGO_VALIDOS
from utils import ids_de_args

logger = logging.getLogger(__name__)

pagos_bp = Blueprint("pagos", __name__)

TIPOS_PAGO_VENTA = ["prepago", "final"]


def _filtros_request():
    return {
        "id_negocio":     ids_de_args(request.args),
        "tipo_pago":       [m for m in request.args.getlist("tipo_pago") if m in METODOS_PAGO_VALIDOS] or None,
        "tipo_pago_venta": [t for t in request.args.getlist("tipo_pago_venta") if t in TIPOS_PAGO_VENTA] or None,
        "fecha_inicio":   request.args.get("fecha_inicio")    or None,
        "fecha_fin":      request.args.get("fecha_fin")        or None,
    }


@pagos_bp.route("/pagos")
@admin_required
def historial_pagos():
    f      = _filtros_request()
    pagina = request.args.get("pagina", 1, type=int)
    data   = listar_pagos_service(
        **f, pagina=pagina,
        orden=request.args.get("orden") or None,
        direccion=request.args.get("dir") or None,
    )

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
    return send_excel(exportar_pagos_excel_service(**_filtros_request()), "historial_pagos")
