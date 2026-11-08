import logging
from flask import Blueprint, render_template, request, jsonify, session

from services.estadisticas_service import (
    dashboard_page_data_service,
    dashboard_api_service,
    exportar_estadisticas_service
)
from extensions import limiter
from services.excel_helpers import send_excel
from middleware.auth_middleware import admin_required

estadisticas_bp = Blueprint("estadisticas", __name__)
logger = logging.getLogger(__name__)


@estadisticas_bp.route("/estadisticas")
@admin_required
def estadisticas():
    try:
        data = dashboard_page_data_service()
        return render_template("admin/estadisticas.html", **data)
    except Exception:  # pragma: no cover
        logger.exception("Error en estadisticas id_usuario=%s", session.get("id_usuario"))
        return render_template("errors/500.html"), 500


@estadisticas_bp.route("/estadisticas/exportar")
@admin_required
@limiter.limit("10 per minute")
def exportar_estadisticas():
    try:
        wb, error = exportar_estadisticas_service(request.args)
        if error:
            return jsonify({"error": error}), 400
        return send_excel(wb, "estadisticas")
    except Exception:  # pragma: no cover
        logger.exception("Error en exportar_estadisticas id_usuario=%s", session.get("id_usuario"))
        return jsonify({"error": "Error al generar el archivo"}), 500


@estadisticas_bp.route("/api/estadisticas/dashboard")
@admin_required
@limiter.limit("60 per minute")
def api_dashboard():
    try:
        data, error = dashboard_api_service(request.args)
        if error:
            return jsonify({"error": error}), 400
        return jsonify(data)
    except Exception:  # pragma: no cover
        logger.exception(
            "Error en api_dashboard id_usuario=%s args=%s",
            session.get("id_usuario"), dict(request.args)
        )
        return jsonify({"error": "Error interno del servidor"}), 500