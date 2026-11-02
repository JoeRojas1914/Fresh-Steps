"""
Búsqueda de clientes por teléfono y botón "Regresar a clientes" en el perfil.
"""
from models.clientes import contar_clientes, obtener_clientes


def _ids(clientes):
    return [c["id_cliente"] for c in clientes]


# cliente_test tiene el teléfono 5512345678

def test_buscar_por_telefono_completo(cliente_test):
    assert cliente_test["id_cliente"] in _ids(obtener_clientes("5512345678", limit=50))


def test_buscar_por_parte_del_telefono(cliente_test):
    assert cliente_test["id_cliente"] in _ids(obtener_clientes("12345678", limit=50))


def test_buscar_telefono_con_espacios_y_guiones(cliente_test):
    for q in ("55 1234 5678", "55-1234-5678", "(55) 1234-5678"):
        assert cliente_test["id_cliente"] in _ids(obtener_clientes(q, limit=50)), q


def test_contar_coincide_con_busqueda_por_telefono(cliente_test):
    assert contar_clientes("5512345678") >= 1


def test_busqueda_por_nombre_sigue_funcionando(cliente_test):
    assert cliente_test["id_cliente"] in _ids(obtener_clientes("TestNombre TestApellido", limit=50))


def test_pagina_clientes_busca_por_telefono(logged_client, cliente_test):
    res = logged_client.get("/clientes?partial=1&q=5512345678")
    assert b"TestNombre" in res.data


def test_perfil_tiene_boton_regresar(logged_client, cliente_test):
    html = logged_client.get(f"/clientes/{cliente_test['id_cliente']}").data.decode()
    assert "Regresar a clientes" in html
    assert 'href="/clientes"' in html


def test_regresar_conserva_busqueda_de_la_lista(logged_client, cliente_test):
    res = logged_client.get(
        f"/clientes/{cliente_test['id_cliente']}",
        headers={"Referer": "http://localhost/clientes?q=Test&pagina=2"},
    )
    assert 'href="/clientes?q=Test&amp;pagina=2"' in res.data.decode()


def test_regresar_ignora_referer_de_otro_sitio(logged_client, cliente_test):
    res = logged_client.get(
        f"/clientes/{cliente_test['id_cliente']}",
        headers={"Referer": "http://otro-sitio.com/clientes?q=x"},
    )
    html = res.data.decode()
    assert 'href="/clientes"' in html
    assert "otro-sitio" not in html
