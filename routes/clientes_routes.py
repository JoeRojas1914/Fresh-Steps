import logging
from urllib.parse import urlparse
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session

logger = logging.getLogger(__name__)
from services.excel_helpers import send_excel

from middleware.auth_middleware import admin_required
from extensions import limiter
from utils import ids_de_args
from services.permisos_service import (
    negocios_permitidos,
    restringir_negocios,
    puede_ver_cliente,
    negocios_visibles,
)
from services.clientes_service import (
    listar_clientes_service,
    guardar_cliente_service,
    eliminar_cliente_service,
    restaurar_cliente_service,
    buscar_clientes_service,
    obtener_cliente_detalle_service,
    obtener_historial_cliente_service,
    obtener_cliente_service,
    exportar_clientes_excel_service,
    exportar_cliente_excel_service,
)

clientes_bp = Blueprint("clientes", __name__)

_SIN_PERMISO_CLIENTE = "No tienes permiso para ver este cliente."


def _es_admin() -> bool:
    return negocios_permitidos() is None


@clientes_bp.route("/clientes")
def clientes():
    q = request.args.get("q", "")
    pagina = request.args.get("pagina", 1, type=int)
    incluir_eliminados = _es_admin() and request.args.get("eliminados") == "1"
    data = listar_clientes_service(
        q=q, pagina=pagina, incluir_eliminados=incluir_eliminados,
        orden=request.args.get("orden") or None,
        direccion=request.args.get("dir") or None,
        id_negocio=None if _es_admin() else restringir_negocios(),
    )
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
    id_cliente = request.form.get("id_cliente")
    if id_cliente and (not id_cliente.isdigit() or not puede_ver_cliente(int(id_cliente))):
        flash(_SIN_PERMISO_CLIENTE, "error")
        return redirect(url_for("clientes.clientes"))
    try:
        resultado = guardar_cliente_service(request.form, id_usuario)
        flash(
            "Cliente actualizado correctamente." if resultado == "actualizado"
            else "Cliente creado correctamente.", "success"
        )
    except ValueError as e:  # pragma: no cover
        flash(str(e), "error")
    except Exception:  # pragma: no cover
        logger.exception("Error al guardar cliente id_usuario=%s", id_usuario)
        flash("Error al guardar el cliente. Verifica los datos.", "error")
    next_url = request.form.get('next', '').strip()
    if next_url and next_url.startswith('/') and not next_url.startswith(('//', '/\\')):
        return redirect(next_url)
    return redirect(url_for("clientes.clientes"))


@clientes_bp.route("/clientes/eliminar/<int:id_cliente>", methods=["POST"])
@admin_required
def eliminar_cliente(id_cliente):
    id_usuario = session.get("id_usuario")
    try:
        ok = eliminar_cliente_service(id_cliente, id_usuario)
        if not ok:
            return jsonify({"ok": False, "error": "No puedes eliminar el cliente porque ya tiene ventas registradas."})
        return jsonify({"ok": True, "message": "Cliente eliminado correctamente."})
    except Exception:  # pragma: no cover
        logger.exception("Error al eliminar cliente id_cliente=%s", id_cliente)
        return jsonify({"ok": False, "error": "Error al eliminar el cliente."}), 500


@clientes_bp.route("/clientes/restaurar/<int:id_cliente>", methods=["POST"])
@admin_required
def restaurar_cliente(id_cliente):
    id_usuario = session.get("id_usuario")
    try:
        restaurar_cliente_service(id_cliente, id_usuario)
        return jsonify({"ok": True, "message": "Cliente restaurado correctamente."})
    except Exception:  # pragma: no cover
        logger.exception("Error al restaurar cliente id_cliente=%s", id_cliente)
        return jsonify({"ok": False, "error": "Error al restaurar el cliente."}), 500


@clientes_bp.route("/clientes/<int:id_cliente>/historial")
def historial_cliente(id_cliente):
    if not puede_ver_cliente(id_cliente):
        return jsonify({"ok": False, "error": _SIN_PERMISO_CLIENTE}), 403
    return jsonify(obtener_historial_cliente_service(id_cliente))


@clientes_bp.route("/api/clientes")
def api_clientes():
    q = request.args.get("q", "")
    return jsonify(buscar_clientes_service(q))


@clientes_bp.route("/clientes/<int:id_cliente>")
def ver_cliente(id_cliente):
    if not puede_ver_cliente(id_cliente):
        return render_template("errors/403.html"), 403
    # Uno o varios negocios (?id_negocio=1&id_negocio=3)
    filtros = request.args.to_dict()
    filtros["id_negocio"] = ids_de_args(request.args)
    negocios_kpis = None
    if not _es_admin():
        # Pedidos y KPIs solo de los negocios de la caja
        filtros["id_negocio"] = restringir_negocios(filtros["id_negocio"])
        negocios_kpis = restringir_negocios()
    data = obtener_cliente_detalle_service(id_cliente, filtros, negocios_kpis=negocios_kpis)
    data["negocios"] = negocios_visibles()
    # En pantalla solo se marcan los negocios que se pidieron explícitamente
    data["id_negocio"] = ids_de_args(request.args)
    if request.args.get('partial') == '1':
        return render_template("clientes/_cliente_pedidos_partial.html", **data)
    data["volver_url"] = _url_volver_clientes()
    if not _es_admin():
        data["kpis"] = None   
    return render_template("clientes/cliente_perfil.html", **data)


def _url_volver_clientes() -> str:
    """Regresa a la lista de clientes conservando búsqueda/página si se llegó desde ahí."""
    lista = url_for("clientes.clientes")
    ref = urlparse(request.referrer or "")
    if ref.netloc == request.host and ref.path == lista:
        return f"{lista}?{ref.query}" if ref.query else lista
    return lista


@clientes_bp.route("/api/clientes/crear", methods=["POST"])
@limiter.limit("30 per minute")
def api_crear_cliente():
    id_usuario = session.get("id_usuario")
    try:
        cliente = guardar_cliente_service(request.form, id_usuario, api=True)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    return jsonify(cliente)


@clientes_bp.route("/api/clientes/<int:id_cliente>")
def api_obtener_cliente(id_cliente):
    if not puede_ver_cliente(id_cliente):
        return jsonify({"ok": False, "error": _SIN_PERMISO_CLIENTE}), 403
    cliente = obtener_cliente_service(id_cliente)
    if not cliente:
        return jsonify({"ok": False, "error": "Cliente no encontrado."}), 404
    return jsonify(cliente)


@clientes_bp.route("/api/clientes/<int:id_cliente>/editar", methods=["POST"])
@limiter.limit("30 per minute")
def api_editar_cliente(id_cliente):
    if not puede_ver_cliente(id_cliente):
        return jsonify({"ok": False, "error": _SIN_PERMISO_CLIENTE}), 403
    if not obtener_cliente_service(id_cliente):
        return jsonify({"ok": False, "error": "Cliente no encontrado."}), 404
    form = request.form.to_dict()
    form["id_cliente"] = id_cliente
    try:
        guardar_cliente_service(form, session.get("id_usuario"))
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception:  # pragma: no cover
        logger.exception("Error al editar cliente id_cliente=%s", id_cliente)
        return jsonify({"ok": False, "error": "Error al guardar el cliente."}), 500
    return jsonify({"ok": True, "cliente": obtener_cliente_service(id_cliente)})


@clientes_bp.route("/clientes/exportar")
@admin_required
def exportar_clientes_excel():
    wb = exportar_clientes_excel_service(
        incluir_eliminados=request.args.get("eliminados") == "1",
        q=request.args.get("q", "").strip() or None,
        orden=request.args.get("orden") or None,
        direccion=request.args.get("dir") or None,
    )
    return send_excel(wb, "clientes")


@clientes_bp.route("/clientes/<int:id_cliente>/exportar")
@admin_required
def exportar_cliente_excel(id_cliente):
    resultado = exportar_cliente_excel_service(
        id_cliente,
        ids_de_args(request.args),
        request.args.get("fecha_inicio") or None,
        request.args.get("fecha_fin") or None,
    )
    if not resultado:
        return render_template("errors/404.html"), 404
    wb, nombre_archivo = resultado
    return send_excel(wb, nombre_archivo)
