"""
El campo "N° Ticket" es el primer filtro (y con estilo destacado) en las páginas de ventas.
"""
import pytest

PAGINAS = ("/ventas/pendientes", "/ventas/listas", "/ventas/historial")


def _form(html):
    inicio = html.index('class="filtro-box"')
    return html[inicio:html.index("</form>", inicio)]


@pytest.mark.parametrize("url", PAGINAS)
def test_ticket_es_el_primer_filtro(logged_client, url):
    form = _form(logged_client.get(url).data.decode())
    primer_campo = form.index('name="')
    assert form[primer_campo:].startswith('name="id_venta"'), url
    assert "filtro-item--ticket" in form


@pytest.mark.parametrize("url", PAGINAS)
def test_ticket_es_el_primer_filtro_para_caja(logged_client_caja, url):
    form = _form(logged_client_caja.get(url).data.decode())
    assert form[form.index('name="'):].startswith('name="id_venta"'), url


@pytest.mark.parametrize("url", PAGINAS)
def test_ticket_conserva_valor_y_sigue_filtrando(logged_client, venta_pendiente, url):
    id_venta = venta_pendiente["id_venta"]
    html = logged_client.get(f"{url}?id_venta={id_venta}").data.decode()
    assert f'value="{id_venta}"' in _form(html)
