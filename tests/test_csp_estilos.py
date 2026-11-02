"""
La CSP del sitio (`style-src 'self' fonts.googleapis.com`, en app.py) bloquea los
atributos style="..." — tanto en las plantillas como en el HTML que el JS inserta
con innerHTML. Los estilos van en CSS (clases) o se asignan con `el.style.x = ...`.
"""
import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
_STYLE_ATTR = re.compile(r"""\sstyle\s*=\s*\\?["'`]""")


def _archivos(carpeta, patron):
    return sorted((RAIZ / carpeta).rglob(patron))


@pytest.mark.parametrize("ruta", _archivos("templates", "*.html"), ids=lambda p: p.name)
def test_plantillas_sin_style_inline(ruta):
    # ticket_venta.html se imprime y no usa la CSP del sitio, pero tampoco debe tenerlo
    lineas = [f"{i}: {l.strip()}" for i, l in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1)
              if _STYLE_ATTR.search(l)]
    assert not lineas, f"{ruta.relative_to(RAIZ)}\n" + "\n".join(lineas)


@pytest.mark.parametrize("ruta", _archivos("static/js", "*.js"), ids=lambda p: p.name)
def test_js_no_inserta_style_inline(ruta):
    lineas = [f"{i}: {l.strip()}" for i, l in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1)
              if _STYLE_ATTR.search(l)]
    assert not lineas, f"{ruta.relative_to(RAIZ)}\n" + "\n".join(lineas)


def test_csp_sigue_sin_unsafe_inline_para_estilos():
    from app import app
    res = app.test_client().get("/login")
    csp = res.headers.get("Content-Security-Policy", "")
    assert "style-src" in csp and "unsafe-inline" not in csp
