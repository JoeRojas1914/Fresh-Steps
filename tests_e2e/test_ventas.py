"""Tests E2E: flujos de ventas."""
import pytest
from playwright.sync_api import expect


def test_ventas_pendientes_carga(admin_page, base_url):
    admin_page.goto(f"{base_url}/ventas/pendientes")
    expect(admin_page.locator("h1")).to_be_visible()
    expect(admin_page.locator("table.table, .empty-articulos, td.td-empty")).to_be_visible()


def test_ventas_listas_carga(admin_page, base_url):
    admin_page.goto(f"{base_url}/ventas/listas")
    expect(admin_page.locator("h1")).to_be_visible()


def test_historial_ventas_carga(admin_page, base_url):
    admin_page.goto(f"{base_url}/ventas/historial")
    expect(admin_page.locator("h1")).to_be_visible()
    expect(admin_page.locator("table.table")).to_be_visible()


def test_crear_venta_pagina_carga(admin_page, base_url):
    admin_page.goto(f"{base_url}/ventas/crear")
    expect(admin_page.locator("#id_negocio")).to_be_visible()
    expect(admin_page.locator("#fecha_estimada_fecha")).to_be_visible()


def test_crear_venta_sin_cliente_bloquea_submit(admin_page, base_url):
    admin_page.goto(f"{base_url}/ventas/crear")
    btn_guardar = admin_page.locator("#btn-guardar-venta, button:has-text('Guardar venta')")
    if btn_guardar.count() > 0:
        expect(btn_guardar.first).to_be_disabled()


def test_selector_negocio_muestra_articulos(admin_page, base_url):
    admin_page.goto(f"{base_url}/ventas/crear")
    select_negocio = admin_page.locator("#id_negocio")
    select_negocio.select_option("1")
    btn_agregar = admin_page.locator("#btn-agregar-articulo")
    expect(btn_agregar).to_be_visible()


def test_estadisticas_admin(admin_page, base_url):
    admin_page.goto(f"{base_url}/estadisticas")
    expect(admin_page.locator("h1")).to_be_visible()
    expect(admin_page.locator("canvas, .kpi-card, .stats-section")).to_be_visible(timeout=5000)
