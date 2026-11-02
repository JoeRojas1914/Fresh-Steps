"""
Los scripts de cada página deben cargarse con `defer` o `type="module"`.

Un <script src> normal se ejecuta en cuanto se lee, antes que los scripts
`defer` de base.html (p. ej. pagination_ajax.js, que define window.initFiltroAjax),
y truena con "initFiltroAjax is not a function".
"""
import re

import pytest

PAGINAS = ("/", "/ventas", "/ventas/pendientes", "/ventas/listas", "/ventas/historial",
           "/clientes", "/servicios", "/gastos", "/pagos", "/usuarios", "/estadisticas")

_SCRIPT_SRC = re.compile(r"<script\b[^>]*\bsrc=[^>]*>", re.I)


@pytest.mark.parametrize("url", PAGINAS)
def test_scripts_de_pagina_no_bloquean(logged_client, url):
    html = logged_client.get(url).data.decode()
    for tag in _SCRIPT_SRC.findall(html):
        assert "defer" in tag or 'type="module"' in tag, (url, tag)
