import logging
import os
import subprocess
from datetime import date, datetime
from flask import Blueprint, render_template, jsonify, session, request
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
    obtener_historial_venta,
    eliminar_venta_service,
    historial_ventas_service,
)

from services.ventas_editar_service import obtener_venta_editar_service, editar_venta_service
from services.permisos_service import (
    negocios_permitidos,
    restringir_negocios,
    puede_usar_negocio,
    puede_ver_venta,
    negocios_visibles,
)
from middleware.auth_middleware import admin_required
from extensions import limiter
from utils import a_entero, ids_de_args

logger = logging.getLogger(__name__)

ventas_bp = Blueprint("ventas", __name__)

_SIN_PERMISO = "No tienes permiso para ver ventas de este negocio."

_EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
_CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.join(os.path.expanduser("~"), r"AppData\Local\Google\Chrome\Application\chrome.exe"),
]

_IPS_LOCALES = {"127.0.0.1", "::1"}


def _encontrar_browser(paths):
    for p in paths:
        if os.path.exists(p):
            return p  # pragma: no cover
    return None  # pragma: no cover


@ventas_bp.route("/ventas/abrir-whatsapp", methods=["POST"])
@limiter.limit("30 per minute")
def abrir_whatsapp():
    if not session.get("id_usuario"):  # pragma: no cover
        return jsonify({"ok": False}), 401
    data       = request.get_json(silent=True) or {}
    url        = data.get("url", "")
    negocio_id = a_entero(data.get("negocio_id")) or 0
    if not isinstance(url, str) or not url.startswith("https://web.whatsapp.com/send?"):
        return jsonify({"ok": False, "error": "URL no válida"}), 400
    # Solo se abre el navegador en el servidor si la petición viene del mismo equipo;
    # desde otra terminal se regresa la URL para abrirla en el navegador del cliente.
    is_local = request.remote_addr in _IPS_LOCALES and not request.headers.get("X-Forwarded-For")
    if is_local:
        paths = _EDGE_PATHS if negocio_id == 1 else _CHROME_PATHS
        exe   = _encontrar_browser(paths)
        if exe:
            try:
                subprocess.Popen([exe, url])  # pragma: no cover
                return jsonify({"ok": True, "opened": True})  # pragma: no cover
            except Exception:  # pragma: no cover
                logger.exception("Error al abrir WhatsApp negocio_id=%s", negocio_id)
        else:
            logger.warning("No se encontró el navegador para negocio_id=%s", negocio_id)
    # Sin navegador dedicado (o desde otra terminal): el cliente abre la URL en su navegador
    return jsonify({"ok": True, "opened": False, "url": url})


@ventas_bp.route("/ventas/guardar", methods=["POST"])
@limiter.limit("30 per minute")
def guardar_venta():
    id_usuario = session.get("id_usuario")
    if not id_usuario:  # pragma: no cover
        return jsonify({"ok": False, "error": "Sesión expirada. Vuelve a iniciar sesión."}), 401
    if not puede_usar_negocio(request.form.get("id_negocio")):
        return jsonify({"ok": False, "error": "No tienes permiso para registrar ventas de este negocio."}), 403
    id_venta, error = guardar_venta_service(request.form, id_usuario)
    if error:
        status = 500 if "interno" in error.lower() else 400
        return jsonify({"ok": False, "error": error}), status
    return jsonify({"ok": True, "id_venta": id_venta}), 200


@ventas_bp.route("/ventas")
def ventas():
    return render_template("ventas/ventas_crear.html", negocios=negocios_visibles())


@ventas_bp.route("/ventas/entregar/<int:id_venta>", methods=["POST"])
@limiter.limit("30 per minute")
def entregar_venta(id_venta):
    id_usuario = session.get("id_usuario")
    if not puede_ver_venta(id_venta, estricto=True):
        return jsonify({"ok": False, "error": _SIN_PERMISO}), 403

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
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception:  # pragma: no cover
        logger.exception("Error en entregar_venta id_venta=%s id_usuario=%s", id_venta, id_usuario)
        return jsonify({"ok": False, "error": "Error interno del servidor"}), 500


@ventas_bp.route("/ventas/ticket/<int:id_venta>")
def venta_ticket(id_venta):
    venta = obtener_venta(id_venta)
    if not venta:
        return render_template("errors/404.html"), 404
    if not puede_ver_venta(id_venta):
        return render_template("errors/403.html"), 403

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
    id_negocio    = ids_de_args(request.args)
    id_venta_raw  = request.args.get("id_venta", "").strip()
    id_venta      = id_venta_raw if id_venta_raw.isdigit() else None
    pagina        = request.args.get("pagina", 1, type=int)
    q             = request.args.get("q", "").strip() or None
    articulo      = request.args.get("articulo", "").strip() or None

    orden         = request.args.get("orden") or None
    direccion     = request.args.get("dir") or None

    data = listar_ventas_listas_service(restringir_negocios(id_negocio), pagina, id_venta, q=q,
                                        orden=orden, direccion=direccion,
                                        articulo=articulo)

    if request.args.get('partial') == '1':
        return render_template("ventas/_listas_partial.html", **data)
    return render_template("ventas/ventas_listas.html", **data)


@ventas_bp.route("/ventas/pendientes")
def ventas_pendientes():
    try:
        id_negocio    = ids_de_args(request.args)
        id_venta_raw  = request.args.get("id_venta", "").strip()
        id_venta      = id_venta_raw if id_venta_raw.isdigit() else None
        pagina        = request.args.get("pagina", 1, type=int)
        q             = request.args.get("q", "").strip() or None
        articulo      = request.args.get("articulo", "").strip() or None

        orden         = request.args.get("orden") or None
        direccion     = request.args.get("dir") or None

        data = listar_entregas_pendientes_service(restringir_negocios(id_negocio), pagina, id_venta, q=q,
                                                  orden=orden, direccion=direccion,
                                                  articulo=articulo)

        if request.args.get('partial') == '1':
            return render_template("ventas/_pendientes_partial.html", **data)
        return render_template("ventas/ventas_pendientes.html", **data)

    except Exception:  # pragma: no cover
        logger.exception("Error en ventas_pendientes id_negocio=%s", request.args.get("id_negocio"))
        return render_template("errors/500.html"), 500


@ventas_bp.route("/ventas/marcar-lista/<int:id_venta>", methods=["POST"])
@limiter.limit("30 per minute")
def marcar_lista(id_venta):
    if not puede_ver_venta(id_venta, estricto=True):
        return jsonify({"ok": False, "error": _SIN_PERMISO}), 403
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
    except Exception:  # pragma: no cover
        logger.exception("Error en marcar_lista id_venta=%s id_usuario=%s", id_venta, id_usuario)
        return jsonify({"ok": False, "error": "Error interno del servidor"}), 500


@ventas_bp.route("/ventas/detalles/<int:id_venta>")
def detalles_venta(id_venta):
    if not puede_ver_venta(id_venta):
        return jsonify({"ok": False, "error": _SIN_PERMISO}), 403
    detalles = obtener_detalles_venta([id_venta])
    return jsonify(detalles.get(id_venta, []))

@ventas_bp.route("/ventas/pago-final", methods=["POST"])
@limiter.limit("30 per minute")
def registrar_pago_final():
    data = request.get_json(silent=True) or {}
    id_usuario = session.get("id_usuario")

    id_venta_pago = a_entero(data.get("id_venta"))
    if id_venta_pago is None:
        return jsonify({"ok": False, "error": "Datos incompletos para el pago final"}), 400
    if not puede_ver_venta(id_venta_pago, estricto=True):
        return jsonify({"ok": False, "error": _SIN_PERMISO}), 403
    data["id_venta"] = id_venta_pago

    ok, mensaje = registrar_pago_final_service(data, id_usuario)
    if not ok:
        return jsonify({"ok": False, "error": mensaje}), 400
    return jsonify({"ok": True, "message": mensaje})


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
    except Exception:  # pragma: no cover
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
    except Exception:  # pragma: no cover
        logger.exception("Error en eliminar_venta id_venta=%s id_usuario=%s", id_venta, id_usuario)
        return jsonify({"ok": False, "error": "Error interno del servidor"}), 500

_TIPOS_FECHA_HISTORIAL = {"fecha_recibo", "fecha_lista", "fecha_entrega"}
_ESTADOS_HISTORIAL     = ("pendiente", "lista", "entregada", "eliminada")


def _filtros_historial():
    """Lee los filtros del historial desde la query string (compartido por la tabla y el Excel).

    La caja solo ve sus negocios asignados y nunca las ventas eliminadas."""
    tipo_fecha = request.args.get("tipo_fecha", "fecha_recibo")
    if tipo_fecha not in _TIPOS_FECHA_HISTORIAL:
        tipo_fecha = "fecha_recibo"
    es_admin = negocios_permitidos() is None
    estados  = request.args.getlist("estado")
    if not es_admin:
        estados = [e for e in estados if e != "eliminada"]
    id_negocio = ids_de_args(request.args)
    return {
        "id_negocio":         id_negocio if es_admin else restringir_negocios(id_negocio),
        "fecha_inicio":       request.args.get("fecha_inicio") or None,
        "fecha_fin":          request.args.get("fecha_fin")    or None,
        "mostrar_eliminadas": es_admin and request.args.get("eliminadas") == "1",
        "q":                  request.args.get("q", "").strip() or None,
        "articulo":           request.args.get("articulo", "").strip() or None,
        "id_venta":           request.args.get("id_venta", type=int),
        "estado":             [e for e in _ESTADOS_HISTORIAL if e in estados],
        "tipo_fecha":         tipo_fecha,
    }


@ventas_bp.route("/ventas/historial")
def historial_ventas():
    filtros = _filtros_historial()
    data = historial_ventas_service(
        **filtros,
        pagina=request.args.get("pagina", 1, type=int),
        orden=request.args.get("orden") or None,
        direccion=request.args.get("dir") or None,
    )
    data["negocios"] = negocios_visibles()
    # El filtro de la caja se calcula con todos sus negocios; en pantalla solo
    # se marcan los que pidió explícitamente.
    if negocios_permitidos() is not None:
        data["id_negocio"] = [n for n in filtros["id_negocio"]
                              if str(n) in request.args.getlist("id_negocio")]

    if request.args.get('partial') == '1':
        return render_template("ventas/_historial_partial.html", **data)
    return render_template("ventas/historial_ventas.html", **data)



@ventas_bp.route("/ventas/historial/exportar")
@admin_required
def exportar_historial_excel():
    wb = exportar_historial_service(
        **_filtros_historial(),
        orden=request.args.get("orden") or None,
        direccion=request.args.get("dir") or None,
    )
    return send_excel(wb, "historial_ventas")

@ventas_bp.route("/ventas/<int:id_venta>/historial")
def historial_venta_por_id(id_venta):
    if not puede_ver_venta(id_venta, estricto=True):
        return jsonify({"ok": False, "error": _SIN_PERMISO}), 403
    data   = obtener_historial_venta(id_venta)
    result = []
    for row in data:
        r = dict(row)
        for k, v in r.items():
            if isinstance(v, (datetime, date)):
                r[k] = v.isoformat()
        result.append(r)
    return jsonify(result)


@ventas_bp.route("/ventas/pendientes/<int:id_venta>/editar", methods=["GET"])
@admin_required
def editar_venta_get(id_venta):
    try:
        data = obtener_venta_editar_service(id_venta)
        return render_template("ventas/ventas_editar.html", **data)
    except ValueError:
        return render_template("errors/404.html"), 404
    except Exception:  # pragma: no cover
        logger.exception("Error en editar_venta_get id_venta=%s", id_venta)
        return render_template("errors/500.html"), 500


@ventas_bp.route("/ventas/pendientes/<int:id_venta>/editar", methods=["POST"])
@admin_required
@limiter.limit("20 per minute")
def editar_venta_post(id_venta):
    id_usuario = session.get("id_usuario")
    try:
        result = editar_venta_service(id_venta, request.form, id_usuario)
        return jsonify({"ok": True, "total_nuevo": result["total_nuevo"]}), 200
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception:  # pragma: no cover
        logger.exception("Error en editar_venta_post id_venta=%s id_usuario=%s", id_venta, id_usuario)
        return jsonify({"ok": False, "error": "Error interno del servidor"}), 500