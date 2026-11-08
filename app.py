import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from db import get_db
from dotenv import load_dotenv
from flask_wtf import CSRFProtect
from flask_talisman import Talisman
from flask_compress import Compress
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
    fh.addFilter(lambda r: not (r.name == "werkzeug" and r.levelno < logging.WARNING))
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
from routes.pagos_routes import pagos_bp
from middleware.auth_middleware import init_auth_middleware
from services.estadisticas_service import kpis_inicio_service
from services.permisos_service import negocios_permitidos, restringir_negocios



# ================= APP =================
load_dotenv()
app = Flask(__name__)

if os.getenv("TRUST_PROXY") == "1":  # pragma: no cover
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

from utils import dinero, fecha, fecha_hora  # noqa: E402
app.add_template_filter(dinero)
app.add_template_filter(fecha)
app.add_template_filter(fecha_hora)
app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:  # pragma: no cover
    raise RuntimeError("SECRET_KEY no está configurada. Defínela en el archivo .env antes de arrancar.")
app.config.update({
    "SESSION_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SAMESITE": "Lax",
    "SESSION_COOKIE_SECURE": os.getenv("FLASK_ENV") != "development",
    "MAX_CONTENT_LENGTH": 10 * 1024 * 1024, 
})
csrf = CSRFProtect()
csrf.init_app(app)
limiter.init_app(app)
Compress(app)

_is_dev = os.getenv("FLASK_ENV") == "development"
_CSP = {
    "default-src": "'self'",
    "script-src": "'self'",
    "style-src": ["'self'", "fonts.googleapis.com"],
    "font-src": ["'self'", "fonts.gstatic.com"],
    "img-src": ["'self'", "data:"],
    "connect-src": "'self'",
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
app.register_blueprint(pagos_bp)
init_auth_middleware(app)


# ================= STATIC CACHE =================
@app.url_defaults
def static_cache_bust(endpoint, values):
    if endpoint == "static" and "filename" in values:
        try:
            values["v"] = int(os.stat(os.path.join(app.static_folder, values["filename"])).st_mtime)
        except OSError:
            pass


@app.after_request
def add_cache_headers(response):
    if request.path.startswith("/static/"):
        response.cache_control.max_age = 604800 
        response.cache_control.public = True
    return response


# ================= ERROR HANDLERS =================
@app.errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(e):  # pragma: no cover
    logger.exception("Error no manejado: %s", e)
    return render_template("errors/500.html"), 500


_NEGOCIOS_VALIDOS = {"all", "1", "2", "3"}


def _negocio_index():
    """Negocio de los KPIs: admin elige con las pastillas ('all' o un id);
    caja siempre ve la suma de sus negocios asignados (lista de ids)."""
    if negocios_permitidos() is not None:
        return restringir_negocios()
    negocio = request.args.get("negocio", "all")
    return negocio if negocio in _NEGOCIOS_VALIDOS else "all"


# ================= HOME =================
@app.route("/")
def index():

    hoy = date.today().isoformat()

    if not session.get("id_usuario"):  # pragma: no cover

        if session.get("pin_habilitado_fecha") == hoy:
            return redirect(url_for("auth.pin_login"))

        return redirect(url_for("auth.login"))

    dias   = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
    meses  = ["enero","febrero","marzo","abril","mayo","junio",
               "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    hoy_dt = date.today()
    fecha_bonita = f"{dias[hoy_dt.weekday()]} {hoy_dt.day} de {meses[hoy_dt.month-1]}, {hoy_dt.year}"

    hora   = datetime.now().hour
    saludo = "Buenos días" if hora < 12 else "Buenas tardes" if hora < 19 else "Buenas noches"
    nombre = (session.get("nombre") or "").split()
    nombre_usuario = nombre[0] if nombre else session.get("usuario", "").capitalize()

    negocio = _negocio_index()
    kpis    = kpis_inicio_service(negocio, session.get("rol") == "admin")

    return render_template(
        "index.html",
        saludo                  = saludo,
        nombre_usuario          = nombre_usuario,
        fecha_bonita            = fecha_bonita,
        negocio_sel             = negocio,
        hoy_iso                 = hoy_dt.isoformat(),
        **kpis,
    )


@app.route("/api/index/kpis")
@limiter.limit("60 per minute")
def api_index_kpis():
    if not session.get("id_usuario"):  # pragma: no cover
        return jsonify({"error": "No autorizado"}), 401

    kpis = kpis_inicio_service(_negocio_index(), session.get("rol") == "admin")
    resp = jsonify(kpis)
    resp.cache_control.private = True
    resp.cache_control.max_age = 30
    return resp





# ================= HEALTH =================
@app.route("/health")
@limiter.limit("10 per minute")
def health():
    try:
        with get_db() as (_, cursor):
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return jsonify({"status": "ok", "db": "ok"}), 200
    except Exception:  # pragma: no cover
        logger.exception("Health check failed")
        return jsonify({"status": "error", "db": "error"}), 503


# ================= RUN =================
if __name__ == "__main__":  # pragma: no cover
    app.run(debug=os.getenv("FLASK_ENV") == "development")