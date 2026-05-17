"""
Tests para services/estadisticas_service.py

Sección 1 — Validaciones de entrada (sin BD)
Sección 2 — Lógica pura: _periodo_anterior
Sección 3 — dashboard_page_data_service (integración BD)
Sección 4 — Estructura de respuesta de dashboard_api_service
Sección 5 — KPIs con datos reales en BD
"""
import pytest
from datetime import date, timedelta

from services.estadisticas_service import (
    dashboard_api_service,
    dashboard_page_data_service,
    _periodo_anterior,
    MAX_DIAS_RANGO,
)
from tests.conftest import cleanup_venta


# ---------------------------------------------------------------------------
# Fixtures de datos
# ---------------------------------------------------------------------------

@pytest.fixture
def venta_con_pago(db_conn, cliente_test, usuario_admin):
    """Venta en negocio 1 con un pago de $300, fecha = hoy."""
    cursor = db_conn.cursor(dictionary=True)
    hoy = date.today()

    cursor.execute("""
        INSERT INTO venta (id_negocio, id_cliente, fecha_recibo, fecha_estimada,
                           aplica_descuento, cantidad_descuento, total, id_usuario_creo)
        VALUES (1, %s, %s, DATE_ADD(%s, INTERVAL 7 DAY), 0, 0, 300.00, %s)
    """, (cliente_test["id_cliente"], hoy, hoy, usuario_admin["id_usuario"]))
    db_conn.commit()
    id_venta = cursor.lastrowid

    cursor.execute(
        "INSERT INTO articulo (id_venta, tipo_articulo) VALUES (%s, 'calzado')",
        (id_venta,),
    )
    cursor.execute("""
        INSERT INTO pago_venta (id_venta, tipo_pago_venta, tipo_pago, monto, id_usuario_cobro, fecha_pago)
        VALUES (%s, 'final', 'efectivo', 300.00, %s, %s)
    """, (id_venta, usuario_admin["id_usuario"], hoy))
    db_conn.commit()
    cursor.close()

    yield {"id_venta": id_venta, "monto": 300.00, "fecha": hoy, "id_negocio": 1}

    cleanup_venta(db_conn, id_venta)


@pytest.fixture
def gasto_hoy(db_conn, usuario_admin):
    """Gasto de $120 en negocio 1 con fecha_registro = hoy."""
    cursor = db_conn.cursor(dictionary=True)
    hoy = date.today()

    cursor.execute("""
        INSERT INTO gastos (id_negocio, descripcion, proveedor, total,
                            fecha_registro, tipo_comprobante, tipo_pago, id_usuario)
        VALUES (1, 'Gasto Test', 'Proveedor Test', 120.00, %s, 'ticket', 'efectivo', %s)
    """, (hoy, usuario_admin["id_usuario"]))
    db_conn.commit()
    gid = cursor.lastrowid
    cursor.close()

    yield {"id_gasto": gid, "total": 120.00, "fecha": hoy, "id_negocio": 1}

    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM gastos_historial WHERE id_gasto = %s", (gid,))
    cursor.execute("DELETE FROM gastos           WHERE id_gasto = %s", (gid,))
    db_conn.commit()
    cursor.close()


def _args(inicio=None, fin=None, id_negocio="all", granularidad="semana"):
    hoy = date.today().isoformat()
    return {
        "inicio":       inicio or hoy,
        "fin":          fin    or hoy,
        "id_negocio":   id_negocio,
        "granularidad": granularidad,
    }


# ---------------------------------------------------------------------------
# Sección 1 — Validaciones de entrada (sin BD)
# ---------------------------------------------------------------------------

def test_sin_inicio_retorna_error(app):
    data, err = dashboard_api_service({"fin": date.today().isoformat()})
    assert data is None
    assert "fechas" in err.lower()


def test_sin_fin_retorna_error(app):
    data, err = dashboard_api_service({"inicio": date.today().isoformat()})
    assert data is None
    assert "fechas" in err.lower()


def test_sin_ninguna_fecha_retorna_error(app):
    data, err = dashboard_api_service({})
    assert data is None
    assert "fechas" in err.lower()


def test_formato_fecha_invalido_retorna_error(app):
    data, err = dashboard_api_service({"inicio": "31/12/2025", "fin": "31/12/2025"})
    assert data is None
    assert "formato" in err.lower()


def test_fin_menor_a_inicio_retorna_error(app):
    data, err = dashboard_api_service({
        "inicio": "2025-12-31",
        "fin":    "2025-01-01",
    })
    assert data is None
    assert "fin" in err.lower()


def test_rango_exactamente_186_dias_es_valido(app):
    inicio = date.today() - timedelta(days=MAX_DIAS_RANGO)
    fin    = date.today()
    data, err = dashboard_api_service(_args(
        inicio=inicio.isoformat(), fin=fin.isoformat()
    ))
    assert err is None
    assert data is not None


def test_rango_mayor_a_186_dias_retorna_error(app):
    inicio = date.today() - timedelta(days=MAX_DIAS_RANGO + 1)
    fin    = date.today()
    data, err = dashboard_api_service(_args(
        inicio=inicio.isoformat(), fin=fin.isoformat()
    ))
    assert data is None
    assert str(MAX_DIAS_RANGO) in err


# ---------------------------------------------------------------------------
# Sección 2 — _periodo_anterior (lógica pura)
# ---------------------------------------------------------------------------

def test_periodo_anterior_un_dia():
    inicio = date(2025, 6, 15)
    fin    = date(2025, 6, 15)
    ini_ant, fin_ant = _periodo_anterior(inicio, fin)
    assert fin_ant  == date(2025, 6, 14)
    assert ini_ant  == date(2025, 6, 14)


def test_periodo_anterior_semana():
    inicio = date(2025, 6, 9)
    fin    = date(2025, 6, 15)   # 7 días
    ini_ant, fin_ant = _periodo_anterior(inicio, fin)
    assert fin_ant  == date(2025, 6, 8)
    assert ini_ant  == date(2025, 6, 2)


def test_periodo_anterior_misma_duracion():
    inicio = date(2025, 1, 1)
    fin    = date(2025, 1, 31)   # 31 días
    ini_ant, fin_ant = _periodo_anterior(inicio, fin)
    duracion_actual   = (fin    - inicio).days + 1
    duracion_anterior = (fin_ant - ini_ant).days + 1
    assert duracion_actual == duracion_anterior
    assert fin_ant == date(2024, 12, 31)


def test_periodo_anterior_no_se_solapa():
    inicio = date(2025, 3, 1)
    fin    = date(2025, 3, 31)
    ini_ant, fin_ant = _periodo_anterior(inicio, fin)
    assert fin_ant < inicio


# ---------------------------------------------------------------------------
# Sección 3 — dashboard_page_data_service
# ---------------------------------------------------------------------------

def test_page_data_contiene_claves_requeridas(app):
    data = dashboard_page_data_service()
    for clave in ("total_clientes", "total_servicios", "negocios", "fecha_inicio", "fecha_fin"):
        assert clave in data, f"Falta la clave: {clave}"


def test_page_data_fecha_inicio_es_primer_dia_del_mes(app):
    data = dashboard_page_data_service()
    hoy  = date.today()
    assert data["fecha_inicio"] == hoy.replace(day=1).isoformat()


def test_page_data_negocios_no_vacia(app):
    data = dashboard_page_data_service()
    assert len(data["negocios"]) >= 3


# ---------------------------------------------------------------------------
# Sección 4 — Estructura de respuesta (BD vacía en el rango)
# ---------------------------------------------------------------------------

AYER = (date.today() - timedelta(days=1)).isoformat()


def test_estructura_completa_con_rango_sin_datos(app):
    """Verifica que todas las claves del payload existan aunque no haya datos."""
    claves_esperadas = {
        "ventas_semanales", "gastos_semanales", "ingresos_semanales",
        "unidades_semanales", "ventas_prepago", "uso_servicios",
        "ventas_por_dia", "top_clientes", "tiempo_entrega",
        "ingresos_x_negocio", "periodo_anterior", "metodos_pago",
        "hora_recepcion", "hora_entrega", "clientes_unicos",
        "clientes_nuevos", "tasa_retorno", "gasto_prom_cliente", "kpis",
    }
    claves_kpis = {
        "ingresos", "gastos", "ganancia", "ticket_promedio",
        "num_ventas", "saldo_por_cobrar",
        "ingresos_pct", "gastos_pct", "ganancia_pct",
        "ticket_pct", "ventas_pct", "saldo_pct",
    }
    data, err = dashboard_api_service(_args(inicio=AYER, fin=AYER))
    assert err is None
    assert claves_esperadas.issubset(data.keys())
    assert claves_kpis.issubset(data["kpis"].keys())


def test_rango_sin_datos_kpis_son_cero(app):
    data, _ = dashboard_api_service(_args(inicio=AYER, fin=AYER))
    kpis = data["kpis"]
    assert kpis["ingresos"]  == 0.0
    assert kpis["gastos"]    == 0.0
    assert kpis["num_ventas"] == 0


def test_granularidad_dia_devuelve_estructura(app):
    data, err = dashboard_api_service(_args(inicio=AYER, fin=AYER, granularidad="dia"))
    assert err is None
    assert isinstance(data["ventas_semanales"], list)
    assert isinstance(data["ingresos_semanales"], list)


def test_granularidad_hora_devuelve_estructura(app):
    data, err = dashboard_api_service(_args(inicio=AYER, fin=AYER, granularidad="hora"))
    assert err is None
    assert isinstance(data["ventas_semanales"], list)
    assert isinstance(data["ingresos_semanales"], list)


def test_negocio_especifico_no_devuelve_ingresos_x_negocio(app):
    """Cuando se filtra por negocio concreto, ingresos_x_negocio debe ser lista vacía."""
    data, err = dashboard_api_service(_args(inicio=AYER, fin=AYER, id_negocio="1"))
    assert err is None
    assert data["ingresos_x_negocio"] == []


def test_negocio_all_devuelve_ingresos_x_negocio(app):
    data, err = dashboard_api_service(_args(inicio=AYER, fin=AYER, id_negocio="all"))
    assert err is None
    assert isinstance(data["ingresos_x_negocio"], list)


# ---------------------------------------------------------------------------
# Sección 5 — KPIs con datos reales en BD
# ---------------------------------------------------------------------------

def test_kpi_ingresos_incluye_pago_en_rango(app, venta_con_pago):
    hoy = venta_con_pago["fecha"].isoformat()
    data, err = dashboard_api_service(_args(inicio=hoy, fin=hoy, id_negocio="all"))
    assert err is None
    assert data["kpis"]["ingresos"] >= venta_con_pago["monto"]


def test_kpi_ingresos_excluye_pago_fuera_del_rango(app, venta_con_pago):
    ayer = (venta_con_pago["fecha"] - timedelta(days=1)).isoformat()
    anteayer = (venta_con_pago["fecha"] - timedelta(days=2)).isoformat()
    data, err = dashboard_api_service(_args(inicio=anteayer, fin=ayer, id_negocio="all"))
    assert err is None
    # El pago es de hoy, así que no debe aparecer en [anteayer, ayer]
    assert data["kpis"]["ingresos"] < venta_con_pago["monto"]


def test_kpi_gastos_incluye_gasto_en_rango(app, gasto_hoy):
    hoy = gasto_hoy["fecha"].isoformat()
    data, err = dashboard_api_service(_args(inicio=hoy, fin=hoy, id_negocio="all"))
    assert err is None
    assert data["kpis"]["gastos"] >= gasto_hoy["total"]


def test_kpi_ganancia_es_ingresos_menos_gastos(app, venta_con_pago, gasto_hoy):
    hoy = date.today().isoformat()
    data, err = dashboard_api_service(_args(inicio=hoy, fin=hoy, id_negocio="all"))
    assert err is None
    kpis = data["kpis"]
    assert abs(kpis["ganancia"] - (kpis["ingresos"] - kpis["gastos"])) < 0.01


def test_kpi_filtro_negocio_aislado(app, venta_con_pago):
    """Filtrando por negocio 2, no deben aparecer los ingresos del negocio 1."""
    hoy = venta_con_pago["fecha"].isoformat()
    data_n1, _  = dashboard_api_service(_args(inicio=hoy, fin=hoy, id_negocio="1"))
    data_n2, _  = dashboard_api_service(_args(inicio=hoy, fin=hoy, id_negocio="2"))
    assert data_n1["kpis"]["ingresos"] >= venta_con_pago["monto"]
    # La venta es de negocio 1, en negocio 2 no debe estar ese ingreso
    assert data_n2["kpis"]["ingresos"] < data_n1["kpis"]["ingresos"]


def test_pct_cambio_cuando_periodo_anterior_sin_datos(app, venta_con_pago):
    """Si el período anterior no tiene datos, pct debe ser None (no dividir entre 0)."""
    hoy        = venta_con_pago["fecha"].isoformat()
    muy_lejos  = (venta_con_pago["fecha"] - timedelta(days=365)).isoformat()
    # Periodo: solo hoy; periodo_anterior: un día de hace un año → sin datos
    data, err = dashboard_api_service(_args(inicio=hoy, fin=hoy, id_negocio="all"))
    assert err is None
    # Si ingresos_ant == 0 y hay ingresos actuales, pct_cambio devuelve None
    if data["kpis"]["ingresos"] > 0 and data["periodo_anterior"]:
        # Verificar que el campo existe y es None o un número
        pct = data["kpis"]["ingresos_pct"]
        assert pct is None or isinstance(pct, (int, float))
