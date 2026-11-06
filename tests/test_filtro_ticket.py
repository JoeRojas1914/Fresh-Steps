"""
Orden de los filtros en las páginas de ventas: primero el Negocio (cuando se muestra)
y enseguida el "N° Ticket".
"""
import pytest

PAGINAS = ("/ventas/pendientes", "/ventas/listas", "/ventas/historial")


def _form(html):
    inicio = html.index('class="filtro-box"')
    return html[inicio:html.index("</form>", inicio)]


def _nombres(form):
    """Nombres de los campos del filtro en el orden en que aparecen (sin repetir)."""
    import re
    vistos = []
    for n in re.findall(r'name="([^"]+)"', form):
        if n not in vistos:
            vistos.append(n)
    return vistos


@pytest.mark.parametrize("url", PAGINAS)
def test_negocio_primero_y_luego_ticket(logged_client, url):
    form = _form(logged_client.get(url).data.decode())
    nombres = _nombres(form)
    assert nombres[:2] == ["id_negocio", "id_venta"], (url, nombres[:3])
    assert "filtro-item--ticket" in form


@pytest.mark.parametrize("url", PAGINAS)
def test_ticket_primero_si_caja_no_ve_negocio(logged_client_caja, url):
    form = _form(logged_client_caja.get(url).data.decode())
    nombres = _nombres(form)
    # La caja con un solo negocio no ve el selector: el ticket queda primero
    if "id_negocio" in nombres:
        assert nombres[:2] == ["id_negocio", "id_venta"], (url, nombres[:3])
    else:
        assert nombres[0] == "id_venta", (url, nombres[:3])


@pytest.mark.parametrize("url", PAGINAS)
def test_ticket_conserva_valor_y_sigue_filtrando(logged_client, venta_pendiente, url):
    id_venta = venta_pendiente["id_venta"]
    html = logged_client.get(f"{url}?id_venta={id_venta}").data.decode()
    assert f'value="{id_venta}"' in _form(html)
