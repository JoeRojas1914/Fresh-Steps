"""
Modo "Año" de estadísticas (series por mes) y marcas/tipos de calzado.
"""
from datetime import date

import pytest

from services.estadisticas_service import (
    dashboard_api_service,
    dashboard_page_data_service,
    exportar_estadisticas_service,
)
from models.estadisticas import obtener_top_calzado
from models.estadisticas_ventas import generar_periodos

HOY = date.today()
ANIO = HOY.year


def _api_anio(anio=ANIO, id_negocio="all", **extra):
    return dashboard_api_service({
        "inicio": f"{anio}-01-01", "fin": f"{anio}-12-31",
        "id_negocio": id_negocio, "modo": "anio", **extra,
    })


# ── Cubetas por mes ──────────────────────────────────────────────────────────

def test_generar_periodos_mes_cruza_cambio_de_anio():
    periodos = generar_periodos(date(2025, 11, 15), date(2026, 2, 3), "mes")
    assert [p["label"] for p in periodos] == ["nov 2025", "dic 2025", "ene 2026", "feb 2026"]
    assert [p["clave"] for p in periodos] == [202511, 202512, 202601, 202602]


def test_generar_periodos_semana_conserva_clave_iso():
    periodos = generar_periodos(date(2026, 11, 2), date(2026, 11, 15), "semana")
    assert [p["clave"] for p in periodos] == [202645, 202646]


# ── API en modo Año ──────────────────────────────────────────────────────────

def test_api_anio_devuelve_doce_meses(app):
    data, error = _api_anio()
    assert error is None
    for serie in ("ventas_semanales", "ingresos_semanales", "unidades_semanales"):
        assert len(data[serie]) == 12
        assert data[serie][0]["label"] == f"ene {ANIO}"
    assert len(data["gastos_semanales"]["labels"]) == 12


def test_api_anio_compara_contra_anio_anterior(app):
    data, _ = _api_anio()
    assert data["periodo_anterior"]["inicio"] == f"{ANIO - 1}-01-01"
    assert data["periodo_actual"]["fin"] == min(HOY, date(ANIO, 12, 31)).isoformat()


@pytest.mark.parametrize("agrupacion", ["proveedor", "categoria"])
def test_api_anio_gastos_por_mes_incluyen_gasto(app, gasto_test, agrupacion):
    # gasto_test: $100 el 1 de enero de 2030 → cae en la cubeta de enero
    data, _ = _api_anio(2030, agrupacion_gastos=agrupacion)
    enero = sum(d["data"][0] for d in data["gastos_semanales"]["datasets"])
    assert enero >= 100


def test_api_anio_cuenta_la_venta_en_su_mes(app, venta_pendiente):
    data, _ = _api_anio()
    assert data["ventas_semanales"][HOY.month - 1]["total"] >= 1
    assert data["unidades_semanales"][HOY.month - 1]["total"] >= 1


def test_api_anio_rechaza_mas_de_un_anio():
    _, error = dashboard_api_service({
        "inicio": "2025-01-01", "fin": "2026-01-01", "modo": "anio",
    })
    assert error is not None


def test_api_sin_modo_anio_sigue_limitado_a_seis_meses():
    _, error = dashboard_api_service({
        "inicio": f"{ANIO}-01-01", "fin": f"{ANIO}-12-31", "modo": "personalizado",
    })
    assert error is not None


def test_api_granularidad_mes_fuera_de_anio_usa_semanas(app):
    data, _ = dashboard_api_service({
        "inicio": "2026-06-01", "fin": "2026-06-30", "granularidad": "mes", "modo": "mes",
    })
    assert isinstance(data["ventas_semanales"][0]["label"], list)   # etiqueta de semana


# ── Selector de años y exportación ───────────────────────────────────────────

def test_page_data_incluye_anio_actual_primero(app):
    anios = dashboard_page_data_service()["anios"]
    assert anios[0] == ANIO
    assert anios == sorted(anios, reverse=True)


def test_exportar_anio_completo_por_mes(app):
    wb, error = exportar_estadisticas_service({"inicio": f"{ANIO}-01-01", "fin": f"{ANIO}-12-31"})
    assert error is None
    ws = wb["Series por período"]
    meses = [ws.cell(row=r, column=1).value for r in range(4, 16)]
    assert meses[0] == f"ene {ANIO}" and meses[-1] == f"dic {ANIO}"


# ── Calzado ──────────────────────────────────────────────────────────────────

def test_top_calzado_cuenta_marca_y_tipo(app, venta_pendiente):
    marcas = {m["nombre"]: m["total"] for m in obtener_top_calzado(HOY, HOY, "marca")}
    tipos  = {t["nombre"]: t["total"] for t in obtener_top_calzado(HOY, HOY, "tipo")}
    assert marcas.get("Nike", 0) >= 1
    assert tipos.get("Tenis", 0) >= 1


def test_top_calzado_rechaza_campo_no_permitido():
    with pytest.raises(ValueError):
        obtener_top_calzado(HOY, HOY, "id_articulo; DROP TABLE venta")


def test_api_calzado_solo_con_todos_o_calzado(app, venta_pendiente):
    hoy = HOY.isoformat()
    con, _ = dashboard_api_service({"inicio": hoy, "fin": hoy, "id_negocio": "all", "modo": "dia"})
    sin, _ = dashboard_api_service({"inicio": hoy, "fin": hoy, "id_negocio": "2", "modo": "dia"})
    assert any(m["nombre"] == "Nike" for m in con["calzado_marcas"])
    assert sin["calzado_marcas"] == [] and sin["calzado_tipos"] == []


# ── Unir nombres mal escritos ────────────────────────────────────────────────

from services.estadisticas_service import agrupar_nombres_similares  # noqa: E402


def _top(*pares, limite=8):
    filas = [{"nombre": n, "total": t} for n, t in pares]
    return {g["nombre"]: g["total"] for g in agrupar_nombres_similares(filas, limite)}


def test_agrupar_ignora_mayusculas_espacios_y_acentos():
    assert _top(("Nike", 5), ("NIKE", 2), (" nike ", 1)) == {"Nike": 8}
    assert _top(("New Balance", 3), ("new-balance", 1), ("NewBalance", 1)) == {"New Balance": 5}
    assert _top(("Bota vaquera", 2), ("bóta vaquera", 1)) == {"Bota vaquera": 3}


def test_agrupar_une_errores_de_dedo_con_la_forma_mas_comun():
    assert _top(("Adidas", 6), ("Addidas", 1), ("Adidsa", 1)) == {"Adidas": 8}   # letra de más / volteadas
    assert _top(("Converse", 4), ("Convrese", 1), ("Cnverse", 1)) == {"Converse": 6}
    assert _top(("Skechers", 3), ("Skechres", 1)) == {"Skechers": 4}


def test_agrupar_no_mezcla_nombres_cortos_distintos():
    assert _top(("Fila", 2), ("Vila", 1), ("Puma", 1)) == {"Fila": 2, "Vila": 1, "Puma": 1}


def test_agrupar_no_mezcla_marcas_diferentes():
    assert _top(("Nike", 3), ("Adidas", 2), ("Reebok", 1)) == {"Nike": 3, "Adidas": 2, "Reebok": 1}


def test_agrupar_sin_marca_queda_aparte():
    assert _top(("Sin marca", 2), ("Sinmarca", 1)) == {"Sin marca": 2, "Sinmarca": 1}


def test_agrupar_capitaliza_si_todo_esta_en_minusculas_o_mayusculas():
    assert _top(("vans", 3)) == {"Vans": 3}
    assert _top(("TENIS", 3)) == {"Tenis": 3}
    assert _top(("DC Shoes", 1)) == {"DC Shoes": 1}


def test_agrupar_recorta_al_limite_despues_de_unir():
    # "Adidass" suelto quedaría fuera del top 1, pero unido a "Adidas" suma más que Puma
    assert _top(("Adidas", 2), ("Puma", 3), ("Adidass", 2), limite=1) == {"Adidas": 4}
