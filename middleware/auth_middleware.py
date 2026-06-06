import logging
from functools import wraps
from flask import session, redirect, url_for, flash, render_template, request, jsonify
from datetime import datetime, timedelta
from config import TIMEOUT_ADMIN, TIMEOUT_CAJA
from models.usuario import obtener_session_token

logger = logging.getLogger(__name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("rol") != "admin":
            wants_json = (
                request.accept_mimetypes.best_match(
                    ["application/json", "text/html"]
                ) == "application/json"
            )
            if wants_json:
                return jsonify({"ok": False, "error": "No autorizado"}), 403
            return render_template("errors/403.html"), 403
        return f(*args, **kwargs)
    return decorated


RUTAS_PUBLICAS = [
    "auth.login",
    "static"
]

RUTAS_CAJA = {
    "index",

    "ventas.ventas",
    "ventas.ventas_listas",
    "ventas.entregar_venta",
    "ventas.ventas_pendientes",
    "ventas.marcar_lista",
    "ventas.venta_ticket",
    "ventas.registrar_pago_final",
    "ventas.detalles_venta", 

    "clientes.api_clientes",
    "clientes.api_crear_cliente",
    "servicios.api_servicios",

    "ventas.guardar_venta",

    "auth.logout",
}



def init_auth_middleware(app):

    @app.before_request
    def control_acceso():

        endpoint = request.endpoint

        if endpoint is None or endpoint.startswith("static"):
            return


        pin_habilitado = session.get("pin_habilitado", False)


        if endpoint == "auth.pin_login":

            if pin_habilitado:
                return

            return redirect(url_for("auth.login"))


        if endpoint == "auth.login" and pin_habilitado and not request.args.get("admin"):
            return redirect(url_for("auth.pin_login"))


        if endpoint in RUTAS_PUBLICAS:
            return


        if not session.get("id_usuario"):

            if pin_habilitado:
                return redirect(url_for("auth.pin_login"))

            return redirect(url_for("auth.login"))


        try:
            token_bd = obtener_session_token(session["id_usuario"])
        except Exception:
            logger.exception("Error al verificar session token id_usuario=%s", session.get("id_usuario"))
            session.clear()
            flash("Error de sesión. Por favor vuelve a ingresar.", "error")
            return redirect(url_for("auth.login"))

        if token_bd != session.get("session_token"):
            session.clear()
            flash("Tu sesión fue iniciada en otro dispositivo.", "error")
            return redirect(url_for("auth.login"))


        ultima = session.get("ultima_actividad")

        if ultima:

            ultima = datetime.fromisoformat(ultima)
            ahora = datetime.now()

            limite = (
                TIMEOUT_ADMIN if session.get("rol") == "admin"
                else TIMEOUT_CAJA
            )

            if ahora - ultima > timedelta(minutes=limite):

                habilitado = session.get("pin_habilitado")

                session.clear()

                flash("Sesión cerrada por inactividad. Ingresa tu PIN", "timeout")

                if habilitado:
                    session["pin_habilitado"] = True
                    return redirect(url_for("auth.pin_login"))

                return redirect(url_for("auth.login"))


        session["ultima_actividad"] = datetime.now().isoformat()


        if session.get("rol") == "admin":
            return

        if session.get("rol") == "caja" and endpoint in RUTAS_CAJA:
            return

        return render_template("errors/403.html"), 403