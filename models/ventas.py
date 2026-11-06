from decimal import Decimal

from db import get_db
from config import TIPO_PAGO_FINAL
from utils import dinero
from .ventas_crear import crear_venta
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
    contar_entregas_resumen,
    contar_entregas_listas,
    contar_entregas_pendientes,
    contar_articulos_entregas,
    contar_ventas_cliente,
    obtener_ventas_cliente,
)


class VentaNoDisponible(ValueError):
    """La venta no existe, está eliminada o ya fue entregada."""


def _bloquear_venta_para_entrega(cursor, id_venta):
    """Bloquea la venta (FOR UPDATE) y regresa (venta, saldo_pendiente).

    Lanza ValueError si no existe, está eliminada, ya se entregó o no está lista."""
    cursor.execute("""
        SELECT total, fecha_lista, fecha_entrega, eliminado
        FROM venta
        WHERE id_venta = %s
        FOR UPDATE
    """, (id_venta,))
    venta = cursor.fetchone()
    if not venta or venta["eliminado"]:
        raise VentaNoDisponible("La venta no existe.")
    if venta["fecha_entrega"]:
        raise VentaNoDisponible("La venta ya fue entregada.")
    if not venta["fecha_lista"]:
        raise ValueError("La venta todavía no está lista para entregar.")

    cursor.execute(
        "SELECT COALESCE(SUM(monto), 0) AS pagado FROM pago_venta WHERE id_venta = %s",
        (id_venta,),
    )
    saldo = Decimal(str(venta["total"])) - Decimal(str(cursor.fetchone()["pagado"]))
    return venta, saldo


def marcar_entregada(id_venta, id_usuario):
    """Entrega una venta lista y ya pagada por completo.

    Regresa False si la venta ya estaba entregada o no existe. Lanza ValueError
    si no está lista o tiene saldo pendiente (debe cobrarse con el pago final)."""
    with get_db() as (_, cursor):
        try:
            _, saldo = _bloquear_venta_para_entrega(cursor, id_venta)
        except VentaNoDisponible:
            return False
        if saldo > 0:
            raise ValueError(
                f"La venta tiene saldo pendiente ({dinero(saldo)}). Registra el pago final para entregarla."
            )

        cursor.execute("""
            UPDATE venta
            SET fecha_entrega = NOW(),
                id_usuario_entrego = %s
            WHERE id_venta = %s
        """, (id_usuario, id_venta))
        registrar_historial_venta(cursor, id_venta, "ENTREGADO", id_usuario)
        return True


def registrar_pago_final_y_entregar(id_venta, monto: Decimal, metodo_pago, id_usuario):
    """Cobra el saldo pendiente y marca la venta como entregada en UNA transacción.

    La fila de la venta se bloquea (FOR UPDATE) para que dos envíos simultáneos
    no registren el pago dos veces. Lanza ValueError (y se revierte todo) si la
    venta no existe, está eliminada, no está lista, ya se entregó, no tiene
    saldo o el monto no es exactamente el saldo pendiente."""
    with get_db() as (_, cursor):
        _, saldo = _bloquear_venta_para_entrega(cursor, id_venta)
        if saldo <= 0:
            raise ValueError("La venta no tiene saldo pendiente.")
        if monto != saldo:
            raise ValueError(f"El monto debe ser igual al saldo pendiente ({dinero(saldo)}).")

        cursor.execute("""
            INSERT INTO pago_venta
                (id_venta, monto, tipo_pago, tipo_pago_venta, fecha_pago, id_usuario_cobro)
            VALUES (%s, %s, %s, %s, NOW(), %s)
        """, (id_venta, monto, metodo_pago, TIPO_PAGO_FINAL, id_usuario))

        cursor.execute("""
            UPDATE venta
            SET fecha_entrega = NOW(),
                id_usuario_entrego = %s
            WHERE id_venta = %s
        """, (id_usuario, id_venta))
        registrar_historial_venta(cursor, id_venta, "ENTREGADO", id_usuario)


def marcar_como_lista(id_venta, id_usuario=None):
    with get_db() as (_, cursor):
        cursor.execute("""
            UPDATE venta
            SET fecha_lista = NOW()
            WHERE id_venta = %s
              AND fecha_lista IS NULL
              AND fecha_entrega IS NULL
              AND eliminado = 0
        """, (id_venta,))

        afectadas = cursor.rowcount
        if afectadas > 0 and id_usuario:
            registrar_historial_venta(cursor, id_venta, "LISTA", id_usuario)

        return afectadas > 0


def revertir_lista(id_venta, id_usuario=None):
    with get_db() as (_, cursor):
        cursor.execute("""
            UPDATE venta
            SET fecha_lista = NULL
            WHERE id_venta = %s
              AND fecha_lista IS NOT NULL
              AND fecha_entrega IS NULL
              AND eliminado = 0
        """, (id_venta,))

        afectadas = cursor.rowcount
        if afectadas > 0 and id_usuario:
            registrar_historial_venta(cursor, id_venta, "REVERTIDO", id_usuario)

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
