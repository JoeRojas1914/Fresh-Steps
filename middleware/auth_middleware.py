from flask import session, redirect, url_for, flash, render_template, request
from datetime import datetime, timedelta


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

TIMEOUT_CAJA = 20
TIMEOUT_ADMIN = 15


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

        return render_template("403.html"), 403