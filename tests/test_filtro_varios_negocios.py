"""
Los filtros de negocio aceptan uno o varios negocios (?id_negocio=1&id_negocio=3)
y se muestran como selector múltiple con casillas.
"""
import pytest
from werkzeug.datastructures import MultiDict

from utils import build_where, cond_in, ids_de_args, nombres_negocios


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def test_cond_in_uno_o_varios():
    assert build_where([cond_in("x", 2)]) == ("WHERE x IN (%s)", [2])
    assert build_where([cond_in("x", [1, 3])]) == ("WHERE x IN (%s, %s)", [1, 3])


@pytest.mark.parametrize("vacio", [None, "", [], [None, ""]])
def test_cond_in_vacio_no_filtra(vacio):
    assert build_where([cond_in("x", vacio)]) == ("", [])


def test_ids_de_args_ignora_basura():
    args = MultiDict([("id_negocio", "1"), ("id_negocio", "x"), ("id_negocio", " 3 "), ("id_negocio", "")])
    assert ids_de_args(args) == [1, 3]


def test_nombres_negocios():
    negocios = [{"id_negocio": 1, "nombre": "Calzado"}, {"id_negocio": 3, "nombre": "Maquila"}]
    assert nombres_negocios([1, 3], negocios) == "Calzado, Maquila"
    assert nombres_negocios([], negocios) == ""


# ---------------------------------------------------------------------------
# Selector en pantalla
# ---------------------------------------------------------------------------

PAGINAS_ADMIN = ("/ventas/pendientes", "/ventas/listas", "/ventas/historial",
                 "/servicios", "/gastos", "/pagos")


def _form_filtros(html):
    """Solo el primer <form> GET de la página (los filtros), sin los modales de alta."""
    inicio = html.index('method="GET"')
    return html[inicio:html.index("</form>", inicio)]


@pytest.mark.parametrize("url", PAGINAS_ADMIN)
def test_selector_de_negocio_es_multiple(logged_client, url):
    form = _form_filtros(logged_client.get(url).data.decode())
    assert 'class="multi-select"' in form
    assert 'type="checkbox" name="id_negocio"' in form
    assert '<select name="id_negocio"' not in form


@pytest.mark.parametrize("url", ("/servicios", "/gastos"))
def test_modal_de_alta_sigue_siendo_un_solo_negocio(logged_client, url):
    # Un servicio o un gasto pertenece a un solo negocio
    assert '<select name="id_negocio" id="id_negocio" required>' in logged_client.get(url).data.decode()


def test_selector_en_perfil_de_cliente(logged_client, cliente_test):
    html = logged_client.get(f"/clientes/{cliente_test['id_cliente']}").data.decode()
    assert 'type="checkbox" name="id_negocio"' in html


@pytest.mark.parametrize("url", PAGINAS_ADMIN)
def test_selector_marca_los_negocios_elegidos(logged_client, url):
    html = logged_client.get(f"{url}?id_negocio=1&id_negocio=3").data.decode()
    assert 'name="id_negocio" value="1"\n                       checked' in html
    assert 'name="id_negocio" value="3"\n                       checked' in html
    assert 'name="id_negocio" value="2"\n                       checked' not in html


# ---------------------------------------------------------------------------
# Filtrado
# ---------------------------------------------------------------------------

def _fila(id_venta):
    return f'id="detalles-{id_venta}"'.encode()


def test_pendientes_varios_negocios(logged_client, venta_pendiente, venta_confeccion, venta_maquila):
    res = logged_client.get("/ventas/pendientes?partial=1&id_negocio=1&id_negocio=3")
    assert _fila(venta_pendiente["id_venta"]) in res.data
    assert _fila(venta_maquila["id_venta"]) in res.data
    assert _fila(venta_confeccion["id_venta"]) not in res.data


def test_pendientes_un_negocio_sigue_funcionando(logged_client, venta_pendiente, venta_confeccion):
    res = logged_client.get("/ventas/pendientes?partial=1&id_negocio=2")
    assert _fila(venta_confeccion["id_venta"]) in res.data
    assert _fila(venta_pendiente["id_venta"]) not in res.data


def test_paginacion_conserva_varios_negocios():
    from flask import url_for
    from app import app
    with app.test_request_context("/"):
        url = url_for("ventas.ventas_pendientes", pagina=2, id_negocio=[1, 3])
    assert "id_negocio=1" in url and "id_negocio=3" in url


def test_perfil_cliente_varios_negocios(logged_client, cliente_test, venta_pendiente, venta_confeccion, venta_maquila):
    res = logged_client.get(f"/clientes/{cliente_test['id_cliente']}?partial=1&id_negocio=2&id_negocio=3")
    assert _fila(venta_confeccion["id_venta"]) in res.data
    assert _fila(venta_maquila["id_venta"]) in res.data
    assert _fila(venta_pendiente["id_venta"]) not in res.data


def test_servicios_varios_negocios(servicio_calzado, servicio_confeccion):
    from models.servicios import obtener_servicios, contar_servicios
    ids = lambda neg: {s["id_servicio"] for s in obtener_servicios(id_negocio=neg, limit=1000)}
    assert {servicio_calzado["id_servicio"], servicio_confeccion["id_servicio"]} <= ids([1, 2])
    assert servicio_confeccion["id_servicio"] not in ids([1, 3])
    assert contar_servicios(id_negocio=[1, 2]) == contar_servicios(id_negocio=1) + contar_servicios(id_negocio=2)


def test_gastos_varios_negocios(gasto_test):
    from models.gastos import obtener_gastos, contar_gastos
    ids = lambda neg: {g["id_gasto"] for g in obtener_gastos(id_negocio=neg, limit=10000)}
    assert gasto_test["id_gasto"] in ids([1, 3])
    assert gasto_test["id_gasto"] not in ids([2, 3])
    assert contar_gastos(id_negocio=[1, 2]) == contar_gastos(id_negocio=1) + contar_gastos(id_negocio=2)


def test_pagos_varios_negocios_suma_individuales():
    from models.pagos import contar_historial_pagos
    contar = lambda neg: contar_historial_pagos(neg, None, None, None, None)
    assert contar([1, 2]) == contar(1) + contar(2)
    assert contar([]) == contar(None)


@pytest.mark.parametrize("url", ("/servicios/exportar", "/gastos/exportar", "/pagos/exportar-excel"))
def test_exportar_con_varios_negocios(logged_client, url):
    res = logged_client.get(f"{url}?id_negocio=1&id_negocio=2")
    assert res.status_code == 200
    assert res.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
