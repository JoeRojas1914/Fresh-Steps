"""
Tests para services/clientes_service.py — CRUD de clientes.
"""
from services.clientes_service import (
    guardar_cliente_service,
    buscar_clientes_service,
    eliminar_cliente_service,
)


def test_crear_cliente_retorna_creado(db_conn, usuario_admin):
    form = {
        "nombre": "Nuevo",
        "apellido": "ClientePrueba",
        "telefono": "5599887766",
        "correo": "nuevo@prueba.com",
        "direccion": "Calle 123",
    }
    resultado = guardar_cliente_service(form, id_usuario=usuario_admin["id_usuario"])
    assert resultado == "creado"

    # Cleanup — buscar el ID creado y eliminarlo
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id_cliente FROM cliente WHERE nombre = 'Nuevo' AND apellido = 'ClientePrueba'"
    )
    row = cursor.fetchone()
    cursor.close()
    assert row is not None, "El cliente no fue insertado en la BD"

    cid = row["id_cliente"]
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM clientes_historial WHERE id_cliente = %s", (cid,))
    cursor.execute("DELETE FROM cliente           WHERE id_cliente = %s", (cid,))
    db_conn.commit()
    cursor.close()


def test_actualizar_cliente_retorna_actualizado(db_conn, cliente_test, usuario_admin):
    form = {
        "id_cliente": str(cliente_test["id_cliente"]),
        "nombre": "NombreActualizado",
        "apellido": cliente_test["apellido"],
        "telefono": "5500000001",
        "correo": "",
        "direccion": "",
    }
    resultado = guardar_cliente_service(form, id_usuario=usuario_admin["id_usuario"])
    assert resultado == "actualizado"

    # Verificar que el cambio persiste
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT nombre FROM cliente WHERE id_cliente = %s", (cliente_test["id_cliente"],))
    row = cursor.fetchone()
    cursor.close()
    assert row["nombre"] == "NombreActualizado"


def test_buscar_clientes_por_nombre(cliente_test):
    resultados = buscar_clientes_service("TestNombre")
    ids = [r["id_cliente"] for r in resultados]
    assert cliente_test["id_cliente"] in ids


def test_buscar_clientes_query_vacia_retorna_lista_vacia():
    resultados = buscar_clientes_service("")
    assert resultados == []


def test_eliminar_cliente_sin_ventas(db_conn, usuario_admin):
    """Un cliente sin ventas se elimina (soft delete activo=0)."""
    cursor = db_conn.cursor()
    cursor.execute(
        """INSERT INTO cliente (nombre, apellido, telefono, activo, id_usuario)
           VALUES ('ElimTest', 'ApellidoElim', '5511223344', 1, %s)""",
        (usuario_admin["id_usuario"],),
    )
    db_conn.commit()
    cid = cursor.lastrowid
    cursor.close()

    resultado = eliminar_cliente_service(cid, id_usuario=usuario_admin["id_usuario"])
    assert resultado is not False

    # Verificar soft delete
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT activo FROM cliente WHERE id_cliente = %s", (cid,))
    row = cursor.fetchone()
    cursor.close()
    assert row["activo"] == 0

    # Cleanup
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM clientes_historial WHERE id_cliente = %s", (cid,))
    cursor.execute("DELETE FROM cliente           WHERE id_cliente = %s", (cid,))
    db_conn.commit()
    cursor.close()
