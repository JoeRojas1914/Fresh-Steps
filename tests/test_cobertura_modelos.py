"""
Tests para alcanzar 100% de cobertura en models/*.
Cubre funciones y ramas que no son ejercidas por los tests de rutas/servicios.
"""
import pytest
from datetime import date


# ============================================================
# models/login.py:17-24  (obtener_usuario_caja_activo)
# ============================================================

def test_obtener_usuario_caja_activo():
    from models.login import obtener_usuario_caja_activo
    result = obtener_usuario_caja_activo()
    assert result is None or isinstance(result, dict)


# ============================================================
# models/pagos.py:41-48  (obtener_pagos_por_venta)
# ============================================================

def test_obtener_pagos_por_venta(venta_pendiente):
    from models.pagos import obtener_pagos_por_venta
    pagos = obtener_pagos_por_venta(venta_pendiente["id_venta"])
    assert isinstance(pagos, list)


# ============================================================
# models/usuario.py:11-13  (obtener_usuarios con q)
# ============================================================

def test_obtener_usuarios_con_q():
    from models.usuario import obtener_usuarios
    result = obtener_usuarios(q="test_admin_pytest")
    assert isinstance(result, dict)
    assert "usuarios" in result


# ============================================================
# models/estadisticas.py:46-48  (ejecutar_query)
# ============================================================

def test_ejecutar_query():
    from models.estadisticas import ejecutar_query
    result = ejecutar_query("SELECT 1 AS val")
    assert result[0]["val"] == 1


# ============================================================
# models/gastos.py:32  (eliminar_categoria con gastos en uso)
# ============================================================

def test_eliminar_categoria_en_uso_retorna_false(db_conn, usuario_admin):
    from models.gastos import eliminar_categoria
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO categoria_gasto (nombre) VALUES ('CatEnUso_pytest')")
    id_cat = cursor.lastrowid
    cursor.execute(
        "INSERT INTO gastos (id_negocio, descripcion, proveedor, total, "
        "fecha_registro, tipo_comprobante, tipo_pago, id_usuario, activo, id_categoria) "
        "VALUES (1, 'desc', 'prov', 10.00, '2030-01-01', 'ticket', 'efectivo', %s, 1, %s)",
        (usuario_admin["id_usuario"], id_cat),
    )
    id_gasto = cursor.lastrowid
    db_conn.commit()
    cursor.close()

    ok, msg = eliminar_categoria(id_cat)
    assert ok is False
    assert "No se puede eliminar" in msg

    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM gastos_historial WHERE id_gasto = %s", (id_gasto,))
    cursor.execute("DELETE FROM gastos WHERE id_gasto = %s", (id_gasto,))
    cursor.execute("DELETE FROM categoria_gasto WHERE id_categoria = %s", (id_cat,))
    db_conn.commit()
    cursor.close()


# ============================================================
# models/gastos.py:172-181  (obtener_gastos_por_proveedor)
# ============================================================

def test_obtener_gastos_por_proveedor():
    from models.gastos import obtener_gastos_por_proveedor
    result = obtener_gastos_por_proveedor(1, date(2020, 1, 1), date(2030, 12, 31))
    assert isinstance(result, list)


# ============================================================
# models/servicios.py:59-71  (obtener_servicio_por_id)
# ============================================================

def test_obtener_servicio_por_id_existente(servicio_calzado):
    from models.servicios import obtener_servicio_por_id
    result = obtener_servicio_por_id(servicio_calzado["id_servicio"])
    assert result is not None
    assert result["id_servicio"] == servicio_calzado["id_servicio"]


def test_obtener_servicio_por_id_inexistente():
    from models.servicios import obtener_servicio_por_id
    result = obtener_servicio_por_id(999999)
    assert result is None


def test_servicio_tiene_ventas(venta_pendiente, servicio_calzado):
    """Lines 106-113: servicio_tiene_ventas con cursor real."""
    from models.servicios import servicio_tiene_ventas
    from db import get_db
    sid = servicio_calzado["id_servicio"]
    with get_db() as (_, cursor):
        tiene = servicio_tiene_ventas(cursor, sid)
    assert tiene is True


# ============================================================
# models/clientes.py:90-98  (buscar_clientes_por_nombre)
# ============================================================

def test_buscar_clientes_por_nombre(cliente_test):
    from models.clientes import buscar_clientes_por_nombre
    result = buscar_clientes_por_nombre("TestNombre")
    assert isinstance(result, list)
    ids = [r["id_cliente"] for r in result]
    assert cliente_test["id_cliente"] in ids


# ============================================================
# models/clientes.py:169  (contar_pedidos_por_cliente lista vacía)
# ============================================================

def test_contar_pedidos_por_cliente_lista_vacia():
    from models.clientes import contar_pedidos_por_cliente
    result = contar_pedidos_por_cliente([])
    assert result == {}


# ============================================================
# models/ventas_historial.py:26,28,30,32  (_aplicar_filtro_estado)
# ============================================================

def test_contar_historial_ventas_estado_pendiente():
    from models.ventas_historial import contar_historial_ventas
    count = contar_historial_ventas(estado="pendiente")
    assert isinstance(count, int) and count >= 0


def test_contar_historial_ventas_estado_lista():
    from models.ventas_historial import contar_historial_ventas
    count = contar_historial_ventas(estado="lista")
    assert isinstance(count, int) and count >= 0


def test_contar_historial_ventas_estado_entregada():
    from models.ventas_historial import contar_historial_ventas
    count = contar_historial_ventas(estado="entregada")
    assert isinstance(count, int) and count >= 0


def test_contar_historial_ventas_estado_eliminada():
    from models.ventas_historial import contar_historial_ventas
    count = contar_historial_ventas(estado="eliminada")
    assert isinstance(count, int) and count >= 0


# ============================================================
# models/ventas_historial.py:69-71,73-74  (q e id_venta en contar)
# ============================================================

def test_contar_historial_ventas_con_q_e_id():
    from models.ventas_historial import contar_historial_ventas
    count = contar_historial_ventas(q="NoExiste_pytest_xyz", id_venta=999999)
    assert count == 0


# ============================================================
# models/ventas_historial.py:134-136,138-139  (q e id_venta en obtener)
# ============================================================

def test_obtener_historial_ventas_con_q_e_id():
    from models.ventas_historial import obtener_historial_ventas
    rows = obtener_historial_ventas(q="NoExiste_pytest_xyz", id_venta=999999)
    assert rows == []


# ============================================================
# models/ventas_detalles.py:78  (obtener_detalles_venta sin artículos)
# ============================================================

def test_obtener_detalles_venta_venta_inexistente():
    from models.ventas_detalles import obtener_detalles_venta
    result = obtener_detalles_venta([999999])
    assert result == {}


# ============================================================
# models/ventas_detalles.py:131-132,134-137  (obtener_ventas_listas filtros)
# ============================================================

def test_obtener_ventas_listas_con_id_venta_y_q():
    from models.ventas_detalles import obtener_ventas_listas
    result = obtener_ventas_listas(id_venta=999999, q="NoExiste_pytest")
    assert isinstance(result, list)


# ============================================================
# models/ventas_detalles.py:171-172,173-175,176-180
# (obtener_entregas_pendientes filtros)
# ============================================================

def test_obtener_entregas_pendientes_con_todos_filtros():
    from models.ventas_detalles import obtener_entregas_pendientes
    result = obtener_entregas_pendientes(id_negocio=1, id_venta=999999, q="NoExiste_pytest")
    assert isinstance(result, list)


# ============================================================
# models/ventas_detalles.py:203-204,205-209  (contar_entregas_resumen filtros)
# ============================================================

def test_contar_entregas_resumen_con_id_venta_y_q():
    from models.ventas_detalles import contar_entregas_resumen
    listas, pendientes = contar_entregas_resumen(id_venta=999999, q="NoExiste_pytest")
    assert listas == 0
    assert pendientes == 0


# ============================================================
# models/ventas_detalles.py:231-232,234-235,237-238
# (contar_ventas_cliente con filtros opcionales)
# ============================================================

def test_contar_ventas_cliente_con_todos_filtros(cliente_test):
    from models.ventas_detalles import contar_ventas_cliente
    count = contar_ventas_cliente(
        cliente_test["id_cliente"],
        id_negocio=1,
        fecha_inicio=date(2020, 1, 1),
        fecha_fin=date(2030, 12, 31),
    )
    assert isinstance(count, int)


# ============================================================
# models/ventas_detalles.py:257-258,260-261,263-264
# (obtener_ventas_cliente con filtros opcionales)
# ============================================================

def test_obtener_ventas_cliente_con_todos_filtros(cliente_test):
    from models.ventas_detalles import obtener_ventas_cliente
    result = obtener_ventas_cliente(
        cliente_test["id_cliente"],
        id_negocio=1,
        fecha_inicio=date(2020, 1, 1),
        fecha_fin=date(2030, 12, 31),
        limit=10,
        offset=0,
    )
    assert isinstance(result, list)


# ============================================================
# models/estadisticas_gastos.py:32-35  (inner loop con datos reales)
# ============================================================

def test_estadisticas_gastos_proveedor_semana_con_datos(gasto_test):
    from models.estadisticas_gastos import obtener_gastos_por_semana_y_proveedor
    inicio = date(2030, 1, 1)
    fin = date(2030, 1, 14)
    result = obtener_gastos_por_semana_y_proveedor(inicio, fin, "all")
    assert "labels" in result
    assert "datasets" in result


# ============================================================
# models/estadisticas_gastos.py:64-65,71-73  (negocio específico + inner loop)
# ============================================================

def test_estadisticas_gastos_categoria_semana_negocio_especifico(gasto_test):
    from models.estadisticas_gastos import obtener_gastos_por_semana_y_categoria
    inicio = date(2030, 1, 1)
    fin = date(2030, 1, 14)
    result = obtener_gastos_por_semana_y_categoria(inicio, fin, "1")
    assert "labels" in result
    assert "datasets" in result


# ============================================================
# models/estadisticas_gastos.py:100-115  (obtener_gastos_por_mes negocio)
# ============================================================

def test_obtener_gastos_por_mes_negocio_especifico():
    from models.estadisticas_gastos import obtener_gastos_por_mes
    result = obtener_gastos_por_mes(2024, "1")
    assert len(result) == 12
    assert result[0]["label"] == "Ene"


# ============================================================
# models/estadisticas_ventas.py:205-206,225-226,246-247,
#                               266-267,292-293,319-320
# (ramas id_negocio != "all")
# ============================================================

def test_estadisticas_ventas_con_negocio_especifico():
    from models.estadisticas_ventas import (
        contar_ventas_por_hora,
        obtener_ingresos_por_hora,
        obtener_unidades_por_hora,
        contar_ventas_por_dia_rango,
        obtener_ingresos_por_dia_rango,
        obtener_unidades_por_dia_rango,
    )
    inicio = date(2024, 1, 1)
    fin    = date(2024, 1, 7)

    r1 = contar_ventas_por_hora(inicio, fin, "1")
    assert len(r1) == 15

    r2 = obtener_ingresos_por_hora(inicio, fin, "1")
    assert len(r2) == 15

    r3 = obtener_unidades_por_hora(inicio, fin, "1")
    assert len(r3) == 15

    r4 = contar_ventas_por_dia_rango(inicio, fin, "1")
    assert len(r4) == 7

    r5 = obtener_ingresos_por_dia_rango(inicio, fin, "1")
    assert len(r5) == 7

    r6 = obtener_unidades_por_dia_rango(inicio, fin, "1")
    assert len(r6) == 7


# ============================================================
# models/estadisticas_ventas.py:495-510  (obtener_ventas_por_mes)
# ============================================================

def test_obtener_ventas_por_mes_negocio_especifico():
    from models.estadisticas_ventas import obtener_ventas_por_mes
    result = obtener_ventas_por_mes(2024, "1")
    assert len(result) == 12
    assert result[0]["label"] == "Ene"


# ============================================================
# models/estadisticas_ventas.py:514-530  (obtener_ingresos_por_mes)
# ============================================================

def test_obtener_ingresos_por_mes_negocio_especifico():
    from models.estadisticas_ventas import obtener_ingresos_por_mes
    result = obtener_ingresos_por_mes(2024, "1")
    assert len(result) == 12
    assert result[0]["label"] == "Ene"


# ============================================================
# models/estadisticas_ventas.py:534-575  (obtener_unidades_por_mes)
# Cubre las tres ramas: id_negocio "all", "2", "3"
# ============================================================

def test_obtener_unidades_por_mes_all():
    from models.estadisticas_ventas import obtener_unidades_por_mes
    result = obtener_unidades_por_mes(2024, "all")
    assert len(result) == 12


def test_obtener_unidades_por_mes_negocio_2():
    from models.estadisticas_ventas import obtener_unidades_por_mes
    result = obtener_unidades_por_mes(2024, "2")
    assert len(result) == 12


def test_obtener_unidades_por_mes_negocio_3():
    from models.estadisticas_ventas import obtener_unidades_por_mes
    result = obtener_unidades_por_mes(2024, "3")
    assert len(result) == 12


def test_obtener_unidades_por_mes_cubre_loops_con_datos(venta_pendiente, venta_confeccion, venta_maquila):
    """Lines 549,561,573: loops internos con ventas reales de los 3 negocios."""
    from models.estadisticas_ventas import obtener_unidades_por_mes
    import datetime
    anio = datetime.date.today().year
    result = obtener_unidades_por_mes(anio, "all")
    assert len(result) == 12
    assert sum(r["total"] for r in result) >= 3


# ============================================================
# models/estadisticas_ventas.py:652-653  (contar_unidades_hoy negocio)
# ============================================================

def test_contar_unidades_hoy_negocio_especifico():
    from models.estadisticas_ventas import contar_unidades_hoy
    result = contar_unidades_hoy("fecha_recibo", "1")
    assert isinstance(result, int)
