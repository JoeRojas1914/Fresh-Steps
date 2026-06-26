import logging
from flask import Blueprint, render_template, request, session, jsonify
from middleware.auth_middleware import admin_required
from extensions import limiter

logger = logging.getLogger(__name__)
from services.usuarios_service import (
    listar_usuarios_service,
    guardar_usuario_service,
    toggle_usuario_service,
    obtener_historial_usuario_service
)
from models.usuario import obtener_usuario_por_id

usuarios_bp = Blueprint("usuarios", __name__)


@usuarios_bp.route("/usuarios")
@admin_required
def listar_usuarios():
    q                = request.args.get("q", "").strip()
    pagina           = request.args.get("pagina", 1, type=int)
    mostrar_inactivos = request.args.get("inactivos") == "1"
    activo_val       = None if mostrar_inactivos else 1

    data = listar_usuarios_service(
        q=q or None,
        activo=activo_val,
        pagina=pagina,
    )

    ctx = dict(
        usuarios=data["usuarios"],
        total_usuarios=data["total"],
        total_paginas=data["total_paginas"],
        pagina=pagina,
        q=q,
        mostrar_inactivos=mostrar_inactivos,
    )
    if request.args.get("partial") == "1":
        return render_template("admin/_usuarios_partial.html", **ctx)
    return render_template("admin/usuarios.html", **ctx)


@usuarios_bp.route("/usuarios/guardar", methods=["POST"])
@admin_required
@limiter.limit("20 per minute")
def guardar_usuario():
    id_usuario = None
    try:
        data           = request.json or {}
        id_usuario_raw = (data.get("id_usuario") or "")
        id_usuario     = int(id_usuario_raw) if id_usuario_raw else None

        guardar_usuario_service(
            id_usuario,
            (data.get("usuario") or "").strip(),
            data.get("password"),
            data.get("rol"),
            data.get("pin"),
            nombre   = (data.get("nombre")   or "").strip() or None,
            apellido = (data.get("apellido") or "").strip() or None,
            telefono = data.get("telefono") or None,
            correo   = data.get("correo")   or None,
            cp       = (data.get("cp")       or "").strip() or None,
        )
        msg = "Usuario editado correctamente." if id_usuario else "Usuario creado correctamente."
        return jsonify({"ok": True, "message": msg})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)})
    except Exception:  # pragma: no cover
        logger.exception(
            "Error al guardar usuario id_usuario=%s id_solicitante=%s",
            id_usuario, session.get("id_usuario")
        )
        return jsonify({"ok": False, "error": "Error inesperado al guardar el usuario."}), 500


@usuarios_bp.route("/usuarios/toggle/<int:id>", methods=["POST"])
@admin_required
@limiter.limit("20 per minute")
def toggle_usuario(id):
    try:
        nuevo_activo = toggle_usuario_service(id)
        if nuevo_activo is None:
            return jsonify({"ok": False, "error": "No se puede cambiar el estado de este usuario."})
        msg = "Usuario activado correctamente." if nuevo_activo else "Usuario desactivado correctamente."
        return jsonify({"ok": True, "message": msg})
    except Exception:  # pragma: no cover
        logger.exception("Error en toggle_usuario id=%s id_solicitante=%s", id, session.get("id_usuario"))
        return jsonify({"ok": False, "error": "Error inesperado al cambiar el estado del usuario."}), 500


@usuarios_bp.route("/usuarios/<int:id>/historial")
@admin_required
def historial_usuario(id):
    return jsonify(obtener_historial_usuario_service(id))


@usuarios_bp.route("/mi-perfil")
def mi_perfil():
    id_usuario = session.get("id_usuario")
    usuario    = obtener_usuario_por_id(id_usuario)
    return render_template("usuario/mi_perfil.html", usuario=usuario)