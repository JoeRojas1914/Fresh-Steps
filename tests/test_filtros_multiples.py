"""Filtros de varias opciones: Método de pago y Tipo (Pagos), Categoría (Gastos)."""
from models.pagos import contar_historial_pagos
from models.gastos import contar_gastos


def _form(html):
    inicio = html.index('method="GET"')
    return html[inicio:html.index("</form>", inicio)]


# ── Pagos ──
def test_pagos_muestra_casillas_de_metodo_y_tipo(logged_client):
    form = _form(logged_client.get("/pagos").data.decode())
    assert 'type="checkbox" name="tipo_pago"' in form
    assert 'type="checkbox" name="tipo_pago_venta"' in form
    assert '<select name="tipo_pago"' not in form


def test_pagos_varios_metodos_suman(logged_client):
    efectivo = contar_historial_pagos(None, ["efectivo"], None, None, None)
    transf   = contar_historial_pagos(None, ["transferencia"], None, None, None)
    ambos    = contar_historial_pagos(None, ["efectivo", "transferencia"], None, None, None)
    assert ambos == efectivo + transf


def test_pagos_conserva_marcados(logged_client):
    form = _form(logged_client.get("/pagos?tipo_pago=efectivo&tipo_pago=tarjeta").data.decode())
    assert 'value="efectivo"\n                       checked' in form
    assert 'value="tarjeta"\n                       checked' in form
    assert 'value="transferencia"\n                       checked' not in form


def test_pagos_ignora_metodos_desconocidos(logged_client):
    assert logged_client.get("/pagos?tipo_pago=inventado").status_code == 200


def test_exportar_pagos_con_varios_metodos(logged_client):
    resp = logged_client.get("/pagos/exportar-excel?tipo_pago=efectivo&tipo_pago=tarjeta&tipo_pago_venta=final")
    assert resp.status_code == 200


# ── Gastos ──
def test_gastos_categoria_con_casillas(logged_client):
    form = _form(logged_client.get("/gastos").data.decode())
    assert 'type="checkbox" name="id_categoria"' in form


def test_gastos_varias_categorias(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT id_categoria FROM categoria_gasto ORDER BY id_categoria LIMIT 2")
    ids = [r[0] for r in cur.fetchall()]
    cur.close()
    if len(ids) < 2:
        return
    a = contar_gastos(None, id_categoria=[ids[0]])
    b = contar_gastos(None, id_categoria=[ids[1]])
    assert contar_gastos(None, id_categoria=ids) == a + b


def test_exportar_gastos_con_varias_categorias(logged_client):
    assert logged_client.get("/gastos/exportar?id_categoria=1&id_categoria=2").status_code == 200
