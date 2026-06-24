"""
Fixtures para tests E2E con Playwright.
Requiere la app corriendo: python app.py
Ejecutar con: pytest tests_e2e/ --base-url http://localhost:5000
"""
import pytest


BASE_URL = "http://localhost:5000"

ADMIN_USER = "admin"
ADMIN_PASS = "Admin1234"


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture
def admin_page(page, base_url):
    """Página con sesión de admin ya iniciada."""
    page.goto(f"{base_url}/login")
    page.fill('input[name="usuario"]', ADMIN_USER)
    page.fill('input[name="password"]', ADMIN_PASS)
    page.click('button[type="submit"]')
    page.wait_for_url(f"{base_url}/")
    return page
