from flask import Blueprint, render_template, request, jsonify


from services.estadisticas_service import (
    dashboard_page_data_service,
    dashboard_api_service
)

estadisticas_bp = Blueprint("estadisticas", __name__)


@estadisticas_bp.route("/estadisticas")
def estadisticas():

    data = dashboard_page_data_service()

    return render_template("estadisticas.html", **data)


@estadisticas_bp.route("/api/estadisticas/dashboard")
def api_dashboard():

    data, error = dashboard_api_service(request.args)

    if error:
        return jsonify({"error": error}), 400

    return jsonify(data)