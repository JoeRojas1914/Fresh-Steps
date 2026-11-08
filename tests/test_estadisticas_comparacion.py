"""
Comparación "mismo avance" de la página de estadísticas.
Un período en curso se compara solo contra el mismo tramo del período anterior.
"""
from datetime import date

import pytest

from services.estadisticas_service import (
    _periodo_comparacion,
    _pct_cambio,
    dashboard_api_service,
)
from models.estadisticas import obtener_top_clientes, obtener_ingresos_por_negocio

D = date.fromisoformat


@pytest.mark.parametrize("inicio, fin, modo, hoy, actual, anterior", [
    # Mes en curso: 1–5 nov contra 1–5 oct
    ("2026-11-01", "2026-11-30", "mes", "2026-11-05", ("2026-11-01", "2026-11-05"), ("2026-10-01", "2026-10-05")),
    # Mes terminado: octubre completo contra septiembre completo
    ("2026-10-01", "2026-10-31", "mes", "2026-11-05", ("2026-10-01", "2026-10-31"), ("2026-09-01", "2026-09-30")),
    # Septiembre (30 días) terminado contra agosto completo (31 días)
    ("2026-09-01", "2026-09-30", "mes", "2026-11-05", ("2026-09-01", "2026-09-30"), ("2026-08-01", "2026-08-31")),
    # Corte el 31 de marzo en curso: febrero se ajusta a su último día
    ("2026-03-01", "2026-03-31", "mes", "2026-03-31", ("2026-03-01", "2026-03-31"), ("2026-02-01", "2026-02-28")),
    # Corte el 30 de marzo: febrero llega hasta el 28
    ("2026-03-01", "2026-03-31", "mes", "2026-03-30", ("2026-03-01", "2026-03-30"), ("2026-02-01", "2026-02-28")),
    # Semana a medias (lun 2 – jue 5 nov) contra lun 26 – jue 29 oct
    ("2026-11-02", "2026-11-08", "semana", "2026-11-05", ("2026-11-02", "2026-11-05"), ("2026-10-26", "2026-10-29")),
    # Día: mismo día de la semana anterior
    ("2026-11-05", "2026-11-05", "dia", "2026-11-05", ("2026-11-05", "2026-11-05"), ("2026-10-29", "2026-10-29")),
    # Personalizado: período anterior de igual duración (sin recorte)
    ("2026-11-01", "2026-11-10", "personalizado", "2026-11-05", ("2026-11-01", "2026-11-10"), ("2026-10-22", "2026-10-31")),
    # Sin modo: comportamiento original
    ("2026-11-01", "2026-11-30", None, "2026-11-05", ("2026-11-01", "2026-11-30"), ("2026-10-02", "2026-10-31")),
    # Mes futuro: no se recorta
    ("2026-12-01", "2026-12-31", "mes", "2026-11-05", ("2026-12-01", "2026-12-31"), ("2026-11-01", "2026-11-30")),
    # Año en curso: 1 ene – 8 nov contra el mismo tramo del año anterior
    ("2026-01-01", "2026-12-31", "anio", "2026-11-08", ("2026-01-01", "2026-11-08"), ("2025-01-01", "2025-11-08")),
    # Año terminado: completo contra completo
    ("2025-01-01", "2025-12-31", "anio", "2026-11-08", ("2025-01-01", "2025-12-31"), ("2024-01-01", "2024-12-31")),
    # Corte el 29 de febrero (bisiesto): el año anterior llega al 28
    ("2028-01-01", "2028-12-31", "anio", "2028-02-29", ("2028-01-01", "2028-02-29"), ("2027-01-01", "2027-02-28")),
])
def test_periodo_comparacion(inicio, fin, modo, hoy, actual, anterior):
    act, ant = _periodo_comparacion(D(inicio), D(fin), modo, D(hoy))
    assert act == (D(actual[0]), D(actual[1]))
    assert ant == (D(anterior[0]), D(anterior[1]))


def test_pct_cambio_sin_base_positiva_es_none():
    assert _pct_cambio(100, 0) is None
    assert _pct_cambio(50, -100) is None      # ganancia negativa: el signo engañaría
    assert _pct_cambio(150, 100) == 50.0


def test_api_devuelve_periodo_actual_y_sin_saldo_pct():
    resultado, error = dashboard_api_service({
        "inicio": "2026-06-01", "fin": "2026-06-30", "modo": "mes",
    })
    assert error is None
    assert resultado["periodo_actual"] == {"inicio": "2026-06-01", "fin": "2026-06-30"}
    assert resultado["periodo_anterior"] == {"inicio": "2026-05-01", "fin": "2026-05-31"}
    assert "saldo_pct" not in resultado["kpis"]


def test_api_modo_invalido_usa_comportamiento_original():
    resultado, error = dashboard_api_service({
        "inicio": "2026-06-01", "fin": "2026-06-30", "modo": "xyz",
    })
    assert error is None
    assert resultado["periodo_anterior"] == {"inicio": "2026-05-02", "fin": "2026-05-31"}


def test_top_clientes_ordenado_por_monto():
    top = obtener_top_clientes(date(2020, 1, 1), date(2030, 12, 31), "all")
    montos = [c["total_gastado"] for c in top]
    assert montos == sorted(montos, reverse=True)


def test_ingresos_por_negocio_incluye_id():
    filas = obtener_ingresos_por_negocio(date(2020, 1, 1), date(2030, 12, 31))
    for f in filas:
        assert f["id_negocio"] in (1, 2, 3)
