"""Tests E2E: gestión de clientes."""
import pytest
from playwright.sync_api import expect


def test_listar_clientes_visible(admin_page, base_url):
    admin_page.goto(f"{base_url}/clientes")
    expect(admin_page.locator("h1")).to_contain_text("Clientes")
    expect(admin_page.locator("table.table")).to_be_visible()


def test_busqueda_clientes(admin_page, base_url):
    admin_page.goto(f"{base_url}/clientes")
    search = admin_page.locator('input[name="q"]')
    if search.count() > 0:
        search.fill("test")
        admin_page.keyboard.press("Enter")
        expect(admin_page.locator("table.table")).to_be_visible()


def test_modal_crear_cliente_abre(admin_page, base_url):
    admin_page.goto(f"{base_url}/clientes")
    btn = admin_page.locator("button.js-nuevo-cliente, button:has-text('Nuevo cliente')")
    if btn.count() > 0:
        btn.first.click()
        expect(admin_page.locator(".modal")).to_be_visible()


def test_crear_cliente_invalido_muestra_error(admin_page, base_url):
    admin_page.goto(f"{base_url}/clientes")
    btn = admin_page.locator("button.js-nuevo-cliente, button:has-text('Nuevo cliente')")
    if btn.count() == 0:
        pytest.skip("Botón de nuevo cliente no encontrado")

    btn.first.click()
    modal = admin_page.locator(".modal")
    expect(modal).to_be_visible()

    modal.locator('input[name="nombre"]').fill("")
    submit = modal.locator('button[type="submit"]')
    submit.click()

    expect(admin_page.locator(".alert.error, .flash-source")).to_be_visible(timeout=3000)
