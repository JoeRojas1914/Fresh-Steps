"""Regresiones de la auditoría de noviembre 2026.

Cubre: secretos fuera del historial de usuario, validación de montos en ventas,
rol/ediciones atómicas de usuarios, sesión invalidada al desactivar, inyección de
fórmulas en Excel, paginación con páginas inválidas, filtro de fecha "hasta" y
logout solo por POST.
"""
import json
from datetime import date, datetime

import pytest

from services.excel_helpers import texto_seguro, xl_cell


def _form_maquila(id_cliente, **extra):
    form = {
        "id_negocio": "3",
        "id_cliente": str(id_cliente),
        "fecha_estimada": "2030-12-31 10:00:00",
        "articulos[0][tipo_articulo]": "maquila",
        "articulos[0][tipo]": "Playera",
        "articulos[0][cantidad]": "2",
        "articulos[0][precio_unitario]": "50.00",
    }
    form.update(extra)
    return form


# ---------------------------------------------------------------------------
# Historial de usuario sin hashes ni token
# ---------------------------------------------------------------------------

def test_historial_usuario_sin_secretos(app, logged_client, usuario_caja, db_conn):
    from services.usuarios_service import guardar_usuario_service
    with app.test_request_context("/"):
        guardar_usuario_service(usuario_caja["id_usuario"], usuario_caja["usuario"],
                                "OtraPass123!", "caja", "5544", nombre="Editado")

    res = logged_client.get(f"/usuarios/{usuario_caja['id_usuario']}/historial")
    assert res.status_code == 200
    texto = json.dumps(res.get_json())
    for secreto in ("password_hash", "pin_hash", "session_token"):
        assert secreto not in texto

    cur = db_conn.cursor(dictionary=True)
    cur.execute("SELECT datos_antes, datos_despues FROM historial_usuario WHERE id_usuario = %s",
                (usuario_caja["id_usuario"],))
    filas = cur.fetchall()
    cur.close()
    assert filas
    for f in filas:
        assert "pin_hash" not in str(f["datos_antes"]) + str(f["datos_despues"])
    despues = json.loads(filas[-1]["datos_despues"])
    assert despues["password_cambiado"] is True and despues["pin_cambiado"] is True


def test_historial_antiguo_con_secretos_se_limpia_al_leer(logged_client, usuario_caja, db_conn):
    cur = db_conn.cursor()
    cur.execute(
        "INSERT INTO historial_usuario (id_usuario, accion, datos_antes, datos_despues, usuario_admin)"
        " VALUES (%s, 'EDITADO', %s, NULL, 'x')",
        (usuario_caja["id_usuario"], json.dumps({"nombre": "A", "pin_hash": "pbkdf2:xxx"})),
    )
    db_conn.commit()
    cur.close()
    res = logged_client.get(f"/usuarios/{usuario_caja['id_usuario']}/historial")
    assert "pin_hash" not in json.dumps(res.get_json())


# ---------------------------------------------------------------------------
# Usuarios: rol válido y ediciones atómicas
# ---------------------------------------------------------------------------

def test_rol_invalido_rechazado(app, usuario_caja):
    from services.usuarios_service import guardar_usuario_service
    with app.test_request_context("/"), pytest.raises(ValueError, match="Rol"):
        guardar_usuario_service(usuario_caja["id_usuario"], usuario_caja["usuario"],
                                None, "superusuario", None)


def test_editar_sin_rol_conserva_el_actual(app, usuario_caja, db_conn):
    from services.usuarios_service import guardar_usuario_service
    with app.test_request_context("/"):
        guardar_usuario_service(usuario_caja["id_usuario"], usuario_caja["usuario"],
                                None, None, None, nombre="SinRol")
    cur = db_conn.cursor(dictionary=True)
    cur.execute("SELECT rol, nombre FROM usuario WHERE id_usuario = %s", (usuario_caja["id_usuario"],))
    row = cur.fetchone()
    cur.close()
    assert row == {"rol": "caja", "nombre": "SinRol"}


def test_password_invalido_no_modifica_nada(app, usuario_caja, db_conn):
    from services.usuarios_service import guardar_usuario_service
    with app.test_request_context("/"), pytest.raises(ValueError):
        guardar_usuario_service(usuario_caja["id_usuario"], usuario_caja["usuario"],
                                "corta", "caja", None, nombre="NoDebeGuardarse")
    cur = db_conn.cursor(dictionary=True)
    cur.execute("SELECT nombre FROM usuario WHERE id_usuario = %s", (usuario_caja["id_usuario"],))
    assert cur.fetchone()["nombre"] != "NoDebeGuardarse"
    cur.close()


def test_usuario_desactivado_pierde_la_sesion(app, client, usuario_caja, db_conn):
    cur = db_conn.cursor()
    cur.execute("UPDATE usuario SET session_token = 'tok_pytest' WHERE id_usuario = %s",
                (usuario_caja["id_usuario"],))
    db_conn.commit()
    cur.close()
    with client.session_transaction() as sess:
        sess.update({"id_usuario": usuario_caja["id_usuario"], "usuario": usuario_caja["usuario"],
                     "rol": "caja", "session_token": "tok_pytest",
                     "ultima_actividad": datetime.now().isoformat()})
    assert client.get("/ventas/pendientes").status_code == 200

    from services.usuarios_service import toggle_usuario_service
    with app.test_request_context("/"):
        assert toggle_usuario_service(usuario_caja["id_usuario"]) == 0

    res = client.get("/ventas/pendientes", follow_redirects=False)
    assert res.status_code == 302
    assert "login" in res.headers["Location"]


# ---------------------------------------------------------------------------
# Ventas: validación de montos, cliente y servicios
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("extra, mensaje", [
    ({"articulos[0][precio_unitario]": "abc"}, "precio unitario"),
    ({"articulos[0][precio_unitario]": "-5"}, "precio unitario"),
    ({"articulos[0][cantidad]": "0"}, "cantidad"),
    ({"articulos[0][cantidad]": "2.5"}, "cantidad"),
    ({"aplica_descuento": "si", "cantidad_descuento": "NaN"}, "descuento"),
    ({"aplica_descuento": "si", "cantidad_descuento": "-10"}, "descuento"),
    ({"fecha_estimada": "mañana"}, "fecha"),
])
def test_venta_con_datos_invalidos_da_400(logged_client, cliente_test, extra, mensaje):
    res = logged_client.post("/ventas/guardar", data=_form_maquila(cliente_test["id_cliente"], **extra))
    assert res.status_code == 400
    assert mensaje in res.get_json()["error"].lower()


def test_venta_con_cliente_eliminado_rechazada(logged_client, cliente_test, db_conn):
    cur = db_conn.cursor()
    cur.execute("UPDATE cliente SET activo = 0 WHERE id_cliente = %s", (cliente_test["id_cliente"],))
    db_conn.commit()
    cur.close()
    res = logged_client.post("/ventas/guardar", data=_form_maquila(cliente_test["id_cliente"]))
    assert res.status_code == 400
    assert "cliente" in res.get_json()["error"].lower()


def test_venta_con_servicio_de_otro_negocio_rechazada(logged_client, cliente_test, servicio_confeccion):
    form = {
        "id_negocio": "1",
        "id_cliente": str(cliente_test["id_cliente"]),
        "fecha_estimada": "2030-12-31 10:00:00",
        "articulos[0][tipo_articulo]": "calzado",
        "articulos[0][tipo]": "Tenis",
        "articulos[0][marca]": "Nike",
        "articulos[0][material]": "Piel",
        "articulos[0][color_base]": "Blanco",
        "articulos[0][servicios][0][id_servicio]": str(servicio_confeccion["id_servicio"]),
        "articulos[0][servicios][0][precio_aplicado]": "100.00",
    }
    res = logged_client.post("/ventas/guardar", data=form)
    assert res.status_code == 400
    assert "servicio" in res.get_json()["error"].lower()


# ---------------------------------------------------------------------------
# Excel: inyección de fórmulas
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("valor", ["=1+1", "+SUM(A1)", "-2+3", "@cmd", '=HYPERLINK("http://x")'])
def test_texto_que_parece_formula_se_escapa(valor):
    assert texto_seguro(valor) == "'" + valor


def test_xl_cell_no_escribe_formulas():
    from openpyxl import Workbook
    ws = Workbook().active
    c = xl_cell(ws, 1, 1, "=1+1")
    assert c.data_type == "s"
    assert xl_cell(ws, 2, 1, 150.5).value == 150.5
    assert xl_cell(ws, 3, 1, "Juan").value == "Juan"


# ---------------------------------------------------------------------------
# Paginación con página inválida
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ruta", [
    "/ventas/historial?pagina=0", "/ventas/historial?pagina=-3",
    "/ventas/pendientes?pagina=-1", "/ventas/listas?pagina=0",
    "/clientes?pagina=-1", "/servicios?pagina=0", "/usuarios?pagina=-2",
    "/pagos?pagina=0", "/gastos?pagina=-1",
])
def test_pagina_invalida_no_rompe(logged_client, ruta):
    assert logged_client.get(ruta).status_code == 200


def test_perfil_cliente_pagina_texto_no_rompe(logged_client, cliente_test):
    res = logged_client.get(f"/clientes/{cliente_test['id_cliente']}?pagina=abc")
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# Filtro "hasta" incluye ventas de ese día
# ---------------------------------------------------------------------------

def test_fecha_fin_incluye_ventas_del_mismo_dia(venta_pendiente, cliente_test):
    from models.ventas import contar_ventas_cliente
    hoy = date.today().isoformat()
    assert contar_ventas_cliente(cliente_test["id_cliente"], fecha_inicio=hoy, fecha_fin=hoy) >= 1


# ---------------------------------------------------------------------------
# Logout solo por POST
# ---------------------------------------------------------------------------

def test_logout_por_get_no_permitido(logged_client):
    assert logged_client.get("/logout").status_code == 405


def test_next_con_barra_invertida_no_redirige_fuera(logged_client, db_conn):
    res = logged_client.post("/clientes/guardar", data={
        "nombre": "RedirPytest", "apellido": "Test", "next": "/\\evil.com",
    }, follow_redirects=False)
    try:
        assert res.headers["Location"].endswith("/clientes")
    finally:
        cur = db_conn.cursor()
        cur.execute("DELETE FROM clientes_historial WHERE id_cliente IN"
                    " (SELECT id_cliente FROM cliente WHERE nombre = 'RedirPytest')")
        cur.execute("DELETE FROM cliente WHERE nombre = 'RedirPytest'")
        db_conn.commit()
        cur.close()


# ---------------------------------------------------------------------------
# Segunda ronda: rangos de fecha sin DATE(), caché acotada, logs y WhatsApp
# ---------------------------------------------------------------------------

def test_historial_rango_de_un_dia_incluye_venta_de_hoy(app, venta_pendiente):
    from services.ventas_service import historial_ventas_service
    hoy = date.today().isoformat()
    with app.test_request_context("/"):
        data = historial_ventas_service(fecha_inicio=hoy, fecha_fin=hoy,
                                        id_venta=venta_pendiente["id_venta"])
    assert data["total_registros"] == 1


def test_kpis_de_hoy_cuentan_la_venta_recien_creada(venta_pendiente):
    from models.estadisticas_ventas import contar_unidades_hoy, contar_ventas_por_dia_rango
    hoy = date.today()
    assert contar_unidades_hoy("fecha_recibo", "1") >= 1
    assert contar_ventas_por_dia_rango(hoy, hoy, "1")[0]["total"] >= 1


def test_pagos_rango_de_un_dia_incluye_pago_de_hoy(app, logged_client, venta_pendiente):
    from services.pagos_service import listar_pagos_service
    logged_client.post(f"/ventas/marcar-lista/{venta_pendiente['id_venta']}")
    logged_client.post("/ventas/pago-final", json={
        "id_venta": venta_pendiente["id_venta"], "monto": "150.00", "metodo_pago": "efectivo",
    })
    hoy = date.today().isoformat()
    data = listar_pagos_service([1], None, None, hoy, hoy, pagina=1)
    assert any(p["id_venta"] == venta_pendiente["id_venta"] for p in data["pagos"])


def test_cache_de_servicios_no_guarda_negocios_inexistentes():
    from services import servicios_service as ss
    ss._invalidar_cache_servicios()
    assert ss.listar_servicios_api(987654)["servicios"] == []
    assert "987654" not in ss._servicios_cache


def test_logs_de_acceso_de_werkzeug_no_van_al_archivo():
    import logging
    from logging.handlers import RotatingFileHandler
    fh = next(h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler))

    def registro(nombre, nivel):
        return logging.LogRecord(nombre, nivel, __file__, 1, "GET /api/clientes?q=Juan", None, None)

    assert not fh.filter(registro("werkzeug", logging.INFO))
    assert fh.filter(registro("werkzeug", logging.ERROR))
    assert fh.filter(registro("routes.ventas_routes", logging.INFO))


def test_mi_perfil_no_expone_hashes(app, usuario_caja):
    from services.usuarios_service import obtener_mi_perfil_service
    perfil = obtener_mi_perfil_service(usuario_caja["id_usuario"])
    assert perfil["usuario"] == usuario_caja["usuario"]
    assert not {"password_hash", "pin_hash", "session_token"} & perfil.keys()


@pytest.mark.parametrize("ruta", ["/clientes/exportar", "/servicios/exportar", "/gastos/exportar",
                                  "/pagos/exportar-excel"])
def test_exportaciones_siguen_generando_xlsx(logged_client, ruta):
    res = logged_client.get(ruta)
    assert res.status_code == 200
    assert res.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
