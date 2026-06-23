from decimal import Decimal
from db import get_db
from .ventas_crear import _INSERTADORES, _resolver_precio
from .ventas_historial import registrar_historial_venta
from .negocio import cargar_tipos_por_negocio
from .ventas_detalles import _extraer_datos

_CAMPOS_ARTICULO = {
    "calzado":    ("articulo_calzado",    ["tipo","marca","material","color_base","color_secundario","color_agujetas"]),
    "confeccion": ("articulo_confeccion", ["tipo","marca","material","color_base","color_secundario","cantidad"]),
    "maquila":    ("articulo_maquila",    ["tipo","cantidad","precio_unitario"]),
}
_NUMERICOS = {"cantidad", "precio_unitario"}

_CAMPOS_REQUERIDOS = {
    "calzado":    {"tipo", "marca", "material", "color_base"},
    "confeccion": {"tipo", "marca", "material", "color_base", "cantidad"},
    "maquila":    {"tipo", "cantidad", "precio_unitario"},
}

_ETIQUETAS_CAMPO = {
    "tipo": "Tipo", "marca": "Marca", "material": "Material",
    "color_base": "Color base", "cantidad": "Cantidad", "precio_unitario": "Precio unitario",
}

_CAMPOS_MINIMO = {"cantidad": Decimal("1"), "precio_unitario": Decimal("0.01")}


def _conv_campo(campo, valor):
    if campo in _NUMERICOS:
        return Decimal(str(valor or "0"))
    return valor


def obtener_venta_para_editar(id_venta):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT
                v.id_venta,
                v.id_negocio,
                v.fecha_estimada,
                v.aplica_descuento,
                v.cantidad_descuento,
                v.total,
                CONCAT(c.nombre, ' ', c.apellido) AS nombre_cliente,
                n.nombre AS negocio_nombre,
                COALESCE(SUM(p.monto), 0) AS total_pagado
            FROM venta v
            JOIN cliente c ON c.id_cliente = v.id_cliente
            JOIN negocio n ON n.id_negocio = v.id_negocio
            LEFT JOIN pago_venta p ON p.id_venta = v.id_venta
            WHERE v.id_venta = %s
              AND v.eliminado = 0
              AND v.fecha_lista IS NULL
              AND v.fecha_entrega IS NULL
            GROUP BY v.id_venta
        """, (id_venta,))
        return cursor.fetchone()


def obtener_articulos_con_servicios(id_venta):
    with get_db() as (_, cursor):
        cursor.execute(
            "SELECT"
            "  a.id_articulo, a.tipo_articulo, a.comentario,"
            "  ac.tipo  AS c_tipo,  ac.marca AS c_marca,  ac.material AS c_material,"
            "  ac.color_base AS c_color_base, ac.color_secundario AS c_color_secundario,"
            "  ac.color_agujetas AS c_color_agujetas,"
            "  acf.tipo AS cf_tipo, acf.marca AS cf_marca, acf.material AS cf_material,"
            "  acf.color_base AS cf_color_base, acf.color_secundario AS cf_color_secundario,"
            "  acf.cantidad AS cf_cantidad,"
            "  am.tipo AS m_tipo, am.cantidad AS m_cantidad, am.precio_unitario AS m_precio_unitario"
            " FROM articulo a"
            " LEFT JOIN articulo_calzado    ac  ON ac.id_articulo  = a.id_articulo"
            " LEFT JOIN articulo_confeccion acf ON acf.id_articulo = a.id_articulo"
            " LEFT JOIN articulo_maquila    am  ON am.id_articulo  = a.id_articulo"
            " WHERE a.id_venta = %s",
            (id_venta,),
        )
        filas = cursor.fetchall()
        if not filas:
            return []

        ids_articulo = [f["id_articulo"] for f in filas]
        ph = ",".join(["%s"] * len(ids_articulo))
        cursor.execute(
            "SELECT asv.id_articulo, asv.id_servicio, s.nombre, asv.precio_aplicado"
            " FROM articulo_servicio asv"
            " JOIN servicio s ON s.id_servicio = asv.id_servicio"
            " WHERE asv.id_articulo IN (" + ph + ")",
            tuple(ids_articulo),
        )
        servicios_map: dict = {}
        for s in cursor.fetchall():
            servicios_map.setdefault(s["id_articulo"], []).append({
                "id_servicio":    s["id_servicio"],
                "nombre":         s["nombre"],
                "precio_aplicado": s["precio_aplicado"],
            })

        result = []
        for f in filas:
            result.append({
                "id_articulo":   f["id_articulo"],
                "tipo_articulo": f["tipo_articulo"],
                "datos":         _extraer_datos(f["tipo_articulo"], f),
                "servicios":     servicios_map.get(f["id_articulo"], []),
                "comentario":    f["comentario"],
            })
        return result


def editar_venta(id_venta, fecha_estimada, nuevos_articulos, nuevos_servicios_por_articulo,
                 ediciones_servicio, eliminaciones_servicio, id_usuario, ediciones_articulo=None):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT id_negocio, fecha_estimada, total
            FROM venta
            WHERE id_venta = %s
              AND eliminado = 0
              AND fecha_lista IS NULL
              AND fecha_entrega IS NULL
            FOR UPDATE
        """, (id_venta,))
        venta = cursor.fetchone()
        if not venta:
            raise ValueError("La venta no existe o ya no está en estado pendiente.")

        datos_antes = {
            "fecha_estimada": str(venta["fecha_estimada"]),
            "total":          float(venta["total"]),
        }

        cursor.execute(
            "SELECT COALESCE(SUM(monto), 0) AS total_pagado FROM pago_venta WHERE id_venta = %s",
            (id_venta,),
        )
        total_pagado = Decimal(str(cursor.fetchone()["total_pagado"]))

        id_negocio    = venta["id_negocio"]
        total_actual  = Decimal(str(venta["total"]))
        delta_total   = Decimal("0.00")
        tipos_negocio = cargar_tipos_por_negocio()
        tipo_esperado = tipos_negocio.get(id_negocio)

        def _info_srv(id_art, id_srv):
            cursor.execute("""
                SELECT asv.precio_aplicado, a.tipo_articulo,
                       COALESCE(acf.cantidad, 1) AS cantidad,
                       s.nombre AS nombre_servicio
                FROM articulo_servicio asv
                JOIN articulo a ON a.id_articulo = asv.id_articulo
                JOIN servicio s ON s.id_servicio = asv.id_servicio
                LEFT JOIN articulo_confeccion acf
                          ON acf.id_articulo = asv.id_articulo
                WHERE asv.id_articulo = %s
                  AND asv.id_servicio = %s
                  AND a.id_venta = %s
            """, (id_art, id_srv, id_venta))
            return cursor.fetchone()

        ids_eliminados  = set()
        eliminados_log  = []
        for elm in (eliminaciones_servicio or []):
            id_art, id_srv = elm["id_articulo"], elm["id_servicio"]
            row = _info_srv(id_art, id_srv)
            if not row:
                continue
            precio_old = Decimal(str(row["precio_aplicado"]))
            mult       = (Decimal(str(row["cantidad"])) if row["tipo_articulo"] == "confeccion"
                          else Decimal("1"))
            delta_total -= precio_old * mult
            cursor.execute(
                "DELETE FROM articulo_servicio"
                " WHERE id_articulo = %s AND id_servicio = %s",
                (id_art, id_srv),
            )
            ids_eliminados.add((id_art, id_srv))
            eliminados_log.append({
                "nombre": row["nombre_servicio"],
                "precio": float(precio_old),
            })

        editados_log = []
        for edt in (ediciones_servicio or []):
            id_art, id_srv = edt["id_articulo"], edt["id_servicio"]
            if (id_art, id_srv) in ids_eliminados:
                continue
            row = _info_srv(id_art, id_srv)
            if not row:
                continue
            precio_old = Decimal(str(row["precio_aplicado"]))
            precio_new = Decimal(str(edt["precio_aplicado"]))
            if precio_new == precio_old:
                continue
            mult = (Decimal(str(row["cantidad"])) if row["tipo_articulo"] == "confeccion"
                    else Decimal("1"))
            delta_total += (precio_new - precio_old) * mult
            cursor.execute(
                "UPDATE articulo_servicio SET precio_aplicado = %s"
                " WHERE id_articulo = %s AND id_servicio = %s",
                (str(precio_new), id_art, id_srv),
            )
            editados_log.append({
                "nombre":       row["nombre_servicio"],
                "precio_antes": float(precio_old),
                "precio_nuevo": float(precio_new),
            })

        arts_editados_count  = 0
        detalles_arts_editados = []
        for id_art, cambios in (ediciones_articulo or {}).items():
            cursor.execute(
                "SELECT a.tipo_articulo,"
                " COALESCE(acf.cantidad, 1) AS conf_cant,"
                " COALESCE(am.cantidad, 0) AS m_cant,"
                " COALESCE(am.precio_unitario, 0) AS m_pu"
                " FROM articulo a"
                " LEFT JOIN articulo_confeccion acf ON acf.id_articulo = a.id_articulo"
                " LEFT JOIN articulo_maquila    am  ON am.id_articulo  = a.id_articulo"
                " WHERE a.id_articulo = %s AND a.id_venta = %s",
                (id_art, id_venta)
            )
            art_row = cursor.fetchone()
            if not art_row:
                continue
            tipo = art_row["tipo_articulo"]
            cfg  = _CAMPOS_ARTICULO.get(tipo)
            if not cfg:
                continue
            tabla, campos_validos = cfg
            updates = {c: cambios[c] for c in campos_validos if c in cambios}
            if not updates:
                continue

            # Rechazar si un campo obligatorio está vacío o bajo el mínimo permitido
            for campo_req in _CAMPOS_REQUERIDOS.get(tipo, set()):
                if campo_req not in updates:
                    continue
                str_val = str(updates[campo_req]).strip()
                invalido = str_val == ""
                if not invalido and campo_req in _CAMPOS_MINIMO:
                    try:
                        invalido = Decimal(str_val) < _CAMPOS_MINIMO[campo_req]
                    except Exception:
                        invalido = True
                if invalido:
                    cursor.execute(
                        "SELECT COUNT(*) + 1 AS pos FROM articulo"
                        " WHERE id_venta = %s AND id_articulo < %s",
                        (id_venta, id_art),
                    )
                    pos = cursor.fetchone()["pos"]
                    etiq = _ETIQUETAS_CAMPO.get(campo_req, campo_req)
                    sufijo = "debe ser mayor a 0." if campo_req in _CAMPOS_MINIMO else "es obligatorio."
                    raise ValueError(f"Art. #{pos}: \"{etiq}\" {sufijo}")

            cols = ", ".join(f"`{c}`" for c in campos_validos)
            cursor.execute(f"SELECT {cols} FROM {tabla} WHERE id_articulo = %s", (id_art,))
            orig = cursor.fetchone() or {}
            cambios_reales = []
            for campo in campos_validos:
                if campo not in cambios:
                    continue
                val_antes  = str(orig.get(campo) if orig.get(campo) is not None else "")
                val_despues = str(cambios[campo])
                if val_antes.strip() != val_despues.strip():
                    cambios_reales.append({
                        "campo":   campo,
                        "antes":   val_antes,
                        "despues": val_despues,
                    })

            if tipo == "confeccion" and "cantidad" in updates:
                old_cant = Decimal(str(art_row["conf_cant"]))
                new_cant = Decimal(str(updates["cantidad"]))
                if old_cant != new_cant:
                    cursor.execute(
                        "SELECT COALESCE(SUM(precio_aplicado), 0) AS s"
                        " FROM articulo_servicio WHERE id_articulo = %s",
                        (id_art,)
                    )
                    delta_total += (new_cant - old_cant) * Decimal(str(cursor.fetchone()["s"]))
            if tipo == "maquila" and ("cantidad" in updates or "precio_unitario" in updates):
                old_cant = Decimal(str(art_row["m_cant"]))
                old_pu   = Decimal(str(art_row["m_pu"]))
                new_cant = Decimal(str(updates.get("cantidad", old_cant)))
                new_pu   = Decimal(str(updates.get("precio_unitario", old_pu)))
                delta_total += (new_cant * new_pu) - (old_cant * old_pu)
            set_clause = ", ".join(f"`{c}` = %s" for c in updates)
            vals = [_conv_campo(c, v) for c, v in updates.items()]
            cursor.execute(
                f"UPDATE {tabla} SET {set_clause} WHERE id_articulo = %s",
                vals + [id_art],
            )

            if cambios_reales:
                cursor.execute(
                    "SELECT COUNT(*) + 1 AS pos FROM articulo"
                    " WHERE id_venta = %s AND id_articulo < %s",
                    (id_venta, id_art),
                )
                pos = cursor.fetchone()["pos"]
                detalles_arts_editados.append({
                    "num":     pos,
                    "tipo":    tipo,
                    "cambios": cambios_reales,
                })
                arts_editados_count += 1

        for art in nuevos_articulos:
            if tipo_esperado and art["tipo_articulo"] != tipo_esperado:
                raise ValueError(f"Este negocio solo permite artículos tipo: {tipo_esperado}")
            cursor.execute(
                "INSERT INTO articulo (id_venta, tipo_articulo, comentario) VALUES (%s, %s, %s)",
                (id_venta, art["tipo_articulo"], art.get("comentario")),
            )
            id_articulo = cursor.lastrowid
            insertador  = _INSERTADORES.get(art["tipo_articulo"])
            if not insertador:
                raise ValueError(f"Tipo de artículo desconocido: {art['tipo_articulo']}")
            delta_total += insertador(cursor, id_articulo, art)

        for entry in nuevos_servicios_por_articulo:
            id_articulo_ex = entry["id_articulo"]
            cursor.execute("""
                SELECT a.id_articulo, a.tipo_articulo, acf.cantidad
                FROM articulo a
                LEFT JOIN articulo_confeccion acf ON acf.id_articulo = a.id_articulo
                WHERE a.id_articulo = %s AND a.id_venta = %s
            """, (id_articulo_ex, id_venta))
            art_row = cursor.fetchone()
            if not art_row:
                raise ValueError(f"Artículo {id_articulo_ex} no pertenece a esta venta.")
            if art_row["tipo_articulo"] not in ("calzado", "confeccion"):
                raise ValueError("Solo se pueden agregar servicios a artículos de calzado o confección.")

            for s in entry["servicios"]:
                cursor.execute(
                    "SELECT 1 FROM articulo_servicio WHERE id_articulo = %s AND id_servicio = %s",
                    (id_articulo_ex, int(s["id_servicio"])),
                )
                if cursor.fetchone():
                    raise ValueError(
                        f"El servicio ya está asignado a este artículo (id_servicio={s['id_servicio']})."
                    )
                precio = _resolver_precio(cursor, s)
                cursor.execute(
                    "INSERT INTO articulo_servicio (id_articulo, id_servicio, precio_aplicado) VALUES (%s, %s, %s)",
                    (id_articulo_ex, int(s["id_servicio"]), precio),
                )
                if art_row["tipo_articulo"] == "confeccion":
                    cantidad = Decimal(str(art_row["cantidad"] or 1))
                    delta_total += cantidad * precio
                else:
                    delta_total += precio

        if fecha_estimada:
            cursor.execute(
                "UPDATE venta SET fecha_estimada = %s WHERE id_venta = %s",
                (fecha_estimada, id_venta),
            )

        total_nuevo = total_actual + delta_total
        if total_nuevo < total_pagado:
            raise ValueError(
                f"El nuevo total (${total_nuevo:.2f}) no puede ser menor al total ya pagado (${total_pagado:.2f})."
            )

        cursor.execute(
            "UPDATE venta SET total = %s WHERE id_venta = %s",
            (str(total_nuevo), id_venta),
        )

        datos_despues = {
            "fecha_estimada":       fecha_estimada or str(venta["fecha_estimada"]),
            "total":                float(total_nuevo),
            "delta_total":          float(delta_total),
            "nuevos_arts":          len(nuevos_articulos),
            "nuevos_srv":           sum(len(e["servicios"]) for e in nuevos_servicios_por_articulo),
            "precios_editados":       editados_log,
            "servicios_eliminados":   eliminados_log,
            "arts_editados":          arts_editados_count,
            "detalles_arts_editados": detalles_arts_editados,
        }
        registrar_historial_venta(cursor, id_venta, "EDITADO", id_usuario, datos_antes, datos_despues)

        return {"total_nuevo": float(total_nuevo)}
