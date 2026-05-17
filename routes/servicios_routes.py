import io
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, flash, jsonify, session, send_file, url_for

logger = logging.getLogger(__name__)
from config import MAX_FILAS_EXPORTAR
from openpyxl import Workbook
from services.excel_helpers import (
    C, xl_cell, xl_row_bg,
    xl_titulo_hoja, xl_fila_headers,
    xl_col_widths, xl_badge_activo, send_excel
)


from middleware.auth_middleware import admin_required
from extensions import limiter
from services.servicios_service import (
    listar_servicios,
    guardar_servicio_service,
    eliminar_servicio_service,
    obtener_historial_servicio_service,
    restaurar_servicio_service
)
from models.negocio import obtener_negocios

servicios_bp = Blueprint("servicios", __name__)

@servicios_bp.route("/servicios")
def servicios():
    q = request.args.get("q", "")
    id_negocio = request.args.get("id_negocio", type=int)
    pagina = request.args.get("pagina", 1, type=int)

    incluir_eliminados = bool(request.args.get("eliminados"))

    data = listar_servicios(
        id_negocio=id_negocio,
        q=q,
        pagina=pagina,
        por_pagina=10,
        incluir_eliminados=incluir_eliminados 
    )

    negocios = obtener_negocios()

    return render_template(
        "admin/servicios.html",
        servicios=data["servicios"],
        negocios=negocios,
        id_negocio=id_negocio,
        q=q,
        pagina=pagina,
        total_paginas=data["total_paginas"],
        total_servicios=data["total"],
        incluir_eliminados=incluir_eliminados
    )



@servicios_bp.route("/servicios/guardar", methods=["POST"])
@admin_required
@limiter.limit("30 per minute")
def guardar_servicio():
    id_servicio = request.form.get("id_servicio") or None
    id_usuario = session.get("id_usuario")
    try:
        id_negocio = int(request.form["id_negocio"])
        nombre = request.form["nombre"]
        precio = float(request.form["precio"])
        resultado = guardar_servicio_service(id_servicio, id_negocio, nombre, precio, id_usuario)
        flash("Servicio actualizado correctamente." if resultado == "actualizado"
              else "Servicio creado correctamente.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except (KeyError, TypeError):
        flash("Datos inválidos. Verifica los campos ingresados.", "error")
    except Exception:
        logger.exception("Error al guardar servicio id_servicio=%s", id_servicio)
        flash("Error al guardar el servicio.", "error")
    return redirect(url_for("servicios.servicios"))


@servicios_bp.route("/servicios/eliminar/<int:id_servicio>")
@admin_required
@limiter.limit("30 per minute")
def eliminar_servicio(id_servicio):
    id_usuario = session.get("id_usuario")
    try:
        eliminar_servicio_service(id_servicio, id_usuario)
        flash("Servicio eliminado correctamente.", "success")
    except Exception:
        logger.exception("Error al eliminar servicio id_servicio=%s", id_servicio)
        flash("Error al eliminar el servicio.", "error")
    return redirect(url_for("servicios.servicios"))




@servicios_bp.route("/api/servicios")
def api_servicios():
    id_negocio = request.args.get("id_negocio", type=int)

    data = listar_servicios(
        id_negocio=id_negocio,
        pagina=1,
        por_pagina=1000
    )

    return jsonify(data["servicios"])



@servicios_bp.route("/servicios/<int:id_servicio>/historial")
def historial_servicio(id_servicio):
    data = obtener_historial_servicio_service(id_servicio)
    return jsonify(data)


@servicios_bp.route("/servicios/restaurar/<int:id_servicio>")
@admin_required
@limiter.limit("30 per minute")
def restaurar_servicio(id_servicio):
    id_usuario = session.get("id_usuario")
    try:
        restaurar_servicio_service(id_servicio, id_usuario)
        flash("Servicio restaurado correctamente.", "success")
    except Exception:
        logger.exception("Error al restaurar servicio id_servicio=%s id_usuario=%s", id_servicio, id_usuario)
        flash("Error al restaurar el servicio.", "error")
    return redirect(url_for("servicios.servicios"))


@servicios_bp.route("/servicios/exportar")
@admin_required
def exportar_servicios_excel():
    from servicios import obtener_servicios

    id_negocio         = request.args.get("id_negocio") or None
    incluir_eliminados = request.args.get("eliminados") == "1"

    servicios = obtener_servicios(
        id_negocio=id_negocio, incluir_eliminados=incluir_eliminados,
        limit=MAX_FILAS_EXPORTAR, offset=0
    )

    subtexto = f"Negocio ID: {id_negocio}" if id_negocio else "Todos los negocios"
    if incluir_eliminados:
        subtexto += "  |  Incluye eliminados"

    wb = Workbook()
    ws = wb.active
    ws.title = "Servicios"
    ws.freeze_panes = "A4"

    xl_titulo_hoja(ws, "Catálogo de Servicios — Fresh Steps", 4, subtexto)
    xl_fila_headers(ws, ["Negocio", "Servicio", "Precio ($)", "Estado"])

    for i, s in enumerate(servicios):
        r  = i + 4
        bg = xl_row_bg(i)
        xl_cell(ws, r, 1, s.get("negocio", ""), fg=bg)
        xl_cell(ws, r, 2, s.get("nombre",  ""), fg=bg)
        xl_cell(ws, r, 3, float(s.get("precio") or 0), fg=bg, bold=True,
                align="right", num_fmt='"$"#,##0.00')
        xl_badge_activo(ws, r, 4, s.get("activo", 1))
        ws.row_dimensions[r].height = 16

    xl_col_widths(ws, [20, 32, 14, 12])
    return send_excel(wb, "servicios")