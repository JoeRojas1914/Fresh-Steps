import logging
from flask import Blueprint, render_template, jsonify, session, request
from datetime import date

from services.ventas_service import (
    listar_ventas_listas_service,
    registrar_pago_final_service,
    listar_entregas_pendientes_service,
    guardar_venta_service,
)
from ventas import (
    marcar_entregada,
    obtener_venta,
    obtener_detalles_venta,
)

logger = logging.getLogger(__name__)

ventas_bp = Blueprint("ventas", __name__)


@ventas_bp.route("/ventas/guardar", methods=["POST"])
def guardar_venta():
    id_usuario = session.get("id_usuario")
    id_venta, error = guardar_venta_service(request.form, id_usuario)

    if error:
        return jsonify({"ok": False, "error": error}), 400

    return jsonify({"ok": True, "id_venta": id_venta}), 200


@ventas_bp.route("/ventas")
def ventas():
    return render_template("ventas_crear.html")


@ventas_bp.route("/ventas/entregar/<int:id_venta>", methods=["POST"])
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

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


@ventas_bp.route("/ventas/ticket/<int:id_venta>")
def venta_ticket(id_venta):
    venta = obtener_venta(id_venta)

    detalles_dict = obtener_detalles_venta([id_venta])
    detalles = detalles_dict.get(id_venta, [])  

    return render_template(
        "ticket_venta.html",
        venta=venta,
        detalles=detalles
    )

@ventas_bp.route("/ventas/listas")
def ventas_listas():
    id_negocio = request.args.get("id_negocio") or None

    data = listar_ventas_listas_service(id_negocio)

    return render_template(
        "ventas_listas.html",
        **data
    )


@ventas_bp.route("/ventas/pendientes")
def ventas_pendientes():
    try:
        id_negocio = request.args.get("id_negocio", type=int)

        data = listar_entregas_pendientes_service(id_negocio)

        logger.debug("ventas_pendientes data: %s", data)

        return render_template(
            "ventas_pendientes.html",
            **data
        )

    except Exception as e:
        logger.error("ERROR EN ventas_pendientes: %s", e, exc_info=True)
        return str(e), 500


@ventas_bp.route("/ventas/marcar-lista/<int:id_venta>", methods=["POST"])
def marcar_lista(id_venta):
    from ventas import marcar_como_lista

    try:
        if marcar_como_lista(id_venta):
            return jsonify({
                "ok": True,
                "message": "Venta marcada como lista correctamente"
            })
        else:
            return jsonify({
                "ok": False,
                "error": "La venta ya está lista o fue entregada"
            })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500
    

@ventas_bp.route("/ventas/detalles/<int:id_venta>")
def detalles_venta(id_venta):
    from ventas import obtener_detalles_venta

    detalles = obtener_detalles_venta([id_venta])  
    return jsonify(detalles.get(id_venta, []))

@ventas_bp.route("/ventas/pago-final", methods=["POST"])
def registrar_pago_final():
    data = request.json
    id_usuario = session.get("id_usuario")

    try:
        ok, mensaje = registrar_pago_final_service(data, id_usuario)

        if not ok:
            return jsonify({
                "ok": False,
                "error": mensaje
            }), 400

        return jsonify({
            "ok": True,
            "message": mensaje
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500
    

@ventas_bp.route("/ventas/eliminar/<int:id_venta>", methods=["POST"])
def eliminar_venta_route(id_venta):
    from services.ventas_service import eliminar_venta_service

    id_usuario = session.get("id_usuario")
    rol = session.get("rol")

    if not id_usuario:
        return jsonify({
            "ok": False,
            "error": "No autenticado"
        }), 401

    if rol != "admin":
        return jsonify({
            "ok": False,
            "error": "No autorizado"
        }), 403

    try:
        ok, mensaje = eliminar_venta_service(id_venta)

        if not ok:
            return jsonify({
                "ok": False,
                "error": mensaje
            }), 400

        return jsonify({
            "ok": True,
            "message": mensaje
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500