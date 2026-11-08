"""
Orden "por pedidos" de la lista de clientes para una caja con negocios asignados:
debe contar solo los pedidos de esos negocios, igual que el número que se muestra.
"""
import pytest

from services.clientes_service import listar_clientes_service

PREFIJO = "ZZOrdenNegocio"


@pytest.fixture
def clientes_con_pedidos(db_conn, usuario_admin):
    """A: 1 pedido en calzado + 3 en confección.  B: 2 pedidos en calzado."""
    cur = db_conn.cursor()
    ids_cliente, ids_venta = {}, []
    for nombre, pedidos in (("A", {1: 1, 2: 3}), ("B", {1: 2})):
        cur.execute(
            "INSERT INTO cliente (nombre, apellido, activo, id_usuario) VALUES (%s, %s, 1, %s)",
            (PREFIJO, nombre, usuario_admin["id_usuario"]),
        )
        ids_cliente[nombre] = cur.lastrowid
        for id_negocio, n in pedidos.items():
            for _ in range(n):
                cur.execute(
                    "INSERT INTO venta (id_negocio, id_cliente, total, id_usuario_creo)"
                    " VALUES (%s, %s, 100, %s)",
                    (id_negocio, ids_cliente[nombre], usuario_admin["id_usuario"]),
                )
                ids_venta.append(cur.lastrowid)
    db_conn.commit()

    yield ids_cliente

    ph = ", ".join(["%s"] * len(ids_venta))
    cur.execute(f"DELETE FROM venta WHERE id_venta IN ({ph})", ids_venta)
    for cid in ids_cliente.values():
        cur.execute("DELETE FROM clientes_historial WHERE id_cliente = %s", (cid,))
        cur.execute("DELETE FROM cliente WHERE id_cliente = %s", (cid,))
    db_conn.commit()
    cur.close()


def _orden(id_negocio):
    res = listar_clientes_service(q=PREFIJO, por_pagina=50, orden="pedidos",
                                  direccion="desc", id_negocio=id_negocio)
    return [(c["apellido"], c["total_pedidos"]) for c in res["clientes"]]


def test_caja_calzado_ordena_por_sus_pedidos(clientes_con_pedidos):
    # Antes salía A primero (4 pedidos en total) aunque mostraba 1
    assert _orden([1]) == [("B", 2), ("A", 1)]


def test_admin_ordena_por_todos_los_pedidos(clientes_con_pedidos):
    assert _orden(None) == [("A", 4), ("B", 2)]
