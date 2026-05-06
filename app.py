import os
import logging
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from dotenv import load_dotenv
from werkzeug.security import check_password_hash
from flask_wtf import CSRFProtect

# ================= LOGGING =================
logging.basicConfig(
    level=logging.DEBUG,      
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)



from routes.servicios_routes import servicios_bp
from routes.gastos_routes import gastos_bp
from routes.clientes_routes import clientes_bp
from routes.estadisticas_routes import estadisticas_bp
from routes.auth_routes import auth_bp
from routes.usuarios_routes import usuarios_bp
from routes.ventas_routes import ventas_bp
from middleware.auth_middleware import init_auth_middleware
from ventas import contar_entregas_pendientes, contar_entregas_listas



# ================= APP =================
load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
csrf = CSRFProtect()
csrf.init_app(app)
app.register_blueprint(servicios_bp)
app.register_blueprint(gastos_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(estadisticas_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(ventas_bp)
init_auth_middleware(app)


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

    return render_template(
        "index.html",
        total_entregas   = contar_entregas_listas(),
        total_pendientes = contar_entregas_pendientes(),
        nombre_usuario   = session.get("nombre") or session.get("usuario", "").capitalize(),
        fecha_bonita     = fecha_bonita,
    )





# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)