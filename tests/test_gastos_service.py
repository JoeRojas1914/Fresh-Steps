"""
Tests para services/gastos_service.py — CRUD de gastos.
"""
import pytest
from services.gastos_service import (
    guardar_gasto_service,
    eliminar_gasto_service,
    restaurar_gasto_service,
    listar_gastos,
)

DATOS_GASTO = ("1", None, "Compra de material pytest", "ProveedorTest", "250.00",
               "2030-01-15", "ticket", "efectivo", None)


@pytest.fixture
def gasto_test(db_conn, usuario_admin):
    """Gasto de prueba insertado directamente en BD."""
    cursor = db_conn.cursor()
    cursor.execute(
        """INSERT INTO gastos
           (id_negocio, descripcion, proveedor, total, fecha_registro,
            tipo_comprobante, tipo_pago, id_usuario, activo)
           VALUES (1, 'GastoTest', 'ProveedorTest', 100.00, '2030-01-01',
                   'ticket', 'efectivo', %s, 1)""",
        (usuario_admin["id_usuario"],),
    )
    db_conn.commit()
    gid = cursor.lastrowid
    cursor.close()

    yield {"id_gasto": gid}

    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM gastos_historial WHERE id_gasto = %s", (gid,))
    cursor.execute("DELETE FROM gastos           WHERE id_gasto = %s", (gid,))
    db_conn.commit()
    cursor.close()


def test_crear_gasto_retorna_creado(db_conn, usuario_admin):
    resultado = guardar_gasto_service(None, DATOS_GASTO, usuario_admin["id_usuario"])
    assert resultado == "creado"

    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT id_gasto FROM gastos WHERE descripcion = 'Compra de material pytest'"
    )
    row = cursor.fetchone()
    cursor.close()
    assert row is not None

    gid = row[0]
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM gastos_historial WHERE id_gasto = %s", (gid,))
    cursor.execute("DELETE FROM gastos           WHERE id_gasto = %s", (gid,))
    db_conn.commit()
    cursor.close()


def test_actualizar_gasto_retorna_actualizado(db_conn, gasto_test, usuario_admin):
    datos_actualizados = ("1", None, "Descripcion Actualizada", "ProveedorTest",
                          "300.00", "2030-01-15", "factura", "transferencia", None)
    resultado = guardar_gasto_service(
        str(gasto_test["id_gasto"]), datos_actualizados, usuario_admin["id_usuario"]
    )
    assert resultado == "actualizado"

    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT descripcion FROM gastos WHERE id_gasto = %s", (gasto_test["id_gasto"],))
    row = cursor.fetchone()
    cursor.close()
    assert row["descripcion"] == "Descripcion Actualizada"


def test_eliminar_gasto_soft_delete(db_conn, gasto_test, usuario_admin):
    eliminar_gasto_service(gasto_test["id_gasto"], usuario_admin["id_usuario"])

    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT activo FROM gastos WHERE id_gasto = %s", (gasto_test["id_gasto"],))
    row = cursor.fetchone()
    cursor.close()
    assert row["activo"] == 0


def test_restaurar_gasto(db_conn, gasto_test, usuario_admin):
    eliminar_gasto_service(gasto_test["id_gasto"], usuario_admin["id_usuario"])
    restaurar_gasto_service(gasto_test["id_gasto"], usuario_admin["id_usuario"])

    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT activo FROM gastos WHERE id_gasto = %s", (gasto_test["id_gasto"],))
    row = cursor.fetchone()
    cursor.close()
    assert row["activo"] == 1


def test_listar_gastos_incluye_gasto_creado(gasto_test):
    data = listar_gastos(pagina=1)
    ids = [g["id_gasto"] for g in data["gastos"]]
    assert gasto_test["id_gasto"] in ids


def test_listar_gastos_excluye_eliminados_por_defecto(db_conn, gasto_test, usuario_admin):
    eliminar_gasto_service(gasto_test["id_gasto"], usuario_admin["id_usuario"])

    data = listar_gastos(pagina=1, incluir_eliminados=False)
    ids = [g["id_gasto"] for g in data["gastos"]]
    assert gasto_test["id_gasto"] not in ids


def test_listar_gastos_incluye_eliminados_cuando_se_pide(db_conn, gasto_test, usuario_admin):
    eliminar_gasto_service(gasto_test["id_gasto"], usuario_admin["id_usuario"])

    data = listar_gastos(pagina=1, incluir_eliminados=True)
    ids = [g["id_gasto"] for g in data["gastos"]]
    assert gasto_test["id_gasto"] in ids
