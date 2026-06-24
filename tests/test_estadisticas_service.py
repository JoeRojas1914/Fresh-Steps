"""
Tests para services/estadisticas_service.py
Cubre validación de inputs, valores de retorno y comportamiento ante DB vacía.
"""
from datetime import date, timedelta
from services.estadisticas_service import (
    dashboard_page_data_service,
    dashboard_api_service,
    exportar_estadisticas_service,
    MAX_DIAS_RANGO,
)


# ---------------------------------------------------------------------------
# dashboard_page_data_service
# ---------------------------------------------------------------------------

def test_dashboard_page_data_devuelve_claves():
    data = dashboard_page_data_service()
    assert "total_clientes"  in data
    assert "total_servicios" in data
    assert "negocios"        in data
    assert "fecha_inicio"    in data
    assert "fecha_fin"       in data


def test_dashboard_page_data_fechas_son_strings():
    data = dashboard_page_data_service()
    assert isinstance(data["fecha_inicio"], str)
    assert isinstance(data["fecha_fin"],    str)


def test_dashboard_page_data_fecha_inicio_es_primer_dia_mes():
    data = dashboard_page_data_service()
    hoy  = date.today()
    assert data["fecha_inicio"] == hoy.replace(day=1).isoformat()


# ---------------------------------------------------------------------------
# dashboard_api_service — validación de inputs
# ---------------------------------------------------------------------------

def test_api_sin_fechas_devuelve_error():
    resultado, error = dashboard_api_service({})
    assert resultado is None
    assert error is not None


def test_api_formato_fecha_invalido():
    resultado, error = dashboard_api_service({"inicio": "01/01/2026", "fin": "30/06/2026"})
    assert resultado is None
    assert "fecha" in error.lower()


def test_api_fin_menor_que_inicio():
    resultado, error = dashboard_api_service({"inicio": "2026-06-01", "fin": "2026-05-01"})
    assert resultado is None
    assert error is not None


def test_api_rango_excede_maximo():
    inicio = date(2026, 1, 1)
    fin    = inicio + timedelta(days=MAX_DIAS_RANGO + 1)
    resultado, error = dashboard_api_service({
        "inicio": inicio.isoformat(),
        "fin":    fin.isoformat(),
    })
    assert resultado is None
    assert str(MAX_DIAS_RANGO) in error


def test_api_tipo_fecha_invalido_no_falla():
    resultado, error = dashboard_api_service({
        "inicio":     "2026-06-01",
        "fin":        "2026-06-30",
        "tipo_fecha": "columna_inexistente",
    })
    assert error is None
    assert resultado is not None


def test_api_rango_valido_devuelve_claves():
    resultado, error = dashboard_api_service({
        "inicio": "2026-06-01",
        "fin":    "2026-06-30",
    })
    assert error is None
    assert "kpis"             in resultado
    assert "ventas_semanales" in resultado
    assert "periodo_anterior" in resultado


def test_api_kpis_tienen_claves_esperadas():
    resultado, _ = dashboard_api_service({
        "inicio": "2026-06-01",
        "fin":    "2026-06-30",
    })
    kpis = resultado["kpis"]
    for clave in ("ingresos", "gastos", "ganancia", "num_ventas", "ticket_promedio", "saldo_por_cobrar"):
        assert clave in kpis


def test_api_kpis_son_numericos_con_db_vacia():
    resultado, _ = dashboard_api_service({
        "inicio": "2020-01-01",
        "fin":    "2020-01-31",
    })
    kpis = resultado["kpis"]
    assert kpis["ingresos"]   >= 0
    assert kpis["gastos"]     >= 0
    assert kpis["num_ventas"] >= 0


def test_api_negocio_especifico():
    resultado, error = dashboard_api_service({
        "inicio":     "2026-06-01",
        "fin":        "2026-06-30",
        "id_negocio": "1",
    })
    assert error is None
    assert resultado is not None


def test_api_agrupacion_gastos_categoria():
    resultado, error = dashboard_api_service({
        "inicio":            "2026-06-01",
        "fin":               "2026-06-30",
        "agrupacion_gastos": "categoria",
    })
    assert error is None
    assert "gastos_semanales" in resultado


def test_api_agrupacion_gastos_invalida_usa_default():
    resultado, error = dashboard_api_service({
        "inicio":            "2026-06-01",
        "fin":               "2026-06-30",
        "agrupacion_gastos": "valor_raro",
    })
    assert error is None
    assert resultado is not None


# ---------------------------------------------------------------------------
# exportar_estadisticas_service — validación + respuesta Flask
# ---------------------------------------------------------------------------

def test_exportar_sin_fechas_devuelve_error():
    resp, error = exportar_estadisticas_service({})
    assert resp is None
    assert error is not None


def test_exportar_fin_menor_que_inicio():
    resp, error = exportar_estadisticas_service({
        "inicio": "2026-06-30",
        "fin":    "2026-06-01",
    })
    assert resp is None
    assert error is not None


def test_exportar_rango_excede_maximo():
    inicio = date(2026, 1, 1)
    fin    = inicio + timedelta(days=MAX_DIAS_RANGO + 1)
    resp, error = exportar_estadisticas_service({
        "inicio": inicio.isoformat(),
        "fin":    fin.isoformat(),
    })
    assert resp is None
    assert str(MAX_DIAS_RANGO) in error


def test_exportar_rango_valido_devuelve_response(app):
    with app.test_request_context("/"):
        resp, error = exportar_estadisticas_service({
            "inicio": "2026-06-01",
            "fin":    "2026-06-30",
        })
    assert error is None
    assert resp is not None
    assert resp.content_type == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
