import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from dotenv import load_dotenv
from werkzeug.security import check_password_hash
from flask_wtf import CSRFProtect
from flask_talisman import Talisman
from extensions import limiter

# ================= LOGGING =================
def _setup_logging() -> None:
    is_dev   = os.getenv("FLASK_ENV") == "development"
    level    = logging.DEBUG if is_dev else logging.INFO
    fmt      = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    os.makedirs("logs", exist_ok=True)
    fh = RotatingFileHandler(
        "logs/app.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    root.addHandler(fh)

_setup_logging()
logger = logging.getLogger(__name__)



from routes.servicios_routes import servicios_bp
from routes.gastos_routes import gastos_bp
from routes.clientes_routes import clientes_bp
from routes.estadisticas_routes import estadisticas_bp
from routes.auth_routes import auth_bp
from routes.usuarios_routes import usuarios_bp
from routes.ventas_routes import ventas_bp
from middleware.auth_middleware import init_auth_middleware
from models.ventas import contar_entregas_resumen



# ================= APP =================
load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("SECRET_KEY no está configurada. Defínela en el archivo .env antes de arrancar.")
app.config.update({
    "SESSION_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SAMESITE": "Lax",
    "SESSION_COOKIE_SECURE": os.getenv("FLASK_ENV") != "development",
    "MAX_CONTENT_LENGTH": 10 * 1024 * 1024,  # 10 MB
})
csrf = CSRFProtect()
csrf.init_app(app)
limiter.init_app(app)

_is_dev = os.getenv("FLASK_ENV") == "development"
_CSP = {
    "default-src": "'self'",
    "script-src": ["'self'", "unpkg.com", "cdn.jsdelivr.net"],
    "style-src": ["'self'", "fonts.googleapis.com", "'unsafe-inline'"],
    "font-src": ["'self'", "fonts.gstatic.com"],
    "img-src": ["'self'", "data:"],
    "connect-src": ["'self'", "cdn.jsdelivr.net"],
}
Talisman(
    app,
    force_https=not _is_dev,
    strict_transport_security=not _is_dev,
    strict_transport_security_max_age=31536000,
    session_cookie_secure=not _is_dev,
    frame_options="DENY",
    content_security_policy=_CSP,
)
app.register_blueprint(servicios_bp)
app.register_blueprint(gastos_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(estadisticas_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(ventas_bp)
init_auth_middleware(app)


# ================= STATIC CACHE =================
@app.after_request
def add_cache_headers(response):
    if request.path.startswith("/static/"):
        response.cache_control.max_age = 604800  # 7 días
        response.cache_control.public = True
    return response


# ================= ERROR HANDLERS =================
@app.errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(e):
    logger.exception("Error no manejado: %s", e)
    return render_template("errors/500.html"), 500


# ================= HOME =================
@app.route("/")
def index():

    hoy = date.today().isoformat()

    if not session.get("id_usuario"):

        if session.get("pin_habilitado_fecha") == hoy:
            return redirect(url_for("auth.pin_login"))

        return redirect(url_for("auth.login"))

    dias   = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
    meses  = ["enero","febrero","marzo","abril","mayo","junio",
               "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    hoy_dt = date.today()
    fecha_bonita = f"{dias[hoy_dt.weekday()]} {hoy_dt.day} de {meses[hoy_dt.month-1]}, {hoy_dt.year}"

    total_entregas, total_pendientes = contar_entregas_resumen()
    return render_template(
        "index.html",
        total_entregas   = total_entregas,
        total_pendientes = total_pendientes,
        nombre_usuario   = session.get("nombre") or session.get("usuario", "").capitalize(),
        fecha_bonita     = fecha_bonita,
    )





# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_ENV") == "development")