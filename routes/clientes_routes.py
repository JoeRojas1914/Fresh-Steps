import io
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, send_file

logger = logging.getLogger(__name__)
from config import MAX_FILAS_EXPORTAR
from openpyxl import Workbook
from services.excel_helpers import (
    C, xl_cell, xl_row_bg, fmt_dt, estado_venta,
    xl_titulo_hoja, xl_fila_headers, xl_fila_totales,
    xl_col_widths, xl_badge_estado, xl_badge_activo, send_excel,
    build_excel_cliente,
)

from middleware.auth_middleware import admin_required
from extensions import limiter
from services.clientes_service import (
    listar_clientes_service,
    guardar_cliente_service,
    eliminar_cliente_service,
    restaurar_cliente_service,
    buscar_clientes_service,
    obtener_cliente_detalle_service,
    obtener_historial_cliente_service,
    exportar_clientes_service,
    exportar_cliente_service,
)

clientes_bp = Blueprint("clientes", __name__)


@clientes_bp.route("/clientes")
def clientes():
    q = request.args.get("q", "")
    pagina = request.args.get("pagina", 1, type=int)
    incluir_eliminados = request.args.get("eliminados") == "1"
    data = listar_clientes_service(q=q, pagina=pagina, incluir_eliminados=incluir_eliminados)
    ctx = dict(
        clientes=data["clientes"], q=q, pagina=pagina,
        total_paginas=data["total_paginas"],
        total_clientes=data["total_clientes"],
        incluir_eliminados=incluir_eliminados
    )
    if request.args.get('partial') == '1':
        return render_template("clientes/_clientes_partial.html", **ctx)
    return render_template("clientes/clientes.html", **ctx)


@clientes_bp.route("/clientes/guardar", methods=["POST"])
@limiter.limit("30 per minute")
def guardar_cliente():
    id_usuario = session.get("id_usuario")
    try:
        resultado = guardar_cliente_service(request.form, id_usuario)
        flash(
            "Cliente actualizado correctamente." if resultado == "actualizado"
            else "Cliente creado correctamente.", "success"
        )
    except ValueError as e:
        flash(str(e), "error")
    except Exception:
        logger.exception("Error al guardar cliente id_usuario=%s", id_usuario)
        flash("Error al guardar el cliente. Verifica los datos.", "error")
    return redirect(url_for("clientes.clientes"))


@clientes_bp.route("/clientes/eliminar/<int:id_cliente>")
@admin_required
def eliminar_cliente(id_cliente):
    id_usuario = session.get("id_usuario")
    try:
        ok = eliminar_cliente_service(id_cliente, id_usuario)
        if not ok:
            flash("No puedes eliminar el cliente porque ya tiene ventas registradas.", "error")
        else:
            flash("Cliente eliminado correctamente.", "success")
    except Exception:
        logger.exception("Error al eliminar cliente id_cliente=%s", id_cliente)
        flash("Error al eliminar el cliente.", "error")
    return redirect(url_for("clientes.clientes"))


@clientes_bp.route("/clientes/restaurar/<int:id_cliente>")
@admin_required
def restaurar_cliente(id_cliente):
    id_usuario = session.get("id_usuario")
    try:
        restaurar_cliente_service(id_cliente, id_usuario)
        flash("Cliente restaurado correctamente.", "success")
    except Exception:
        logger.exception("Error al restaurar cliente id_cliente=%s", id_cliente)
        flash("Error al restaurar el cliente.", "error")
    return redirect(url_for("clientes.clientes"))


@clientes_bp.route("/clientes/<int:id_cliente>/historial")
@admin_required
def historial_cliente(id_cliente):
    return jsonify(obtener_historial_cliente_service(id_cliente))


@clientes_bp.route("/api/clientes")
def api_clientes():
    q = request.args.get("q", "")
    return jsonify(buscar_clientes_service(q))


@clientes_bp.route("/clientes/<int:id_cliente>")
def ver_cliente(id_cliente):
    filtros = request.args
    data = obtener_cliente_detalle_service(id_cliente, filtros)
    return render_template("clientes/cliente_perfil.html", **data)


@clientes_bp.route("/api/clientes/crear", methods=["POST"])
@limiter.limit("30 per minute")
def api_crear_cliente():
    id_usuario = session.get("id_usuario")
    cliente = guardar_cliente_service(request.form, id_usuario, api=True)
    return jsonify(cliente)


@clientes_bp.route("/clientes/exportar")
@admin_required
def exportar_clientes_excel():
    incluir_eliminados = request.args.get("eliminados") == "1"
    clientes, pedidos_map = exportar_clientes_service(incluir_eliminados)

    wb = Workbook()
    ws = wb.active
    ws.title = "Clientes"
    ws.freeze_panes = "A4"

    xl_titulo_hoja(ws, "Clientes — Fresh Steps", 7,
                   "Incluye eliminados" if incluir_eliminados else "Solo clientes activos")
    xl_fila_headers(ws, ["Nombre", "Apellido", "Teléfono", "Correo", "Dirección", "Estado", "Total pedidos"])

    for i, cl in enumerate(clientes):
        r  = i + 4
        bg = xl_row_bg(i)
        xl_cell(ws, r, 1, cl.get("nombre",    ""),  fg=bg, bold=True)
        xl_cell(ws, r, 2, cl.get("apellido",  ""),  fg=bg, bold=True)
        xl_cell(ws, r, 3, cl.get("telefono",  "—"), fg=bg)
        xl_cell(ws, r, 4, cl.get("correo",    "—"), fg=bg)
        xl_cell(ws, r, 5, cl.get("direccion", "—"), fg=bg)
        xl_badge_activo(ws, r, 6, cl.get("activo", 1))
        xl_cell(ws, r, 7, pedidos_map.get(cl["id_cliente"], 0), fg=bg, align="center")
        ws.row_dimensions[r].height = 16

    xl_col_widths(ws, [20, 20, 14, 28, 30, 11, 13])
    return send_excel(wb, "clientes")


@clientes_bp.route("/clientes/<int:id_cliente>/exportar")
@admin_required
def exportar_cliente_excel(id_cliente):
    id_negocio   = request.args.get("id_negocio")  or None
    fecha_inicio = request.args.get("fecha_inicio") or None
    fecha_fin    = request.args.get("fecha_fin")    or None

    cliente, pedidos, detalles_map, pagos_map = exportar_cliente_service(
        id_cliente, id_negocio, fecha_inicio, fecha_fin
    )

    nombre_cliente = f"{cliente['nombre']} {cliente['apellido']}"
    filtro_txt = "  ".join(filter(None, [
        f"Desde: {fecha_inicio}" if fecha_inicio else "",
        f"Hasta: {fecha_fin}"   if fecha_fin    else "",
    ])) or "Sin filtros de fecha"

    wb = build_excel_cliente(pedidos, detalles_map, pagos_map, nombre_cliente, filtro_txt)
    nombre_archivo = f"pedidos_{cliente['nombre']}_{cliente['apellido']}".replace(" ", "_")
    return send_excel(wb, nombre_archivo)