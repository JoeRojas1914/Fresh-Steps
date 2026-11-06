"""Pago final (/ventas/pago-final): validación, atomicidad y permisos.

Cubre los hallazgos C1 y C2 de reviews/audit-plan-full.md:
- un solo pago aunque se envíe dos veces
- monto no numérico, distinto al saldo o <= 0
- venta pendiente, eliminada o ya entregada
- id con formato raro ("123 ") que saltaba el permiso por negocio
"""
import pytest

from utils import a_entero, a_monto

SALDO = "150.00"   # venta_pendiente: 1 servicio de $150 sin prepago


def _pagos(db_conn, id_venta):
    db_conn.commit()
    cur = db_conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS n, COALESCE(SUM(monto), 0) AS s FROM pago_venta WHERE id_venta = %s",
                (id_venta,))
    row = cur.fetchone()
    cur.execute("SELECT fecha_entrega FROM venta WHERE id_venta = %s", (id_venta,))
    row["entregada"] = cur.fetchone()["fecha_entrega"] is not None
    cur.close()
    return row


def _pagar(client, id_venta, monto=SALDO, metodo="efectivo"):
    return client.post("/ventas/pago-final", json={"id_venta": id_venta, "monto": monto, "metodo_pago": metodo})


@pytest.fixture
def venta_lista(logged_client, venta_pendiente):
    logged_client.post(f"/ventas/marcar-lista/{venta_pendiente['id_venta']}")
    return venta_pendiente


# ── Caso feliz ────────────────────────────────────────────────────────────────

def test_pago_final_cobra_y_entrega(logged_client, db_conn, venta_lista):
    res = _pagar(logged_client, venta_lista["id_venta"])
    assert res.status_code == 200 and res.get_json()["ok"] is True
    pagos = _pagos(db_conn, venta_lista["id_venta"])
    assert pagos["n"] == 1 and float(pagos["s"]) == 150.0 and pagos["entregada"]


def test_pago_final_acepta_monto_numerico(logged_client, db_conn, venta_lista):
    """El JS manda el saldo como número (150), no como texto."""
    res = _pagar(logged_client, venta_lista["id_venta"], monto=150)
    assert res.status_code == 200


# ── C1: doble envío y validación del monto ────────────────────────────────────

def test_pago_final_doble_envio_registra_un_solo_pago(logged_client, db_conn, venta_lista):
    assert _pagar(logged_client, venta_lista["id_venta"]).status_code == 200
    res = _pagar(logged_client, venta_lista["id_venta"])
    assert res.status_code == 400
    assert "ya fue entregada" in res.get_json()["error"]
    assert _pagos(db_conn, venta_lista["id_venta"])["n"] == 1


@pytest.mark.parametrize("monto", ["abc", "NaN", "Infinity", "1e999999"])
def test_pago_final_monto_no_numerico_400(logged_client, db_conn, venta_lista, monto):
    res = _pagar(logged_client, venta_lista["id_venta"], monto=monto)
    assert res.status_code == 400
    assert _pagos(db_conn, venta_lista["id_venta"])["n"] == 0


@pytest.mark.parametrize("monto", ["0", "-150"])
def test_pago_final_monto_no_positivo_400(logged_client, db_conn, venta_lista, monto):
    res = _pagar(logged_client, venta_lista["id_venta"], monto=monto)
    assert res.status_code == 400
    assert _pagos(db_conn, venta_lista["id_venta"])["n"] == 0


@pytest.mark.parametrize("monto", ["100.00", "151.00"])
def test_pago_final_monto_distinto_al_saldo_400(logged_client, db_conn, venta_lista, monto):
    res = _pagar(logged_client, venta_lista["id_venta"], monto=monto)
    assert res.status_code == 400
    assert "saldo pendiente" in res.get_json()["error"]
    pagos = _pagos(db_conn, venta_lista["id_venta"])
    assert pagos["n"] == 0 and not pagos["entregada"]


# ── C1: estado de la venta ────────────────────────────────────────────────────

def test_pago_final_venta_no_lista_400(logged_client, db_conn, venta_pendiente):
    res = _pagar(logged_client, venta_pendiente["id_venta"])
    assert res.status_code == 400
    assert "no está lista" in res.get_json()["error"]
    assert _pagos(db_conn, venta_pendiente["id_venta"])["n"] == 0


def test_pago_final_venta_eliminada_400(logged_client, db_conn, venta_lista):
    logged_client.post(f"/ventas/eliminar/{venta_lista['id_venta']}")
    res = _pagar(logged_client, venta_lista["id_venta"])
    assert res.status_code == 400
    assert _pagos(db_conn, venta_lista["id_venta"])["n"] == 0


def test_pago_final_venta_inexistente_400(logged_client):
    res = _pagar(logged_client, 999_999_999)
    assert res.status_code == 400


# ── C2: formato del id y permiso por negocio ──────────────────────────────────

@pytest.mark.parametrize("id_raro", ["{id} ", " {id}", "{id}.0", "0x{id}", True])
def test_pago_final_id_con_formato_raro_400(logged_client, db_conn, venta_lista, id_raro):
    idv = venta_lista["id_venta"]
    valor = id_raro.format(id=idv) if isinstance(id_raro, str) else id_raro
    res = _pagar(logged_client, valor)
    assert res.status_code == 400
    assert _pagos(db_conn, idv)["n"] == 0


def test_caja_no_puede_cobrar_venta_ajena_con_id_raro(client, db_conn, usuario_caja, venta_lista):
    """Antes: "123 " saltaba el permiso y la caja cobraba ventas de otro negocio."""
    from datetime import datetime
    cur = db_conn.cursor()
    cur.execute("DELETE FROM usuario_negocio WHERE id_usuario = %s AND id_negocio <> 2",
                (usuario_caja["id_usuario"],))
    db_conn.commit()
    cur.close()
    with client.session_transaction() as s:
        s.update(id_usuario=usuario_caja["id_usuario"], usuario=usuario_caja["usuario"],
                 rol="caja", ultima_actividad=datetime.now().isoformat())

    idv = venta_lista["id_venta"]   # negocio 1
    assert _pagar(client, f"{idv} ").status_code == 400
    assert _pagar(client, idv).status_code == 403
    pagos = _pagos(db_conn, idv)
    assert pagos["n"] == 0 and not pagos["entregada"]


# ── Helpers ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("valor,esperado", [
    (5, 5), ("5", 5), (0, None), (-3, None), ("5 ", None), ("5.0", None),
    ("", None), (None, None), (True, None), (5.0, None), ("abc", None),
])
def test_a_entero(valor, esperado):
    assert a_entero(valor) == esperado


@pytest.mark.parametrize("valor,esperado", [
    ("150", "150.00"), (150, "150.00"), (150.5, "150.50"), (" 10.005 ", "10.00"),
    ("abc", None), ("NaN", None), ("Infinity", None), ("", None), (None, None), (True, None),
])
def test_a_monto(valor, esperado):
    resultado = a_monto(valor)
    assert (str(resultado) if resultado is not None else None) == esperado
