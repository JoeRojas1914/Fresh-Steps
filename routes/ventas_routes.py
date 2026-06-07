import logging
import os
import subprocess
from datetime import date, datetime
from flask import Blueprint, render_template, jsonify, session, request, send_file
from models.ventas import obtener_historial_venta
from services.excel_helpers import send_excel
from services.excel_ventas_service import exportar_historial_service

from services.ventas_service import (
    listar_ventas_listas_service,
    registrar_pago_final_service,
    listar_entregas_pendientes_service,
    guardar_venta_service,
    marcar_lista_service,
    revertir_lista_service,
    marcar_entregada,
    obtener_venta,
    obtener_detalles_venta,
    eliminar_venta_service,
    historial_ventas_service,
)

from middleware.auth_middleware import admin_required
from extensions import limiter

logger = logging.getLogger(__name__)

ventas_bp = Blueprint("ventas", __name__)

_EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
_CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.join(os.path.expanduser("~"), r"AppData\Local\Google\Chrome\Application\chrome.exe"),
]

def _encontrar_browser(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


@ventas_bp.route("/ventas/abrir-whatsapp", methods=["POST"])
@limiter.limit("30 per minute")
def abrir_whatsapp():
    if not session.get("id_usuario"):
        return jsonify({"ok": False}), 401
    data       = request.get_json(silent=True) or {}
    url        = data.get("url", "")
    negocio_id = int(data.get("negocio_id", 0))
    if not url.startswith("https://web.whatsapp.com/send?"):
        return jsonify({"ok": False, "error": "URL no válida"}), 400
    is_local = not request.headers.get("X-Forwarded-For")
    if is_local:
        try:
            paths = _EDGE_PATHS if negocio_id == 1 else _CHROME_PATHS
            exe   = _encontrar_browser(paths)
            if exe:
                subprocess.Popen([exe, url])
            else:
                logger.warning("No se encontró el navegador para negocio_id=%s", negocio_id)
        except Exception:
            logger.exception("Error al abrir WhatsApp negocio_id=%s", negocio_id)
        return jsonify({"ok": True, "opened": True})
    return jsonify({"ok": True, "opened": False, "url": url})


@ventas_bp.route("/ventas/guardar", methods=["POST"])
@limiter.limit("30 per minute")
def guardar_venta():
    id_usuario = session.get("id_usuario")
    if not id_usuario:
        return jsonify({"ok": False, "error": "Sesión expirada. Vuelve a iniciar sesión."}), 401
    try:
        id_venta = guardar_venta_service(request.form, id_usuario)
        return jsonify({"ok": True, "id_venta": id_venta}), 200
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception:
        logger.exception("Error en guardar_venta id_usuario=%s", id_usuario)
        return jsonify({"ok": False, "error": "Error interno del servidor"}), 500


@ventas_bp.route("/ventas")
def ventas():
    return render_template("ventas/ventas_crear.html")


@ventas_bp.route("/ventas/entregar/<int:id_venta>", methods=["POST"])
@limiter.limit("30 per minute")
def entregar_venta(id_venta):
    id_usuario = session.get("id_usuario")

    try:
        if marcar_entregada(id_venta, id_usuario):
            return jsonify({
                "ok": True,
                "message": "Venta entregada correctamente"
            })
        else:
            return jsonify({
                "ok": False,
                "error": "La venta ya fue entregada o no existe"
            })

    except Exception:
        logger.exception("Error en entregar_venta id_venta=%s id_usuario=%s", id_venta, id_usuario)
        return jsonify({"ok": False, "error": "Error interno del servidor"}), 500


@ventas_bp.route("/ventas/ticket/<int:id_venta>")
def venta_ticket(id_venta):
    venta = obtener_venta(id_venta)
    if not venta:
        return render_template("errors/404.html"), 404

    detalles_dict = obtener_detalles_venta([id_venta])
    detalles = detalles_dict.get(id_venta, [])
    copias   = min(request.args.get("copias", 1, type=int), 5)

    return render_template(
        "ventas/ticket_venta.html",
        venta=venta,
        detalles=detalles,
        copias=copias,
    )

@ventas_bp.route("/ventas/listas")
def ventas_listas():
    id_negocio = request.args.get("id_negocio", type=int)
    id_venta   = request.args.get("id_venta", type=int)
    pagina     = request.args.get("pagina", 1, type=int)

    data = listar_ventas_listas_service(id_negocio, pagina, id_venta)

    return render_template("ventas/ventas_listas.html", **data)


@ventas_bp.route("/ventas/pendientes")
def ventas_pendientes():
    try:
        id_negocio = request.args.get("id_negocio", type=int)
        id_venta   = request.args.get("id_venta", type=int)
        pagina     = request.args.get("pagina", 1, type=int)

        data = listar_entregas_pendientes_service(id_negocio, pagina, id_venta)

        return render_template("ventas/ventas_pendientes.html", **data)

    except Exception:
        logger.exception("Error en ventas_pendientes id_negocio=%s", request.args.get("id_negocio"))
        return render_template("errors/500.html"), 500


@ventas_bp.route("/ventas/marcar-lista/<int:id_venta>", methods=["POST"])
@limiter.limit("30 per minute")
def marcar_lista(id_venta):
    try:
        id_usuario = session.get('id_usuario')
        if marcar_lista_service(id_venta, id_usuario):
            return jsonify({
                "ok": True,
                "message": "Venta marcada como lista correctamente"
            })
        else:
            return jsonify({
                "ok": False,
                "error": "La venta ya está lista o fue entregada"
            })
    except Exception:
        logger.exception("Error en marcar_lista id_venta=%s id_usuario=%s", id_venta, id_usuario)
        return jsonify({"ok": False, "error": "Error interno del servidor"}), 500


@ventas_bp.route("/ventas/detalles/<int:id_venta>")
def detalles_venta(id_venta):
    detalles = obtener_detalles_venta([id_venta])  
    return jsonify(detalles.get(id_venta, []))

@ventas_bp.route("/ventas/pago-final", methods=["POST"])
@limiter.limit("30 per minute")
def registrar_pago_final():
    data = request.get_json(silent=True) or {}
    id_usuario = session.get("id_usuario")

    try:
        mensaje = registrar_pago_final_service(data, id_usuario)
        return jsonify({"ok": True, "message": mensaje})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception:
        logger.exception("Error en registrar_pago_final id_usuario=%s", id_usuario)
        return jsonify({"ok": False, "error": "Error interno del servidor"}), 500


@ventas_bp.route("/ventas/revertir-lista/<int:id_venta>", methods=["POST"])
@admin_required
@limiter.limit("30 per minute")
def revertir_lista_route(id_venta):
    id_usuario = session.get("id_usuario")
    try:
        if revertir_lista_service(id_venta, id_usuario):
            return jsonify({"ok": True, "message": "Venta regresada a pendientes correctamente"})
        else:
            return jsonify({"ok": False, "error": "La venta no puede ser revertida"})
    except Exception:
        logger.exception("Error en revertir_lista id_venta=%s id_usuario=%s", id_venta, id_usuario)
        return jsonify({"ok": False, "error": "Error interno del servidor"}), 500


@ventas_bp.route("/ventas/eliminar/<int:id_venta>", methods=["POST"])
@admin_required
@limiter.limit("30 per minute")
def eliminar_venta_route(id_venta):
    id_usuario = session.get("id_usuario")

    try:
        eliminar_venta_service(id_venta, id_usuario)
        return jsonify({"ok": True, "message": "Venta eliminada correctamente"})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception:
        logger.exception("Error en eliminar_venta id_venta=%s id_usuario=%s", id_venta, id_usuario)
        return jsonify({"ok": False, "error": "Error interno del servidor"}), 500

@ventas_bp.route("/ventas/historial")
@admin_required
def historial_ventas():

    id_negocio   = request.args.get("id_negocio",  type=int)
    fecha_inicio = request.args.get("fecha_inicio") or None
    fecha_fin    = request.args.get("fecha_fin")    or None
    pagina       = request.args.get("pagina", 1,    type=int)
    q            = request.args.get("q", "").strip() or None
    id_venta     = request.args.get("id_venta",     type=int)
    estado       = request.args.get("estado")       or None

    mostrar_eliminadas = request.args.get('eliminadas') == '1'
    data = historial_ventas_service(
        id_negocio, fecha_inicio, fecha_fin, pagina, mostrar_eliminadas, q=q, id_venta=id_venta, estado=estado
    )

    return render_template("ventas/historial_ventas.html", **data)



@ventas_bp.route("/ventas/historial/exportar")
@admin_required
def exportar_historial_excel():
    id_negocio   = request.args.get("id_negocio",  type=int)
    fecha_inicio = request.args.get("fecha_inicio") or None
    fecha_fin    = request.args.get("fecha_fin")    or None
    wb = exportar_historial_service(id_negocio, fecha_inicio, fecha_fin)
    return send_excel(wb, "historial_ventas")

@ventas_bp.route("/ventas/<int:id_venta>/historial")
def historial_venta_por_id(id_venta):
    data   = obtener_historial_venta(id_venta)
    result = []
    for row in data:
        r = dict(row)
        for k, v in r.items():
            if isinstance(v, (datetime, date)):
                r[k] = v.isoformat()
        result.append(r)
    return jsonify(result)