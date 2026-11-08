import logging
from flask import Blueprint, render_template, request, redirect, flash, url_for, session, jsonify

logger = logging.getLogger(__name__)
from services.excel_helpers import send_excel

from services.gastos_service import (
    listar_gastos,
    guardar_gasto_service,
    eliminar_gasto_service,
    obtener_historial_gasto,
    restaurar_gasto_service,
    obtener_negocios,
    obtener_categorias,
    crear_categoria_service,
    actualizar_categoria_service,
    eliminar_categoria_service,
    exportar_gastos_excel_service,
)
from middleware.auth_middleware import admin_required
from extensions import limiter
from utils import ids_de_args

gastos_bp = Blueprint("gastos", __name__)


@gastos_bp.route("/gastos")
@admin_required
def gastos():
    id_negocio         = ids_de_args(request.args)
    id_categoria       = ids_de_args(request.args, "id_categoria") or None
    fecha_inicio       = request.args.get("fecha_inicio") or None
    fecha_fin          = request.args.get("fecha_fin")    or None
    pagina             = request.args.get("pagina", 1, type=int)
    incluir_eliminados = request.args.get("eliminados") == "1"

    data = listar_gastos(
        id_negocio=id_negocio, id_categoria=id_categoria,
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
        pagina=pagina, incluir_eliminados=incluir_eliminados,
        orden=request.args.get("orden") or None,
        direccion=request.args.get("dir") or None,
    )
    ctx = dict(
        gastos=data["gastos"], negocios=obtener_negocios(),
        categorias=obtener_categorias(),
        pagina=pagina, total_paginas=data["total_paginas"],
        incluir_eliminados=incluir_eliminados
    )
    if request.args.get('partial') == '1':
        return render_template("admin/_gastos_partial.html", **ctx)
    return render_template("admin/gastos.html", **ctx)


@gastos_bp.route("/gastos/guardar", methods=["POST"])
@admin_required
@limiter.limit("30 per minute")
def guardar_gasto():
    id_gasto   = request.form.get("id_gasto")
    id_usuario = session.get("id_usuario")
    try:
        raw_categoria = request.form.get("id_categoria") or None
        datos = (
            int(request.form["id_negocio"]),
            int(raw_categoria) if raw_categoria else None,
            request.form["descripcion"].strip(),
            request.form["proveedor"].strip(),
            float(request.form["total"]),
            request.form["fecha_registro"],
            request.form["tipo_comprobante"],
            request.form["tipo_pago"],
            (request.form.get("notas") or "").strip() or None,
        )
        resultado = guardar_gasto_service(id_gasto, datos, id_usuario)
        flash("Gasto editado correctamente." if resultado == "actualizado"
              else "Gasto creado correctamente.", "success")
    except (ValueError, KeyError):  # pragma: no cover
        flash("Datos inválidos. Verifica los campos ingresados.", "error")
    except Exception:  # pragma: no cover
        logger.exception("Error al guardar gasto id_gasto=%s", id_gasto)
        flash("Error al guardar el gasto. Verifica los datos ingresados.", "error")
    return redirect(url_for("gastos.gastos"))


@gastos_bp.route("/gastos/eliminar/<int:id_gasto>", methods=["POST"])
@admin_required
@limiter.limit("30 per minute")
def eliminar_gasto(id_gasto):
    id_usuario = session.get("id_usuario")
    try:
        eliminar_gasto_service(id_gasto, id_usuario)
        return jsonify({"ok": True, "message": "Gasto eliminado correctamente."})
    except Exception:  # pragma: no cover
        logger.exception("Error al eliminar gasto id_gasto=%s", id_gasto)
        return jsonify({"ok": False, "error": "Error al eliminar el gasto."}), 500


@gastos_bp.route("/gastos/<int:id_gasto>/historial")
@admin_required
def historial_gasto(id_gasto):
    return jsonify(obtener_historial_gasto(id_gasto))


@gastos_bp.route("/gastos/restaurar/<int:id_gasto>", methods=["POST"])
@admin_required
@limiter.limit("30 per minute")
def restaurar_gasto_route(id_gasto):
    id_usuario = session.get("id_usuario")
    try:
        restaurar_gasto_service(id_gasto, id_usuario)
        return jsonify({"ok": True, "message": "Gasto restaurado correctamente."})
    except Exception:  # pragma: no cover
        logger.exception("Error al restaurar gasto id_gasto=%s id_usuario=%s", id_gasto, id_usuario)
        return jsonify({"ok": False, "error": "Error al restaurar el gasto."}), 500


@gastos_bp.route("/gastos/categorias/lista")
@admin_required
def categorias_lista():
    return render_template("admin/_categorias_lista.html", categorias=obtener_categorias())


@gastos_bp.route("/gastos/categorias/guardar", methods=["POST"])
@admin_required
@limiter.limit("30 per minute")
def guardar_categoria():
    data         = request.get_json(silent=True) or {}
    id_categoria = data.get("id_categoria") or None
    nombre       = (data.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"ok": False, "error": "El nombre no puede estar vacío."}), 400
    try:
        if id_categoria:
            actualizar_categoria_service(int(id_categoria), nombre)
        else:
            crear_categoria_service(nombre)
        return jsonify({"ok": True})
    except Exception:  # pragma: no cover
        logger.exception("Error al guardar categoría id=%s", id_categoria)
        return jsonify({"ok": False, "error": "Error al guardar la categoría."}), 500


@gastos_bp.route("/gastos/categorias/eliminar/<int:id_categoria>", methods=["POST"])
@admin_required
@limiter.limit("30 per minute")
def eliminar_categoria_route(id_categoria):
    try:
        ok, mensaje = eliminar_categoria_service(id_categoria)
        if ok:
            return jsonify({"ok": True, "message": mensaje})
        return jsonify({"ok": False, "error": mensaje})
    except Exception:  # pragma: no cover
        logger.exception("Error al eliminar categoría id=%s", id_categoria)
        return jsonify({"ok": False, "error": "Error al eliminar la categoría."}), 500


@gastos_bp.route("/gastos/exportar")
@admin_required
def exportar_gastos_excel():
    wb = exportar_gastos_excel_service(
        ids_de_args(request.args),
        ids_de_args(request.args, "id_categoria") or None,
        request.args.get("fecha_inicio") or None,
        request.args.get("fecha_fin") or None,
        request.args.get("eliminados") == "1",
    )
    return send_excel(wb, "gastos")
