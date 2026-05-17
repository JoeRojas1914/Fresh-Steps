from db import get_db
from .ventas_historial import registrar_historial_venta

# Re-exports — mantienen compatibilidad con todos los `from ventas import X` existentes
from .ventas_crear import TIPOS_POR_NEGOCIO, crear_venta
from .ventas_historial import (
    registrar_historial_venta,
    obtener_historial_venta,
    contar_historial_ventas,
    obtener_historial_ventas,
)
from .ventas_detalles import (
    obtener_venta,
    obtener_detalles_venta,
    obtener_ventas_listas,
    obtener_entregas_pendientes,
    contar_entregas_listas,
    contar_entregas_pendientes,
    contar_ventas_cliente,
    obtener_ventas_cliente,
)


def marcar_entregada(id_venta, id_usuario):
    with get_db() as (_, cursor):
        cursor.execute("""
            UPDATE venta
            SET fecha_entrega = NOW(),
                id_usuario_entrego = %s
            WHERE id_venta = %s
              AND fecha_entrega IS NULL
        """, (id_usuario, id_venta))

        afectadas = cursor.rowcount
        if afectadas > 0:
            registrar_historial_venta(cursor, id_venta, "ENTREGADO", id_usuario)

        return afectadas > 0


def marcar_como_lista(id_venta, id_usuario=None):
    with get_db() as (_, cursor):
        cursor.execute("""
            UPDATE venta
            SET fecha_lista = NOW()
            WHERE id_venta = %s
              AND fecha_lista IS NULL
              AND fecha_entrega IS NULL
        """, (id_venta,))

        afectadas = cursor.rowcount
        if afectadas > 0 and id_usuario:
            registrar_historial_venta(cursor, id_venta, "LISTA", id_usuario)

        return afectadas > 0


def eliminar_venta(id_venta, id_usuario=None):
    with get_db() as (_, cursor):
        cursor.execute("""
            UPDATE venta
            SET eliminado = 1,
                fecha_eliminado = NOW()
            WHERE id_venta = %s
              AND eliminado = 0
        """, (id_venta,))

        afectadas = cursor.rowcount
        if afectadas > 0 and id_usuario:
            registrar_historial_venta(cursor, id_venta, "ELIMINADO", id_usuario)

        return afectadas > 0
