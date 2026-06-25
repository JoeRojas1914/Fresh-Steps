"""
Tests de flujo completo (CRUD de punta a punta).
Verifican que crear → actualizar → eliminar → restaurar funcionen como cadena,
no solo como operaciones aisladas.
"""
from services.clientes_service import (
    guardar_cliente_service,
    eliminar_cliente_service,
    restaurar_cliente_service,
    buscar_clientes_service,
)
from services.gastos_service import (
    guardar_gasto_service,
    eliminar_gasto_service,
    restaurar_gasto_service,
    listar_gastos,
)
from services.servicios_service import (
    guardar_servicio_service,
    eliminar_servicio_service,
    restaurar_servicio_service,
    listar_servicios,
)


# ---------------------------------------------------------------------------
# Flujo completo: Cliente
# ---------------------------------------------------------------------------

def test_flujo_completo_cliente(db_conn, usuario_admin):
    """Crear → actualizar → verificar búsqueda → eliminar → restaurar."""
    id_u = usuario_admin["id_usuario"]

    # 1. Crear
    resultado = guardar_cliente_service(
        {"nombre": "FlujoNombre", "apellido": "FlujoApellido",
         "telefono": "5512340001", "correo": "flujo@test.com", "direccion": ""},
        id_usuario=id_u,
    )
    assert resultado == "creado"

    cursor = db_conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id_cliente, activo FROM cliente WHERE nombre='FlujoNombre' AND apellido='FlujoApellido'"
    )
    row = cursor.fetchone()
    cursor.close()
    assert row is not None
    cid = row["id_cliente"]
    assert row["activo"] == 1

    try:
        # 2. Actualizar — commit para salir del snapshot de la lectura anterior (REPEATABLE READ)
        db_conn.commit()
        resultado = guardar_cliente_service(
            {"id_cliente": str(cid), "nombre": "FlujoEditado", "apellido": "FlujoApellido",
             "telefono": "5512340001", "correo": "", "direccion": ""},
            id_usuario=id_u,
        )
        assert resultado == "actualizado"

        db_conn.commit()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT nombre FROM cliente WHERE id_cliente = %s", (cid,))
        assert cursor.fetchone()["nombre"] == "FlujoEditado"
        cursor.close()

        # 3. Búsqueda encuentra al cliente
        resultados = buscar_clientes_service("FlujoEditado")
        assert any(r["id_cliente"] == cid for r in resultados)

        # 4. Eliminar (soft delete)
        ok = eliminar_cliente_service(cid, id_usuario=id_u)
        assert ok is not False

        db_conn.commit()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT activo FROM cliente WHERE id_cliente = %s", (cid,))
        assert cursor.fetchone()["activo"] == 0
        cursor.close()

        # 5. Restaurar
        restaurar_cliente_service(cid, id_usuario=id_u)

        db_conn.commit()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT activo FROM cliente WHERE id_cliente = %s", (cid,))
        assert cursor.fetchone()["activo"] == 1
        cursor.close()

    finally:
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM clientes_historial WHERE id_cliente = %s", (cid,))
        cursor.execute("DELETE FROM cliente           WHERE id_cliente = %s", (cid,))
        db_conn.commit()
        cursor.close()


# ---------------------------------------------------------------------------
# Flujo completo: Gasto
# ---------------------------------------------------------------------------

def test_flujo_completo_gasto(db_conn, usuario_admin):
    """Crear → actualizar → verificar listado → eliminar → restaurar."""
    id_u = usuario_admin["id_usuario"]
    # (id_negocio, id_categoria, descripcion, proveedor, total, fecha_registro, tipo_comprobante, tipo_pago, notas)
    datos_crear = (1, None, "Renta local test", "ProveedorTest", 500.00, "2030-01-15", "factura", "efectivo", None)

    # 1. Crear
    resultado = guardar_gasto_service(None, datos_crear, id_usuario=id_u)
    assert resultado == "creado"

    db_conn.commit()
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id_gasto, activo FROM gastos WHERE descripcion = 'Renta local test' ORDER BY id_gasto DESC LIMIT 1"
    )
    row = cursor.fetchone()
    cursor.close()
    assert row is not None
    gid = row["id_gasto"]
    assert row["activo"] == 1

    try:
        # 2. Actualizar
        db_conn.commit()
        datos_editar = (1, None, "Renta local editada", "ProveedorTest", 600.00, "2030-01-15", "ticket", "transferencia", None)
        resultado = guardar_gasto_service(str(gid), datos_editar, id_usuario=id_u)
        assert resultado == "actualizado"

        db_conn.commit()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT descripcion, total FROM gastos WHERE id_gasto = %s", (gid,))
        row = cursor.fetchone()
        cursor.close()
        assert row["descripcion"] == "Renta local editada"
        assert float(row["total"]) == 600.00

        # 3. Aparece en listado activo
        data = listar_gastos(id_negocio="1", por_pagina=100)
        ids_gastos = [g["id_gasto"] for g in data["gastos"]]
        assert gid in ids_gastos

        # 4. Eliminar (soft delete)
        eliminar_gasto_service(gid, id_usuario=id_u)

        db_conn.commit()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT activo FROM gastos WHERE id_gasto = %s", (gid,))
        assert cursor.fetchone()["activo"] == 0
        cursor.close()

        # 5. No aparece en listado activo pero sí con incluir_eliminados
        data_activos = listar_gastos(id_negocio="1", por_pagina=100)
        assert gid not in [g["id_gasto"] for g in data_activos["gastos"]]

        data_todos = listar_gastos(id_negocio="1", por_pagina=100, incluir_eliminados=True)
        assert gid in [g["id_gasto"] for g in data_todos["gastos"]]

        # 6. Restaurar
        restaurar_gasto_service(gid, id_usuario=id_u)

        db_conn.commit()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT activo FROM gastos WHERE id_gasto = %s", (gid,))
        assert cursor.fetchone()["activo"] == 1
        cursor.close()

    finally:
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM gastos_historial WHERE id_gasto = %s", (gid,))
        cursor.execute("DELETE FROM gastos           WHERE id_gasto = %s", (gid,))
        db_conn.commit()
        cursor.close()


# ---------------------------------------------------------------------------
# Flujo completo: Servicio
# ---------------------------------------------------------------------------

def test_flujo_completo_servicio(db_conn, usuario_admin):
    """Crear → actualizar → verificar nombre único → eliminar → restaurar."""
    id_u = usuario_admin["id_usuario"]

    # Limpieza previa por si quedó huérfano de una ejecución interrumpida
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT id_servicio FROM servicio WHERE nombre = 'Servicio Flujo Test' AND id_negocio = 1"
    )
    leftover = cursor.fetchone()
    if leftover:
        lid = leftover[0]
        cursor.execute("DELETE FROM servicios_historial WHERE id_servicio = %s", (lid,))
        cursor.execute("DELETE FROM servicio WHERE id_servicio = %s", (lid,))
        db_conn.commit()
    cursor.close()

    # 1. Crear
    resultado = guardar_servicio_service(
        id_servicio=None,
        id_negocio=1,
        nombre="Servicio Flujo Test",
        precio=120.00,
        id_usuario=id_u,
    )
    assert resultado == "creado"

    db_conn.commit()
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id_servicio, activo FROM servicio WHERE nombre = 'Servicio Flujo Test' AND id_negocio = 1"
    )
    row = cursor.fetchone()
    cursor.close()
    assert row is not None
    sid = row["id_servicio"]
    assert row["activo"] == 1

    try:
        # 2. Actualizar precio
        db_conn.commit()
        resultado = guardar_servicio_service(
            id_servicio=str(sid),
            id_negocio=1,
            nombre="Servicio Flujo Editado",
            precio=150.00,
            id_usuario=id_u,
        )
        assert resultado == "actualizado"

        db_conn.commit()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT nombre, precio FROM servicio WHERE id_servicio = %s", (sid,))
        row = cursor.fetchone()
        cursor.close()
        assert row["nombre"] == "Servicio Flujo Editado"
        assert float(row["precio"]) == 150.00

        # 3. Nombre duplicado activo levanta ValueError
        import pytest
        with pytest.raises(ValueError, match="Ya existe"):
            guardar_servicio_service(
                id_servicio=None,
                id_negocio=1,
                nombre="Servicio Flujo Editado",
                precio=99.00,
                id_usuario=id_u,
            )

        # 4. Eliminar
        ok = eliminar_servicio_service(sid, id_usuario=id_u)
        assert ok is not False

        db_conn.commit()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT activo FROM servicio WHERE id_servicio = %s", (sid,))
        assert cursor.fetchone()["activo"] == 0
        cursor.close()

        # 5. Restaurar
        restaurar_servicio_service(sid, id_usuario=id_u)

        db_conn.commit()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT activo FROM servicio WHERE id_servicio = %s", (sid,))
        assert cursor.fetchone()["activo"] == 1
        cursor.close()

    finally:
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM servicios_historial WHERE id_servicio = %s", (sid,))
        cursor.execute("DELETE FROM servicio            WHERE id_servicio = %s", (sid,))
        db_conn.commit()
        cursor.close()
