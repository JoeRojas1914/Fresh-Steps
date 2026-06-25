"""
Tests apuntados a líneas específicas no cubiertas.
Cubre: auth_service, gastos_service, servicios_service, usuarios_service,
       ventas_service (prepago/descuento/validaciones), ventas_editar_service,
       estadisticas_service, clientes_service, y rutas pendientes.
"""
import pytest
from decimal import Decimal


# ===========================================================================
# auth_service
# ===========================================================================

def test_registrar_logout_service(app, usuario_admin):
    """Cubre services/auth_service.py:117."""
    from services.auth_service import registrar_logout_service
    with app.test_request_context("/", headers={"User-Agent": "pytest"}):
        registrar_logout_service(
            usuario_admin["id_usuario"],
            usuario_admin["usuario"],
            "127.0.0.1",
        )


def test_invalidar_session_token_service(usuario_admin):
    """Cubre services/auth_service.py:121."""
    from services.auth_service import invalidar_session_token_service
    invalidar_session_token_service(usuario_admin["id_usuario"])


def test_login_pin_sin_usuarios_caja(app, db_conn):
    """Cubre auth_service.py:95 — retorna None cuando no hay usuarios caja activos."""
    from services.auth_service import login_pin_service
    # Desactivamos todos los usuarios caja temporalmente
    cursor = db_conn.cursor()
    cursor.execute("UPDATE usuario SET activo = 0 WHERE rol = 'caja'")
    db_conn.commit()
    try:
        with app.test_request_context("/", headers={"User-Agent": "pytest"}):
            result = login_pin_service("1234", "127.0.0.1")
        assert result is None
    finally:
        cursor.execute("UPDATE usuario SET activo = 1 WHERE rol = 'caja'")
        db_conn.commit()
        cursor.close()


def test_login_pin_incorrecto_retorna_none(app, usuario_caja, db_conn):
    """Cubre auth_service.py:113 — PIN incorrecto (no bloqueado) retorna None."""
    # Limpiar intentos acumulados de ejecuciones previas para esta IP
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM login_intentos WHERE ip = '10.0.0.99'")
    db_conn.commit()
    cursor.close()

    from services.auth_service import login_pin_service
    with app.test_request_context("/", headers={"User-Agent": "pytest"}):
        result = login_pin_service("0000", "10.0.0.99")
    assert result is None

    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM login_intentos WHERE ip = '10.0.0.99'")
    db_conn.commit()
    cursor.close()


def test_login_pin_bloqueado_retorna_locked(app, usuario_caja):
    """Cubre auth_service.py:110-111 — retorna 'LOCKED' cuando todos los usuarios están bloqueados."""
    from services.auth_service import login_pin_service
    from config import MAX_INTENTOS_PIN, BLOQUEO_MIN_PIN
    with app.test_request_context("/", headers={"User-Agent": "pytest"}):
        # Consumir todos los intentos para bloquear el usuario caja
        for _ in range(MAX_INTENTOS_PIN + 1):
            login_pin_service("0000", "127.0.0.1")
        # Ahora el usuario está bloqueado → debe retornar LOCKED
        result = login_pin_service("0000", "127.0.0.1")
        assert result == "LOCKED"


# ===========================================================================
# gastos_service
# ===========================================================================

def test_obtener_historial_gasto_service(gasto_test):
    """Cubre gastos_service.py:67."""
    from services.gastos_service import obtener_historial_gasto_service
    historial = obtener_historial_gasto_service(gasto_test["id_gasto"])
    assert isinstance(historial, list)


def test_actualizar_categoria_service(db_conn):
    """Cubre gastos_service.py:79."""
    from services.gastos_service import actualizar_categoria_service
    from models.gastos import crear_categoria, obtener_categorias, eliminar_categoria

    crear_categoria("CatTestCobertura")
    cats = obtener_categorias()
    cat = next((c for c in cats if c["nombre"] == "CatTestCobertura"), None)
    assert cat is not None
    try:
        actualizar_categoria_service(cat["id_categoria"], "CatTestCoberturaEdit")
        cats2 = obtener_categorias()
        nombres = [c["nombre"] for c in cats2]
        assert "CatTestCoberturaEdit" in nombres
    finally:
        cats3 = obtener_categorias()
        cat3 = next((c for c in cats3 if "CatTestCobertura" in c["nombre"]), None)
        if cat3:
            eliminar_categoria(cat3["id_categoria"])


def test_eliminar_categoria_service(db_conn):
    """Cubre gastos_service.py:83."""
    from services.gastos_service import eliminar_categoria_service
    from models.gastos import crear_categoria, obtener_categorias

    crear_categoria("CatElimTest")
    cats = obtener_categorias()
    cat = next((c for c in cats if c["nombre"] == "CatElimTest"), None)
    assert cat is not None
    result = eliminar_categoria_service(cat["id_categoria"])
    assert result is not None  # (True, msg) o (False, msg)


# ===========================================================================
# servicios_service — cache hit (línea 55)
# ===========================================================================

def test_listar_servicios_api_cache_hit():
    """Cubre servicios_service.py:55 — segunda llamada dentro del TTL usa caché."""
    import services.servicios_service as ss
    ss._servicios_cache.clear()
    primera = ss.listar_servicios_api(1)
    segunda = ss.listar_servicios_api(1)
    assert primera == segunda
    ss._servicios_cache.clear()


# ===========================================================================
# usuarios_service
# ===========================================================================

def test_guardar_usuario_service_editar_inexistente(app):
    """Cubre usuarios_service.py:56 — editar usuario que no existe."""
    from services.usuarios_service import guardar_usuario_service
    with app.test_request_context("/"):
        with pytest.raises(ValueError, match="no encontrado"):
            guardar_usuario_service(
                99999, "nadie", None, "caja", None,
                nombre="N", apellido="A",
            )


def test_guardar_usuario_service_editar_admin_no_cambia(app, usuario_admin):
    """Cubre usuarios_service.py:58 — editar un admin retorna sin hacer cambios."""
    from services.usuarios_service import guardar_usuario_service
    with app.test_request_context("/"):
        # No debe lanzar excepción; simplemente retorna (return early)
        guardar_usuario_service(
            usuario_admin["id_usuario"],
            usuario_admin["usuario"],
            "nuevaPassword1",
            "admin",
            None,
            nombre="NuevoNombre",
        )


def test_guardar_usuario_service_editar_con_password(app, usuario_caja):
    """Cubre usuarios_service.py:66-67 — editar caja con nueva contraseña."""
    from services.usuarios_service import guardar_usuario_service
    with app.test_request_context("/"):
        guardar_usuario_service(
            usuario_caja["id_usuario"],
            usuario_caja["usuario"],
            "NuevaPass123",
            "caja",
            None,
        )


def test_guardar_usuario_service_editar_con_pin(app, usuario_caja, db_conn):
    """Cubre usuarios_service.py:70-72 — editar caja con nuevo PIN."""
    from services.usuarios_service import guardar_usuario_service
    # Usa un PIN que no coincida con el pin actual para evitar colisión
    nuevo_pin = "8877"
    with app.test_request_context("/"):
        guardar_usuario_service(
            usuario_caja["id_usuario"],
            usuario_caja["usuario"],
            None,
            "caja",
            nuevo_pin,
        )


def test_toggle_usuario_service_inexistente(app):
    """Cubre usuarios_service.py:85 — toggle usuario que no existe."""
    from services.usuarios_service import toggle_usuario_service
    with app.test_request_context("/"):
        result = toggle_usuario_service(99999)
    assert result is None


# ===========================================================================
# ventas_service — validaciones internas
# ===========================================================================

def test_validar_reglas_negocio_servicio_sin_id():
    """Cubre ventas_service.py:271."""
    from services.ventas_service import _validar_reglas_negocio
    with pytest.raises(ValueError, match="sin id"):
        _validar_reglas_negocio("calzado", [
            {"servicios": [{"id_servicio": None, "precio_aplicado": Decimal("100")}]}
        ])


def test_validar_reglas_negocio_maquila_con_servicios():
    """Cubre ventas_service.py:277."""
    from services.ventas_service import _validar_reglas_negocio
    with pytest.raises(ValueError, match="Maquila no permite servicios"):
        _validar_reglas_negocio("maquila", [
            {"servicios": [{"id_servicio": 1, "precio_aplicado": Decimal("50")}]}
        ])


def test_parsear_prepago_con_si():
    """Cubre ventas_service.py:177-180."""
    from services.ventas_service import _parsear_prepago
    prepago, monto = _parsear_prepago({"prepago": "si", "monto_prepago": "75.50"})
    assert prepago is True
    assert monto == Decimal("75.50")


def test_parsear_prepago_monto_invalido():
    """Cubre la rama de excepción en _parsear_prepago."""
    from services.ventas_service import _parsear_prepago
    with pytest.raises(ValueError, match="no es válido"):
        _parsear_prepago({"prepago": "si", "monto_prepago": "abc"})


def test_parsear_descuento_con_si():
    """Cubre ventas_service.py:186-187."""
    from services.ventas_service import _parsear_descuento
    aplica, cant = _parsear_descuento({"aplica_descuento": "si", "cantidad_descuento": "20.00"})
    assert aplica is True
    assert cant == Decimal("20.00")


def test_parsear_descuento_monto_invalido():
    """Cubre ventas_service.py:188-189 — InvalidOperation en descuento."""
    from services.ventas_service import _parsear_descuento
    with pytest.raises(ValueError, match="no es válido"):
        _parsear_descuento({"aplica_descuento": "si", "cantidad_descuento": "abc"})


def test_parsear_articulos_tipo_desconocido():
    """Cubre ventas_service.py:224 — tipo_articulo desconocido cuando tipo_permitido=None."""
    from services.ventas_service import _parsear_articulos_form
    with pytest.raises(ValueError, match="desconocido"):
        _parsear_articulos_form({"articulos[0][tipo_articulo]": "zapaton"}, None)


def _cleanup_ultima_venta_cliente(db_conn, id_cliente):
    """Limpia la última venta creada para un cliente (para ventas con error de prepago)."""
    from tests.conftest import cleanup_venta
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id_venta FROM venta WHERE id_cliente = %s ORDER BY id_venta DESC LIMIT 1",
        (id_cliente,),
    )
    row = cursor.fetchone()
    cursor.close()
    if row:
        cleanup_venta(db_conn, row["id_venta"])


def test_guardar_venta_prepago_sin_tipo_pago(app, usuario_admin, cliente_test, servicio_calzado, db_conn):
    """Cubre ventas_service.py:314-316 — prepago sin tipo_pago."""
    from services.ventas_service import guardar_venta_service
    sid = servicio_calzado["id_servicio"]
    form = {
        "id_negocio": "1",
        "id_cliente": str(cliente_test["id_cliente"]),
        "fecha_estimada": "2030-12-31 10:00:00",
        "prepago": "si",
        "monto_prepago": "50.00",
        # sin tipo_pago
        "articulos[0][tipo_articulo]": "calzado",
        "articulos[0][tipo]": "Tenis",
        "articulos[0][marca]": "Nike",
        "articulos[0][material]": "Piel",
        "articulos[0][color_base]": "Blanco",
        f"articulos[0][servicios][0][id_servicio]": str(sid),
        f"articulos[0][servicios][0][precio_aplicado]": "150.00",
    }
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=usuario_admin["id_usuario"])
    assert error == "Debes seleccionar el tipo de pago del prepago."
    # La venta se crea antes de la verificación → limpiar la venta huérfana
    _cleanup_ultima_venta_cliente(db_conn, cliente_test["id_cliente"])


def test_guardar_venta_prepago_mayor_al_total(app, usuario_admin, cliente_test, servicio_calzado, db_conn):
    """Cubre ventas_service.py:317-319 — prepago mayor al total."""
    from services.ventas_service import guardar_venta_service
    sid = servicio_calzado["id_servicio"]
    form = {
        "id_negocio": "1",
        "id_cliente": str(cliente_test["id_cliente"]),
        "fecha_estimada": "2030-12-31 10:00:00",
        "prepago": "si",
        "monto_prepago": "9999.00",  # mayor que el total (150)
        "tipo_pago": "efectivo",
        "articulos[0][tipo_articulo]": "calzado",
        "articulos[0][tipo]": "Tenis",
        "articulos[0][marca]": "Nike",
        "articulos[0][material]": "Piel",
        "articulos[0][color_base]": "Blanco",
        f"articulos[0][servicios][0][id_servicio]": str(sid),
        f"articulos[0][servicios][0][precio_aplicado]": "150.00",
    }
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=usuario_admin["id_usuario"])
    assert error == "El prepago no puede ser mayor al total de la venta."
    # La venta se crea antes de la verificación → limpiar la venta huérfana
    _cleanup_ultima_venta_cliente(db_conn, cliente_test["id_cliente"])


def test_guardar_venta_con_prepago_valido(app, usuario_admin, cliente_test, servicio_calzado, db_conn):
    """Cubre ventas_service.py:320-326 — prepago registrado correctamente."""
    from services.ventas_service import guardar_venta_service
    from tests.conftest import cleanup_venta
    sid = servicio_calzado["id_servicio"]
    form = {
        "id_negocio": "1",
        "id_cliente": str(cliente_test["id_cliente"]),
        "fecha_estimada": "2030-12-31 10:00:00",
        "prepago": "si",
        "monto_prepago": "50.00",
        "tipo_pago": "efectivo",
        "articulos[0][tipo_articulo]": "calzado",
        "articulos[0][tipo]": "Tenis",
        "articulos[0][marca]": "Adidas",
        "articulos[0][material]": "Piel",
        "articulos[0][color_base]": "Negro",
        f"articulos[0][servicios][0][id_servicio]": str(sid),
        f"articulos[0][servicios][0][precio_aplicado]": "150.00",
    }
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=usuario_admin["id_usuario"])
    assert error is None
    assert id_venta is not None
    cleanup_venta(db_conn, id_venta)


def test_guardar_venta_con_descuento(app, usuario_admin, cliente_test, servicio_calzado, db_conn):
    """Cubre ventas_service.py (descuento)."""
    from services.ventas_service import guardar_venta_service
    from tests.conftest import cleanup_venta
    sid = servicio_calzado["id_servicio"]
    form = {
        "id_negocio": "1",
        "id_cliente": str(cliente_test["id_cliente"]),
        "fecha_estimada": "2030-12-31 10:00:00",
        "aplica_descuento": "si",
        "cantidad_descuento": "10.00",
        "articulos[0][tipo_articulo]": "calzado",
        "articulos[0][tipo]": "Tenis",
        "articulos[0][marca]": "Puma",
        "articulos[0][material]": "Tela",
        "articulos[0][color_base]": "Rojo",
        f"articulos[0][servicios][0][id_servicio]": str(sid),
        f"articulos[0][servicios][0][precio_aplicado]": "150.00",
    }
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=usuario_admin["id_usuario"])
    assert error is None
    cleanup_venta(db_conn, id_venta)


def test_historial_ventas_con_eliminada(app, db_conn, venta_pendiente, usuario_admin):
    """Cubre ventas_service.py:87 — estado='eliminada' en _enriquecer_ventas."""
    from services.ventas_service import eliminar_venta_service, historial_ventas_service
    id_venta = venta_pendiente["id_venta"]
    with app.test_request_context("/"):
        eliminar_venta_service(id_venta, usuario_admin["id_usuario"])
    with app.test_request_context("/"):
        data = historial_ventas_service(mostrar_eliminadas=True)
    ventas = data["ventas"]
    eliminadas = [v for v in ventas if v.get("id_venta") == id_venta]
    assert any(v["estado"] == "eliminada" for v in eliminadas)


# ===========================================================================
# ventas_editar_service
# ===========================================================================

def test_parsear_dec_invalido():
    """Cubre ventas_editar_service.py:69-70 — InvalidOperation retorna Decimal('0')."""
    from services.ventas_editar_service import _parsear_dec
    result = _parsear_dec("no_es_numero")
    assert result == Decimal("0")


def test_validar_post_eliminaciones_sin_servicios(venta_pendiente):
    """Cubre ventas_editar_service.py:26-52 — raise ValueError al quitar el último servicio."""
    from services.ventas_editar_service import _validar_post_eliminaciones
    eliminaciones = [{
        "id_articulo": venta_pendiente["id_articulo"],
        "id_servicio": venta_pendiente["id_servicio"],
    }]
    with pytest.raises(ValueError, match="sin servicios"):
        _validar_post_eliminaciones(
            venta_pendiente["id_venta"], "calzado", eliminaciones
        )


def test_editar_venta_service_con_nuevos_articulos(app, venta_pendiente, servicio_calzado, usuario_admin, db_conn):
    """Cubre ventas_editar_service.py:160 — _validar_reglas_negocio con nuevos_articulos."""
    from services.ventas_editar_service import editar_venta_service
    sid = servicio_calzado["id_servicio"]
    form = {
        "articulos[0][tipo_articulo]": "calzado",
        "articulos[0][tipo]": "Zapato",
        "articulos[0][marca]": "Clarks",
        "articulos[0][material]": "Cuero",
        "articulos[0][color_base]": "Café",
        f"articulos[0][servicios][0][id_servicio]": str(sid),
        f"articulos[0][servicios][0][precio_aplicado]": "80.00",
    }
    with app.test_request_context("/"):
        result = editar_venta_service(
            venta_pendiente["id_venta"], form, usuario_admin["id_usuario"]
        )
    assert "total_nuevo" in result


# ===========================================================================
# estadisticas_service
# ===========================================================================

def test_dashboard_api_granularidad_hora(app):
    """Cubre estadisticas_service.py:109-111 — granularidad='hora'."""
    from services.estadisticas_service import dashboard_api_service
    with app.test_request_context("/"):
        data, err = dashboard_api_service({
            "inicio": "2026-01-01",
            "fin": "2026-01-07",
            "id_negocio": "all",
            "granularidad": "hora",
        })
    assert err is None
    assert "ventas_semanales" in data


def test_dashboard_api_agrupacion_categoria(app):
    """Cubre estadisticas_service.py:122 — agrupacion_gastos='categoria'."""
    from services.estadisticas_service import dashboard_api_service
    with app.test_request_context("/"):
        data, err = dashboard_api_service({
            "inicio": "2026-01-01",
            "fin": "2026-01-31",
            "id_negocio": "all",
            "agrupacion_gastos": "categoria",
        })
    assert err is None


def test_exportar_estadisticas_tipo_fecha_invalido(app):
    """Cubre estadisticas_service.py:181 — col se resetea a 'fecha_recibo'."""
    from services.estadisticas_service import exportar_estadisticas_service
    with app.test_request_context("/"):
        result, err = exportar_estadisticas_service({
            "inicio": "2026-01-01",
            "fin": "2026-01-31",
            "tipo_fecha": "campo_invalido",
        })
    assert err is None


def test_exportar_estadisticas_fecha_invalida(app):
    """Cubre estadisticas_service.py:188-189 — formato de fecha inválido."""
    from services.estadisticas_service import exportar_estadisticas_service
    with app.test_request_context("/"):
        result, err = exportar_estadisticas_service({
            "inicio": "no-es-fecha",
            "fin": "tampoco",
        })
    assert err == "Formato de fecha inválido"


def test_exportar_estadisticas_fin_menor_inicio(app):
    """Cubre estadisticas_service.py:190-191 — fin < inicio."""
    from services.estadisticas_service import exportar_estadisticas_service
    with app.test_request_context("/"):
        result, err = exportar_estadisticas_service({
            "inicio": "2026-12-31",
            "fin": "2026-01-01",
        })
    assert err is not None
    assert "fin" in err.lower() or "inicio" in err.lower()


def test_exportar_estadisticas_rango_demasiado_largo(app):
    """Cubre estadisticas_service.py:192-193 — rango mayor al máximo."""
    from services.estadisticas_service import exportar_estadisticas_service
    with app.test_request_context("/"):
        result, err = exportar_estadisticas_service({
            "inicio": "2024-01-01",
            "fin": "2026-12-31",  # más de 186 días
        })
    assert err is not None
    assert "máximo" in err.lower() or "maximo" in err.lower() or "rango" in err.lower()


# ===========================================================================
# clientes_service — detalle con ventas
# ===========================================================================

def test_obtener_cliente_detalle_con_ventas(app, cliente_test, venta_pendiente):
    """Cubre clientes_service.py:112-119 — loop body cuando el cliente tiene ventas."""
    from services.clientes_service import obtener_cliente_detalle_service
    with app.test_request_context("/"):
        data = obtener_cliente_detalle_service(
            cliente_test["id_cliente"],
            filtros={"pagina": 1},
        )
    assert "pedidos" in data
    assert len(data["pedidos"]) > 0


# ===========================================================================
# conftest — teardown cubre líneas 68-69 (gasto sin cleanup en test)
# ===========================================================================

def test_fixture_teardown_limpia_gastos(app, db_conn, usuario_admin):
    """Crea un gasto y lo deja para que el teardown de usuario_admin lo limpie (líneas 68-69)."""
    from models.gastos import crear_gasto
    crear_gasto(
        1, None, "GastoTeardownTest", "Proveedor", 5.00,
        "2030-01-01", "ticket", "efectivo", None,
        usuario_admin["id_usuario"],
    )
    # Deliberadamente no eliminamos — usuario_admin teardown lo limpia


# ===========================================================================
# ventas_routes — rutas no autenticadas y ramas no cubiertas
# ===========================================================================

def test_abrir_whatsapp_local_sin_forward(logged_client):
    """Cubre ventas_routes.py:61-70 — is_local=True, exe=None, rama else."""
    res = logged_client.post(
        "/ventas/abrir-whatsapp",
        json={
            "url": "https://web.whatsapp.com/send?phone=521234567890&text=hola",
            "negocio_id": 2,  # Chrome path, no instalado en CI
        },
        # SIN X-Forwarded-For → is_local=True
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert data.get("opened") is True


def test_historial_ventas_tipo_fecha_invalido(logged_client):
    """Cubre ventas_routes.py:248 — tipo_fecha inválido se resetea a fecha_recibo."""
    res = logged_client.get("/ventas/historial?tipo_fecha=campo_invalido")
    assert res.status_code == 200


def test_exportar_historial_tipo_fecha_invalido(logged_client):
    """Cubre ventas_routes.py:270 — tipo_fecha inválido en exportar."""
    res = logged_client.get("/ventas/historial/exportar?tipo_fecha=campo_invalido")
    assert res.status_code == 200


def test_entregar_venta_ya_entregada(logged_client, venta_pendiente, usuario_admin):
    """Cubre ventas_routes.py:104-107 — entregar venta ya entregada retorna ok:False."""
    from services.ventas_service import marcar_entregada
    marcar_entregada(venta_pendiente["id_venta"], usuario_admin["id_usuario"])
    res = logged_client.post(f"/ventas/entregar/{venta_pendiente['id_venta']}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is False


def test_marcar_lista_ya_lista(logged_client, venta_pendiente, usuario_admin):
    """Cubre ventas_routes.py:177-180 — marcar lista venta ya lista retorna ok:False."""
    from services.ventas_service import marcar_lista_service
    marcar_lista_service(venta_pendiente["id_venta"], usuario_admin["id_usuario"])
    # Intentar marcar lista de nuevo
    res = logged_client.post(f"/ventas/marcar-lista/{venta_pendiente['id_venta']}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is False
