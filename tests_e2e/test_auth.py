"""Tests E2E: flujos de autenticación."""
import pytest
from playwright.sync_api import expect


def test_login_admin_exitoso(page, base_url, admin_user="admin", admin_pass="Admin1234"):
    page.goto(f"{base_url}/login")
    expect(page.locator('input[name="usuario"]')).to_be_visible()

    page.fill('input[name="usuario"]', admin_user)
    page.fill('input[name="password"]', admin_pass)
    page.click('button[type="submit"]')

    expect(page).to_have_url(f"{base_url}/")
    expect(page.locator("body")).not_to_contain_text("Credenciales inválidas")


def test_login_credenciales_incorrectas(page, base_url):
    page.goto(f"{base_url}/login")
    page.fill('input[name="usuario"]', "usuarioinexistente")
    page.fill('input[name="password"]', "wrongpass")
    page.click('button[type="submit"]')

    expect(page).to_have_url(f"{base_url}/login")
    expect(page.locator(".alert.error, .flash-source")).to_be_visible()


def test_logout(page, base_url, admin_page):
    admin_page.goto(f"{base_url}/logout")
    expect(admin_page).to_have_url(f"{base_url}/login")


def test_ruta_protegida_sin_sesion_redirige(page, base_url):
    page.goto(f"{base_url}/ventas/pendientes")
    expect(page).to_have_url(f"{base_url}/login")


def test_ruta_admin_bloqueada_para_anonimo(page, base_url):
    page.goto(f"{base_url}/gastos")
    expect(page).to_have_url(f"{base_url}/login")
