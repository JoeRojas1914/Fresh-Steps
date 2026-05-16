import io
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, flash, url_for, session, jsonify, send_file

logger = logging.getLogger(__name__)
from openpyxl import Workbook
from services.excel_helpers import (
    C, xl_cell, xl_row_bg,
    xl_titulo_hoja, xl_fila_headers, xl_fila_totales,
    xl_col_widths, xl_badge_activo, send_excel
)

from services.gastos_service import (
    listar_gastos,
    guardar_gasto_service,
    eliminar_gasto_service,
    obtener_historial_gasto,
    restaurar_gasto_service
)
from negocio import obtener_negocios
from middleware.auth_middleware import admin_required
from extensions import limiter

gastos_bp = Blueprint("gastos", __name__)


@gastos_bp.route("/gastos")
@admin_required
def gastos():
    id_negocio         = request.args.get("id_negocio")
    fecha_inicio       = request.args.get("fecha_inicio")
    fecha_fin          = request.args.get("fecha_fin")
    pagina             = request.args.get("pagina", 1, type=int)
    incluir_eliminados = request.args.get("eliminados") == "1"

    data = listar_gastos(
        id_negocio=id_negocio, fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin, pagina=pagina,
        incluir_eliminados=incluir_eliminados
    )
    return render_template(
        "gastos.html",
        gastos=data["gastos"], negocios=obtener_negocios(),
        pagina=pagina, total_paginas=data["total_paginas"],
        incluir_eliminados=incluir_eliminados
    )


@gastos_bp.route("/gastos/guardar", methods=["POST"])
@limiter.limit("30 per minute")
def guardar_gasto():
    id_gasto   = request.form.get("id_gasto")
    id_usuario = session.get("id_usuario")
    try:
        datos = (
            int(request.form["id_negocio"]),   request.form["descripcion"],
            request.form["proveedor"],          float(request.form["total"]),
            request.form["fecha_registro"],     request.form["tipo_comprobante"],
            request.form["tipo_pago"]
        )
        resultado = guardar_gasto_service(id_gasto, datos, id_usuario)
        flash("Gasto editado correctamente." if resultado == "actualizado"
              else "Gasto creado correctamente.", "success")
    except (ValueError, KeyError):
        flash("Datos inválidos. Verifica los campos ingresados.", "error")
    except Exception:
        logger.exception("Error al guardar gasto id_gasto=%s", id_gasto)
        flash("Error al guardar el gasto. Verifica los datos ingresados.", "error")
    return redirect(url_for("gastos.gastos"))


@gastos_bp.route("/gastos/eliminar/<int:id_gasto>")
@limiter.limit("30 per minute")
def eliminar_gasto(id_gasto):
    id_usuario = session.get("id_usuario")
    try:
        eliminar_gasto_service(id_gasto, id_usuario)
        flash("Gasto eliminado correctamente.", "success")
    except Exception:
        logger.exception("Error al eliminar gasto id_gasto=%s", id_gasto)
        flash("Error al eliminar el gasto.", "error")
    return redirect(url_for("gastos.gastos"))


@gastos_bp.route("/gastos/<int:id_gasto>/historial")
def historial_gasto(id_gasto):
    return jsonify(obtener_historial_gasto(id_gasto))


@gastos_bp.route("/gastos/restaurar/<int:id_gasto>")
@limiter.limit("30 per minute")
def restaurar_gasto_route(id_gasto):
    id_usuario = session.get("id_usuario")
    try:
        restaurar_gasto_service(id_gasto, id_usuario)
        flash("Gasto restaurado correctamente.", "success")
    except Exception:
        logger.exception("Error al restaurar gasto id_gasto=%s id_usuario=%s", id_gasto, id_usuario)
        flash("Error al restaurar el gasto.", "error")
    return redirect(url_for("gastos.gastos"))


@gastos_bp.route("/gastos/exportar")
@admin_required
def exportar_gastos_excel():
    from gastos import obtener_gastos

    id_negocio         = request.args.get("id_negocio")  or None
    fecha_inicio       = request.args.get("fecha_inicio") or None
    fecha_fin          = request.args.get("fecha_fin")    or None
    incluir_eliminados = request.args.get("eliminados") == "1"

    gastos = obtener_gastos(
        id_negocio, fecha_inicio, fecha_fin,
        limit=99999, offset=0, incluir_eliminados=incluir_eliminados
    )

    PAGO_LABEL = {"efectivo": "Efectivo", "transferencia": "Transferencia", "TDC": "Tarjeta de cr\u00e9dito"}
    COMP_LABEL = {"factura": "Factura", "ticket": "Ticket"}

    subtexto = "  ".join(filter(None, [
        f"Negocio ID: {id_negocio}" if id_negocio    else "",
        f"Desde: {fecha_inicio}"    if fecha_inicio   else "",
        f"Hasta: {fecha_fin}"       if fecha_fin      else "",
    ])) or "Sin filtros \u2014 todos los registros"

    NCOLS   = 9
    HEADERS = ["Negocio","Descripci\u00f3n","Proveedor","Total ($)",
               "Comprobante","M\u00e9todo de pago","Fecha registro","Registrado por","Estado"]

    wb = Workbook()
    ws = wb.active
    ws.title = "Gastos"
    ws.freeze_panes = "A4"

    xl_titulo_hoja(ws, "Gastos \u2014 Fresh Steps", NCOLS, subtexto)
    xl_fila_headers(ws, HEADERS)

    for i, g in enumerate(gastos):
        r  = i + 4
        bg = xl_row_bg(i)
        xl_cell(ws, r, 1, g.get("negocio",     ""), fg=bg)
        xl_cell(ws, r, 2, g.get("descripcion", ""), fg=bg)
        xl_cell(ws, r, 3, g.get("proveedor",   ""), fg=bg)
        xl_cell(ws, r, 4, float(g.get("total") or 0), fg=bg, bold=True, align="right", num_fmt='"$"#,##0.00')
        xl_cell(ws, r, 5, COMP_LABEL.get(g.get("tipo_comprobante",""), g.get("tipo_comprobante","")), fg=bg)
        xl_cell(ws, r, 6, PAGO_LABEL.get(g.get("tipo_pago",""), g.get("tipo_pago","")), fg=bg)
        fr = g.get("fecha_registro")
        xl_cell(ws, r, 7, fr.strftime("%d/%m/%Y") if fr else "\u2014", fg=bg)
        xl_cell(ws, r, 8, g.get("creado_por", "\u2014"), fg=bg)
        xl_badge_activo(ws, r, 9, g.get("activo", 1))
        ws.row_dimensions[r].height = 16

    if gastos:
        xl_fila_totales(ws, len(gastos) + 4, NCOLS, [4])

    xl_col_widths(ws, [18, 28, 22, 13, 13, 18, 16, 18, 11])
    return send_excel(wb, "gastos")