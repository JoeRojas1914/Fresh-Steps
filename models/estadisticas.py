from db import get_db

# Re-exports — mantienen compatibilidad con todos los `from estadisticas import X` existentes
from .estadisticas_ventas import (
    generar_semanas_rango,
    contar_ventas_por_semana,
    obtener_unidades_por_semana,
    obtener_total_ingresos,
    obtener_ingresos_por_semana,
    contar_ventas_por_hora,
    obtener_ingresos_por_hora,
    obtener_unidades_por_hora,
    contar_ventas_por_dia_rango,
    obtener_ingresos_por_dia_rango,
    obtener_unidades_por_dia_rango,
    obtener_uso_servicios,
    obtener_ventas_con_y_sin_prepago,
    obtener_ventas_por_dia,
    obtener_ticket_promedio,
    obtener_saldo_por_cobrar,
    obtener_tiempo_promedio_entrega,
    obtener_ingresos_por_negocio,
    obtener_ventas_por_mes,
    obtener_ingresos_por_mes,
    obtener_unidades_por_mes,
    obtener_metodos_pago,
    obtener_hora_pico_recepcion,
    obtener_hora_pico_entrega,
)
from .estadisticas_gastos import (
    obtener_gastos_por_semana_y_proveedor,
    obtener_gastos_por_semana_y_categoria,
    obtener_total_gastos,
    obtener_gastos_por_mes,
)
from .estadisticas_clientes import (
    obtener_top_clientes,
    obtener_clientes_unicos,
    obtener_clientes_nuevos,
    obtener_tasa_retorno,
    obtener_gasto_promedio_cliente,
)


def ejecutar_query(sql, params=None):
    with get_db() as (_, cursor):
        cursor.execute(sql, params or [])
        return cursor.fetchall()
