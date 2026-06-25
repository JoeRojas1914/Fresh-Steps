from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime

from services.auth_service import (
    login_password_service,
    login_pin_service,
    invalidar_session_token_service,
    registrar_logout_service,
)
from extensions import limiter

auth_bp = Blueprint("auth", __name__)


def _poblar_sesion(usuario: dict, rol: str) -> None:
    session["id_usuario"]       = usuario["id_usuario"]
    session["usuario"]          = usuario["usuario"]
    session["nombre"]           = usuario.get("nombre") or ""
    session["apellido"]         = usuario.get("apellido") or ""
    session["rol"]              = rol
    session["ultima_actividad"] = datetime.now().isoformat()
    session["session_token"]    = usuario.get("_session_token")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():

    admin_mode = request.args.get("admin")

    if request.method == "POST":

        usuario = login_password_service(
            request.form.get("usuario"),
            request.form.get("password"),
            request.remote_addr
        )

        if usuario == "LOCKED":
            flash("Cuenta bloqueada por demasiados intentos.", "error")
            return render_template("auth/login.html")

        if not usuario:
            flash("Usuario o contraseña incorrectos", "error")
            return render_template("auth/login.html")


        session.clear()

        if usuario["rol"] == "admin":
            session["pin_habilitado"] = True



        if admin_mode == "1":
            _poblar_sesion(usuario, usuario["rol"])
            return redirect(url_for("index"))


        return redirect(url_for("auth.pin_login"))


    return render_template("auth/login.html")

@auth_bp.route("/pin", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def pin_login():

    if not session.get("pin_habilitado"):  # pragma: no cover
        flash("Primero un administrador debe iniciar sesión.", "error")
        return redirect(url_for("auth.login"))


    if request.method == "GET":
        return render_template("auth/pin.html")


    usuario = login_pin_service(
        request.form.get("pin"),
        request.remote_addr
    )

    if usuario == "LOCKED":
        flash("PIN bloqueado por demasiados intentos. Inténtalo de nuevo en 30 minutos.", "error")
        return render_template("auth/pin.html")

    if not usuario:
        flash("PIN incorrecto.", "error")
        return render_template("auth/pin.html")


    session.clear()
    session["pin_habilitado"] = True
    _poblar_sesion(usuario, "caja")

    return redirect(url_for("index"))


@auth_bp.route("/logout")
def logout():
    pin_habilitado = session.get("pin_habilitado")
    id_usuario     = session.get("id_usuario")
    username       = session.get("usuario")

    if id_usuario:
        if username:
            registrar_logout_service(id_usuario, username, request.remote_addr)
        invalidar_session_token_service(id_usuario)

    session.clear()

    if pin_habilitado:
        session["pin_habilitado"] = True
        return redirect(url_for("auth.pin_login"))

    return redirect(url_for("auth.login"))
