"""
Skeleton loaders: static/js/components/skeleton.js + estilos en base/animations.css.

No hay pruebas de JS en el proyecto; aquí se verifica lo que se puede sin navegador:
que el script se cargue en el orden correcto y que las clases que arma el JS existan.
"""
import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SKELETON_JS = (RAIZ / "static/js/components/skeleton.js").read_text(encoding="utf-8")
ANIMATIONS_CSS = (RAIZ / "static/css/base/animations.css").read_text(encoding="utf-8")


def test_skeleton_js_se_carga_antes_que_pagination_ajax(logged_client):
    html = logged_client.get("/ventas/pendientes").data.decode()
    i_skel = html.index("js/components/skeleton.js")
    i_pag  = html.index("js/components/pagination_ajax.js")
    assert i_skel < i_pag
    tag = re.search(r"<script[^>]*skeleton\.js[^>]*>", html).group(0)
    assert "defer" in tag


def test_cada_ancho_del_js_tiene_su_clase_css():
    anchos = re.search(r"const ANCHOS = \[([^\]]+)\]", SKELETON_JS).group(1)
    for ancho in re.findall(r'"(w\d+)"', anchos):
        assert f".skeleton--{ancho} " in ANIMATIONS_CSS or f".skeleton--{ancho}{{" in ANIMATIONS_CSS, ancho


def test_clases_base_del_skeleton_existen():
    for clase in (".skeleton {", ".skeleton--line", ".skeleton-row", ".skeleton-li", ".is-skeleton"):
        assert clase in ANIMATIONS_CSS, clase


def test_skeleton_respeta_reduce_motion():
    assert "prefers-reduced-motion" in ANIMATIONS_CSS


def test_estadisticas_sin_texto_cargando(logged_client):
    html = logged_client.get("/estadisticas").data.decode()
    assert 'id="topClientesContainer"' in html
    assert "Cargando..." not in html


def test_js_usa_skeleton_en_vez_de_texto_cargando():
    for archivo in ("static/js/pages/detalles_venta.js", "static/js/base/historial_helpers.js",
                    "static/js/pages/historial_ventas.js", "static/js/components/pagination_ajax.js"):
        assert "Skeleton." in (RAIZ / archivo).read_text(encoding="utf-8"), archivo
