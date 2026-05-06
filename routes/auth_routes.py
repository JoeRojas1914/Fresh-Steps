from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime

from services.auth_service import (
    login_password_service,
    login_pin_service
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    admin_mode = request.args.get("admin")

    if request.method == "POST":

        usuario = login_password_service(
            request.form.get("usuario"),
            request.form.get("password"),
            request.remote_addr
        )

        if usuario == "LOCKED":
            flash("🚫 Cuenta bloqueada por demasiados intentos.", "error")
            return render_template("login.html")

        if not usuario:
            flash("❌ Usuario o contraseña incorrectos", "error")
            return render_template("login.html")


        session.clear()

        if usuario["rol"] == "admin":
            session["pin_habilitado"] = True



        if admin_mode:

            session["id_usuario"] = usuario["id_usuario"]
            session["usuario"]    = usuario["usuario"]
            session["nombre"]     = usuario.get("nombre") or usuario["usuario"].capitalize()
            session["rol"]        = usuario["rol"]
            session["ultima_actividad"] = datetime.now().isoformat()

            return redirect(url_for("index"))


        return redirect(url_for("auth.pin_login"))


    return render_template("login.html")

@auth_bp.route("/pin", methods=["GET", "POST"])
def pin_login():

    if not session.get("pin_habilitado"):
        flash("Primero un administrador debe iniciar sesión.", "error")
        return redirect(url_for("auth.login"))


    if request.method == "GET":
        return render_template("pin.html")


    usuario = login_pin_service(
        request.form.get("pin"),
        request.remote_addr
    )

    if usuario == "LOCKED":
        flash("🚫 PIN bloqueado por demasiados intentos.", "error")
        return render_template("pin.html")

    if not usuario:
        flash("❌ PIN incorrecto", "error")
        return render_template("pin.html")


    session["id_usuario"] = usuario["id_usuario"]
    session["usuario"]    = usuario["usuario"]
    session["nombre"]     = usuario.get("nombre") or usuario["usuario"].capitalize()
    session["rol"]        = "caja"
    session["ultima_actividad"] = datetime.now().isoformat()

    return redirect(url_for("index"))


@auth_bp.route("/logout")
def logout():

    pin_habilitado = session.get("pin_habilitado")

    session.clear()

    if pin_habilitado:
        session["pin_habilitado"] = True
        return redirect(url_for("auth.pin_login"))

    return redirect(url_for("auth.login"))