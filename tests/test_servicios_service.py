"""
Tests para services/servicios_service.py — CRUD de servicios.
"""
import pytest
from services.servicios_service import (
    guardar_servicio_service,
    eliminar_servicio_service,
    restaurar_servicio_service,
    listar_servicios,
)


@pytest.fixture
def servicio_test(db_conn, usuario_admin):
    """Servicio de prueba insertado directamente en BD (negocio 1 = calzado)."""
    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO servicio (id_negocio, nombre, precio, activo) VALUES (1, 'ServicioTest', 99.00, 1)"
    )
    db_conn.commit()
    sid = cursor.lastrowid
    cursor.close()

    yield {"id_servicio": sid, "id_negocio": 1, "nombre": "ServicioTest", "precio": 99.00}

    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM servicios_historial WHERE id_servicio = %s", (sid,))
    cursor.execute("DELETE FROM servicio            WHERE id_servicio = %s", (sid,))
    db_conn.commit()
    cursor.close()


def test_crear_servicio_retorna_creado(db_conn, usuario_admin):
    resultado = guardar_servicio_service(None, "1", "NuevoServicio", "75.00", usuario_admin["id_usuario"])
    assert resultado == "creado"

    cursor = db_conn.cursor()
    cursor.execute("SELECT id_servicio FROM servicio WHERE nombre = 'NuevoServicio'")
    row = cursor.fetchone()
    cursor.close()
    assert row is not None

    sid = row[0]
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM servicios_historial WHERE id_servicio = %s", (sid,))
    cursor.execute("DELETE FROM servicio            WHERE id_servicio = %s", (sid,))
    db_conn.commit()
    cursor.close()


def test_actualizar_servicio_retorna_actualizado(db_conn, servicio_test, usuario_admin):
    resultado = guardar_servicio_service(
        str(servicio_test["id_servicio"]), "1", "NombreActualizado", "120.00",
        usuario_admin["id_usuario"]
    )
    assert resultado == "actualizado"

    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT nombre FROM servicio WHERE id_servicio = %s", (servicio_test["id_servicio"],))
    row = cursor.fetchone()
    cursor.close()
    assert row["nombre"] == "NombreActualizado"


def test_eliminar_servicio_sin_ventas(db_conn, servicio_test, usuario_admin):
    ok = eliminar_servicio_service(servicio_test["id_servicio"], usuario_admin["id_usuario"])
    assert ok is not False

    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT activo FROM servicio WHERE id_servicio = %s", (servicio_test["id_servicio"],))
    row = cursor.fetchone()
    cursor.close()
    assert row["activo"] == 0


def test_restaurar_servicio(db_conn, servicio_test, usuario_admin):
    eliminar_servicio_service(servicio_test["id_servicio"], usuario_admin["id_usuario"])
    restaurar_servicio_service(servicio_test["id_servicio"], usuario_admin["id_usuario"])

    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT activo FROM servicio WHERE id_servicio = %s", (servicio_test["id_servicio"],))
    row = cursor.fetchone()
    cursor.close()
    assert row["activo"] == 1


def test_listar_servicios_incluye_servicio_creado(servicio_test):
    data = listar_servicios(id_negocio=1, pagina=1, por_pagina=100)
    ids = [s["id_servicio"] for s in data["servicios"]]
    assert servicio_test["id_servicio"] in ids


def test_listar_servicios_excluye_eliminados_por_defecto(db_conn, servicio_test, usuario_admin):
    eliminar_servicio_service(servicio_test["id_servicio"], usuario_admin["id_usuario"])

    data = listar_servicios(id_negocio=1, pagina=1, por_pagina=100, incluir_eliminados=False)
    ids = [s["id_servicio"] for s in data["servicios"]]
    assert servicio_test["id_servicio"] not in ids


def test_listar_servicios_filtra_por_negocio(servicio_test):
    data_n1 = listar_servicios(id_negocio=1, pagina=1, por_pagina=100)
    data_n2 = listar_servicios(id_negocio=2, pagina=1, por_pagina=100)

    ids_n1 = [s["id_servicio"] for s in data_n1["servicios"]]
    ids_n2 = [s["id_servicio"] for s in data_n2["servicios"]]

    assert servicio_test["id_servicio"] in ids_n1
    assert servicio_test["id_servicio"] not in ids_n2
