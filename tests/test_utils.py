"""
Tests para utils.py — funciones de utilidad puras, sin DB.
"""
from decimal import Decimal
from datetime import date, datetime
from utils import to_json_safe, build_where, calcular_paginacion


# ---------------------------------------------------------------------------
# to_json_safe
# ---------------------------------------------------------------------------

def test_to_json_safe_convierte_decimal():
    result = to_json_safe({"precio": Decimal("19.99")})
    assert result["precio"] == 19.99
    assert isinstance(result["precio"], float)


def test_to_json_safe_convierte_date():
    hoy = date(2026, 6, 24)
    result = to_json_safe({"fecha": hoy})
    assert result["fecha"] == "2026-06-24"


def test_to_json_safe_convierte_datetime():
    dt = datetime(2026, 6, 24, 10, 30, 0)
    result = to_json_safe({"ts": dt})
    assert result["ts"].startswith("2026-06-24T10:30:00")


def test_to_json_safe_pasa_strings_sin_cambio():
    result = to_json_safe({"nombre": "Juan"})
    assert result["nombre"] == "Juan"


def test_to_json_safe_pasa_enteros_sin_cambio():
    result = to_json_safe({"id": 42})
    assert result["id"] == 42


def test_to_json_safe_none_devuelve_none():
    assert to_json_safe(None) is None


def test_to_json_safe_dict_vacio_devuelve_none():
    assert to_json_safe({}) is None


def test_to_json_safe_mezcla_tipos():
    result = to_json_safe({
        "precio": Decimal("10.50"),
        "fecha":  date(2026, 1, 1),
        "nombre": "Test",
        "id":     1,
    })
    assert result["precio"] == 10.50
    assert result["fecha"] == "2026-01-01"
    assert result["nombre"] == "Test"
    assert result["id"] == 1


# ---------------------------------------------------------------------------
# build_where
# ---------------------------------------------------------------------------

def test_build_where_sin_filtros():
    where, params = build_where([])
    assert where == ""
    assert params == []


def test_build_where_filtro_none_se_ignora():
    where, params = build_where([("id_negocio = %s", None)])
    assert where == ""
    assert params == []


def test_build_where_un_filtro():
    where, params = build_where([("id_negocio = %s", 1)])
    assert "WHERE" in where
    assert "id_negocio = %s" in where
    assert params == [1]


def test_build_where_multiples_filtros():
    where, params = build_where([
        ("id_negocio = %s", 1),
        ("eliminado = %s", 0),
    ])
    assert "WHERE" in where
    assert "AND" in where
    assert params == [1, 0]


def test_build_where_mezcla_none_y_valor():
    where, params = build_where([
        ("id_negocio = %s", None),
        ("eliminado = %s", 0),
    ])
    assert "eliminado = %s" in where
    assert "id_negocio" not in where
    assert params == [0]


# ---------------------------------------------------------------------------
# calcular_paginacion
# ---------------------------------------------------------------------------

def test_paginacion_primera_pagina():
    offset, total_paginas = calcular_paginacion(total=100, pagina=1, por_pagina=10)
    assert offset == 0
    assert total_paginas == 10


def test_paginacion_segunda_pagina():
    offset, total_paginas = calcular_paginacion(total=100, pagina=2, por_pagina=10)
    assert offset == 10
    assert total_paginas == 10


def test_paginacion_total_cero_devuelve_1_pagina():
    offset, total_paginas = calcular_paginacion(total=0, pagina=1, por_pagina=10)
    assert offset == 0
    assert total_paginas == 1


def test_paginacion_total_no_divisible():
    offset, total_paginas = calcular_paginacion(total=25, pagina=1, por_pagina=10)
    assert total_paginas == 3


def test_paginacion_exacto():
    offset, total_paginas = calcular_paginacion(total=20, pagina=1, por_pagina=10)
    assert total_paginas == 2


def test_paginacion_un_registro():
    offset, total_paginas = calcular_paginacion(total=1, pagina=1, por_pagina=10)
    assert total_paginas == 1
    assert offset == 0
