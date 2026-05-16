import logging
from flask import Blueprint, render_template, request, redirect, session, jsonify, flash, url_for
from middleware.auth_middleware import admin_required

logger = logging.getLogger(__name__)
from services.usuarios_service import (
    listar_usuarios_service,
    guardar_usuario_service,
    toggle_usuario_service,
    obtener_historial_usuario_service
)

usuarios_bp = Blueprint("usuarios", __name__)


@usuarios_bp.route("/usuarios")
@admin_required
def listar_usuarios():
    q      = request.args.get("q", "").strip()
    rol    = request.args.get("rol", "")
    activo = request.args.get("activo", "")

    activo_val = None
    if activo == "1":   activo_val = 1
    elif activo == "0": activo_val = 0

    usuarios = listar_usuarios_service(
        q=q or None,
        rol=rol or None,
        activo=activo_val
    )

    return render_template(
        "usuarios.html",
        usuarios=usuarios,
        total_usuarios=len(usuarios),
        q=q, rol=rol, activo=activo
    )


@usuarios_bp.route("/usuarios/guardar", methods=["POST"])
@admin_required
def guardar_usuario():

    try:
        id_usuario_raw = request.form.get("id_usuario", "").strip()
        id_usuario     = int(id_usuario_raw) if id_usuario_raw else None

        guardar_usuario_service(
            id_usuario,
            request.form.get("usuario"),
            request.form.get("password"),
            request.form.get("rol"),
            request.form.get("pin"),
            nombre   = request.form.get("nombre")   or None,
            apellido = request.form.get("apellido") or None,
            telefono = request.form.get("telefono") or None,
            correo   = request.form.get("correo")   or None,
            cp       = request.form.get("cp")       or None,
        )
        flash("Usuario editado correctamente." if id_usuario else "Usuario creado correctamente.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception:
        logger.exception(
            "Error al guardar usuario id_usuario=%s id_solicitante=%s",
            id_usuario, session.get("id_usuario")
        )
        flash("Error inesperado al guardar el usuario.", "error")

    return redirect(url_for("usuarios.listar_usuarios"))


@usuarios_bp.route("/usuarios/toggle/<int:id>")
@admin_required
def toggle_usuario(id):
    try:
        nuevo_activo = toggle_usuario_service(id)
        if nuevo_activo is None:
            flash("No se puede cambiar el estado de este usuario.", "error")
        elif nuevo_activo:
            flash("Usuario activado correctamente.", "success")
        else:
            flash("Usuario desactivado correctamente.", "success")
    except Exception:
        logger.exception("Error en toggle_usuario id=%s id_solicitante=%s", id, session.get("id_usuario"))
        flash("Error inesperado al cambiar el estado del usuario.", "error")
    return redirect(url_for("usuarios.listar_usuarios"))


@usuarios_bp.route("/usuarios/<int:id>/historial")
@admin_required
def historial_usuario(id):
    return jsonify(obtener_historial_usuario_service(id))