from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session


from services.clientes_service import (
    listar_clientes_service,
    guardar_cliente_service,
    eliminar_cliente_service,
    restaurar_cliente_service,
    buscar_clientes_service,
    obtener_cliente_detalle_service,
    obtener_historial_cliente_service
)

clientes_bp = Blueprint("clientes", __name__)



@clientes_bp.route("/clientes")
def clientes():

    q = request.args.get("q", "")
    pagina = request.args.get("pagina", 1, type=int)
    incluir_eliminados = request.args.get("eliminados") == "1"

    data = listar_clientes_service(
        q=q,
        pagina=pagina,
        incluir_eliminados=incluir_eliminados
    )

    return render_template(
        "clientes.html",
        clientes=data["clientes"],
        q=q,
        pagina=pagina,
        total_paginas=data["total_paginas"],
        incluir_eliminados=incluir_eliminados
    )



@clientes_bp.route("/clientes/guardar", methods=["POST"])
def guardar_cliente():

    id_usuario = session["id_usuario"]

    resultado = guardar_cliente_service(request.form, id_usuario)

    flash(
        "✅ Cliente actualizado correctamente." if resultado == "actualizado"
        else "✅ Cliente creado correctamente.",
        "success"
    )

    return redirect(url_for("clientes.clientes"))



@clientes_bp.route("/clientes/eliminar/<int:id_cliente>")
def eliminar_cliente(id_cliente):

    id_usuario = session["id_usuario"]

    ok = eliminar_cliente_service(id_cliente, id_usuario)

    if not ok:
        flash("❌ No puedes eliminar el cliente porque ya tiene ventas registradas.", "error")
    else:
        flash("🗑️ Cliente eliminado correctamente.", "success")

    return redirect(url_for("clientes.clientes"))



@clientes_bp.route("/clientes/restaurar/<int:id_cliente>")
def restaurar_cliente(id_cliente):

    id_usuario = session["id_usuario"]

    restaurar_cliente_service(id_cliente, id_usuario)

    flash("♻️ Cliente restaurado correctamente.", "success")

    return redirect(request.referrer or url_for("clientes.clientes"))



@clientes_bp.route("/clientes/<int:id_cliente>/historial")
def historial_cliente(id_cliente):
    return jsonify(obtener_historial_cliente_service(id_cliente))



@clientes_bp.route("/api/clientes")
def api_clientes():
    q = request.args.get("q", "")
    return jsonify(buscar_clientes_service(q))


@clientes_bp.route("/clientes/<int:id_cliente>")
def ver_cliente(id_cliente):
    filtros = request.args
    data = obtener_cliente_detalle_service(id_cliente, filtros)
    return render_template("cliente_perfil.html", **data)


@clientes_bp.route("/api/clientes/crear", methods=["POST"])
def api_crear_cliente():
    id_usuario = session["id_usuario"]
    cliente = guardar_cliente_service(request.form, id_usuario, api=True)
    return jsonify(cliente)


@clientes_bp.route("/clientes/<int:id_cliente>/exportar")
def exportar_cliente_excel(id_cliente):
    import io
    from datetime import datetime
    from flask import send_file
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from ventas import obtener_ventas_cliente, obtener_detalles_venta
    from pagos import obtener_pagos_por_venta
    from clientes import obtener_cliente_por_id

    id_negocio   = request.args.get("id_negocio")  or None
    fecha_inicio = request.args.get("fecha_inicio") or None
    fecha_fin    = request.args.get("fecha_fin")    or None

    cliente = obtener_cliente_por_id(id_cliente)
    pedidos = obtener_ventas_cliente(
        id_cliente, id_negocio, fecha_inicio, fecha_fin,
        limit=99999, offset=0
    )

    ids_venta    = [p["id_venta"] for p in pedidos]
    detalles_map = obtener_detalles_venta(ids_venta)
    pagos_map    = {p["id_venta"]: obtener_pagos_por_venta(p["id_venta"]) for p in pedidos}

    C = {
        "azul":       "1E7FD6", "azul_cl":   "E6F3FF",
        "blanco":     "FFFFFF", "gris":      "F8FBFF",
        "verde":      "22C55E", "verde_cl":  "DCFCE7",
        "amarillo":   "F59E0B", "amarillo_cl":"FEF9C3",
        "rojo":       "E53935", "rojo_cl":   "FEE2E2",
        "gris_txt":   "6B7280", "dark":      "1F2937",
    }
    borde = Border(
        left=Side(style="thin", color="CFD8E3"),
        right=Side(style="thin", color="CFD8E3"),
        top=Side(style="thin", color="CFD8E3"),
        bottom=Side(style="thin", color="CFD8E3"),
    )

    def cell(ws, r, col, value="", bold=False, fg=None, color=None,
             align="left", num_fmt=None, italic=False, size=9, wrap=False):
        c = ws.cell(row=r, column=col, value=value)
        c.font      = Font(bold=bold, italic=italic, color=color or C["dark"], name="Arial", size=size)
        if fg: c.fill = PatternFill("solid", fgColor=fg)
        c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=wrap)
        c.border    = borde
        if num_fmt: c.number_format = num_fmt
        return c

    def head(ws, r, col, value):
        c = cell(ws, r, col, value, bold=True, fg=C["azul"], color=C["blanco"], align="center")
        return c

    def row_bg(i): return C["gris"] if i % 2 == 0 else C["blanco"]

    def titulo_hoja(ws, texto, ncols, subtexto=""):
        ws.merge_cells(f"A1:{get_column_letter(ncols)}1")
        c = ws["A1"]
        c.value     = texto
        c.font      = Font(bold=True, color=C["blanco"], name="Arial", size=13)
        c.fill      = PatternFill("solid", fgColor=C["azul"])
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 30
        ws.merge_cells(f"A2:{get_column_letter(ncols)}2")
        s = ws["A2"]
        s.value     = subtexto
        s.font      = Font(italic=True, color=C["gris_txt"], name="Arial", size=9)
        s.fill      = PatternFill("solid", fgColor=C["azul_cl"])
        s.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[2].height = 16

    def fmt_dt(dt):
        return dt.strftime("%d/%m/%Y %H:%M") if dt else "—"

    def estado_str(p):
        if p.get("fecha_entrega"): return "Entregada"
        if p.get("fecha_lista"):   return "Lista"
        return "Pendiente"

    COLOR_E    = {"Entregada": C["verde"],    "Lista": C["amarillo"],    "Pendiente": C["rojo"]}
    COLOR_E_CL = {"Entregada": C["verde_cl"], "Lista": C["amarillo_cl"], "Pendiente": C["rojo_cl"]}

    nombre_cliente = f"{cliente['nombre']} {cliente['apellido']}"
    filtro_txt = "  ".join(filter(None, [
        f"Desde: {fecha_inicio}" if fecha_inicio else "",
        f"Hasta: {fecha_fin}"   if fecha_fin    else "",
    ])) or "Sin filtros de fecha"

    wb = Workbook()


    ws1 = wb.active
    ws1.title = "Resumen pedidos"
    ws1.freeze_panes = "A4"

    COLS1 = ["# Recibo", "Negocio", "Fecha recibo", "Fecha estimada",
             "Fecha lista", "Fecha entrega", "Total ($)", "Cobrado ($)",
             "Saldo ($)", "Estado"]
    titulo_hoja(ws1, f"Historial de pedidos — {nombre_cliente}", len(COLS1), filtro_txt)
    for ci, h in enumerate(COLS1, 1): head(ws1, 3, ci, h)
    ws1.row_dimensions[3].height = 22

    for i, p in enumerate(pedidos):
        r       = i + 4
        bg      = row_bg(i)
        estado  = estado_str(p)
        total   = float(p.get("total") or 0)
        pagos   = pagos_map.get(p["id_venta"], [])
        cobrado = sum(float(pg["monto"]) for pg in pagos)
        saldo   = max(total - cobrado, 0)

        cell(ws1, r, 1,  f"#{p['id_venta']}", fg=bg, bold=True, align="center")
        cell(ws1, r, 2,  p.get("negocio", ""), fg=bg)
        cell(ws1, r, 3,  fmt_dt(p.get("fecha_recibo")), fg=bg)
        cell(ws1, r, 4,  fmt_dt(p.get("fecha_estimada")), fg=bg)
        cell(ws1, r, 5,  fmt_dt(p.get("fecha_lista")), fg=bg)
        cell(ws1, r, 6,  fmt_dt(p.get("fecha_entrega")), fg=bg)
        cell(ws1, r, 7,  total,   fg=bg, bold=True, align="right", num_fmt='"$"#,##0.00')
        cell(ws1, r, 8,  cobrado, fg=bg, bold=True, align="right", num_fmt='"$"#,##0.00')
        cell(ws1, r, 9,  saldo,   fg=bg, bold=True, align="right", num_fmt='"$"#,##0.00',
             color=C["rojo"] if saldo > 0 else C["verde"])
        ce = ws1.cell(row=r, column=10, value=estado)
        ce.font      = Font(bold=True, color=COLOR_E[estado], name="Arial", size=9)
        ce.fill      = PatternFill("solid", fgColor=COLOR_E_CL[estado])
        ce.alignment = Alignment(horizontal="center", vertical="center")
        ce.border    = borde
        ws1.row_dimensions[r].height = 16

    if pedidos:
        tr = len(pedidos) + 4
        ws1.merge_cells(f"A{tr}:{get_column_letter(6)}{tr}")
        ct = ws1.cell(row=tr, column=1, value="TOTALES")
        ct.font      = Font(bold=True, color=C["blanco"], name="Arial", size=10)
        ct.fill      = PatternFill("solid", fgColor=C["azul"])
        ct.alignment = Alignment(horizontal="right", vertical="center")
        ct.border    = borde
        fd, ld = 4, len(pedidos) + 3
        for col in [7, 8, 9]:
            L  = get_column_letter(col)
            tc = ws1.cell(row=tr, column=col, value=f"=SUM({L}{fd}:{L}{ld})")
            tc.font         = Font(bold=True, color=C["blanco"], name="Arial", size=10)
            tc.fill         = PatternFill("solid", fgColor=C["azul"])
            tc.alignment    = Alignment(horizontal="right", vertical="center")
            tc.number_format = '"$"#,##0.00'
            tc.border        = borde
        ws1.cell(row=tr, column=10).fill  = PatternFill("solid", fgColor=C["azul"])
        ws1.cell(row=tr, column=10).border = borde
        ws1.row_dimensions[tr].height = 20

    for ci, w in enumerate([10, 18, 20, 20, 18, 18, 13, 13, 13, 13], 1):
        ws1.column_dimensions[get_column_letter(ci)].width = w


    ws2 = wb.create_sheet("Artículos")
    ws2.freeze_panes = "A4"

    COLS2 = ["# Recibo", "Negocio", "Tipo artículo", "Descripción",
             "Material / Notas", "Cantidad", "Servicio", "Precio ($)", "Comentario"]
    titulo_hoja(ws2, f"Artículos — {nombre_cliente}", len(COLS2), filtro_txt)
    for ci, h in enumerate(COLS2, 1): head(ws2, 3, ci, h)
    ws2.row_dimensions[3].height = 22

    r2 = 4
    for p in pedidos:
        detalles = detalles_map.get(p["id_venta"], [])
        if not detalles:
            bg = row_bg(r2)
            cell(ws2, r2, 1, f"#{p['id_venta']}", fg=bg, bold=True, align="center")
            cell(ws2, r2, 2, p.get("negocio", ""), fg=bg)
            for ci in range(3, 10):
                cell(ws2, r2, ci, "—", fg=bg, color=C["gris_txt"], align="center")
            ws2.row_dimensions[r2].height = 15
            r2 += 1
            continue

        for det in detalles:
            tipo      = det.get("tipo_articulo", "")
            datos     = det.get("datos") or {}
            coment    = det.get("comentario") or ""
            servicios = det.get("servicios", [])

            if tipo == "calzado":
                desc = f"{datos.get('tipo','')} {datos.get('marca','')}".strip()
                mat  = f"Color: {datos.get('color_base','—')}  Material: {datos.get('material','—')}"
                cant = 1
            elif tipo == "confeccion":
                desc = f"{datos.get('tipo','')} {datos.get('marca','')}".strip()
                mat  = f"Material: {datos.get('material','—')}"
                cant = datos.get("cantidad", 1)
            elif tipo == "maquila":
                desc = datos.get("tipo", "—")
                mat  = f"Precio unitario: ${float(datos.get('precio_unitario') or 0):.2f}"
                cant = datos.get("cantidad", 1)
            else:
                desc, mat, cant = "—", "—", "—"

            rows = servicios if servicios else [None]
            for si, svc in enumerate(rows):
                bg = row_bg(r2)
                cell(ws2, r2, 1, f"#{p['id_venta']}" if si == 0 else "", fg=bg, bold=si==0, align="center")
                cell(ws2, r2, 2, p.get("negocio","") if si == 0 else "", fg=bg)
                cell(ws2, r2, 3, tipo.capitalize() if si == 0 else "", fg=bg, align="center")
                cell(ws2, r2, 4, desc if si == 0 else "", fg=bg)
                cell(ws2, r2, 5, mat  if si == 0 else "", fg=bg, wrap=True)
                cell(ws2, r2, 6, cant if si == 0 else "", fg=bg, align="center")
                cell(ws2, r2, 7, svc.get("nombre","") if svc else "—", fg=bg)
                cell(ws2, r2, 8,
                     float(svc.get("precio_aplicado") or 0) if svc else "—",
                     fg=bg, align="right",
                     num_fmt='"$"#,##0.00' if svc else None)
                cell(ws2, r2, 9, coment if si == 0 else "", fg=bg, wrap=True, italic=bool(coment))
                ws2.row_dimensions[r2].height = 15
                r2 += 1

    for ci, w in enumerate([10, 18, 14, 24, 28, 10, 24, 13, 24], 1):
        ws2.column_dimensions[get_column_letter(ci)].width = w


    ws3 = wb.create_sheet("Pagos")
    ws3.freeze_panes = "A4"

    COLS3 = ["# Recibo", "Negocio", "Tipo pago", "Método", "Monto ($)", "Total venta ($)"]
    titulo_hoja(ws3, f"Pagos — {nombre_cliente}", len(COLS3), filtro_txt)
    for ci, h in enumerate(COLS3, 1): head(ws3, 3, ci, h)
    ws3.row_dimensions[3].height = 22

    r3 = 4
    for p in pedidos:
        pagos = pagos_map.get(p["id_venta"], [])
        total = float(p.get("total") or 0)
        if not pagos:
            bg = row_bg(r3)
            cell(ws3, r3, 1, f"#{p['id_venta']}", fg=bg, bold=True, align="center")
            cell(ws3, r3, 2, p.get("negocio",""), fg=bg)
            cell(ws3, r3, 3, "Sin pagos", fg=bg, color=C["gris_txt"], italic=True)
            cell(ws3, r3, 4, "—", fg=bg, align="center")
            cell(ws3, r3, 5, "—", fg=bg, align="center")
            cell(ws3, r3, 6, total, fg=bg, align="right", num_fmt='"$"#,##0.00')
            ws3.row_dimensions[r3].height = 15
            r3 += 1
            continue

        for pi, pg in enumerate(pagos):
            bg = row_bg(r3)
            cell(ws3, r3, 1, f"#{p['id_venta']}" if pi == 0 else "", fg=bg, bold=pi==0, align="center")
            cell(ws3, r3, 2, p.get("negocio","") if pi == 0 else "", fg=bg)
            cell(ws3, r3, 3, (pg.get("tipo_pago_venta") or "—").capitalize(), fg=bg)
            cell(ws3, r3, 4, (pg.get("tipo_pago") or "—").capitalize(), fg=bg)
            cell(ws3, r3, 5, float(pg.get("monto") or 0),
                 fg=bg, bold=True, align="right",
                 color=C["verde"], num_fmt='"$"#,##0.00')
            cell(ws3, r3, 6, total if pi == 0 else "", fg=bg,
                 align="right", num_fmt='"$"#,##0.00')
            ws3.row_dimensions[r3].height = 15
            r3 += 1

    for ci, w in enumerate([10, 18, 16, 16, 14, 14], 1):
        ws3.column_dimensions[get_column_letter(ci)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    nombre_archivo = f"pedidos_{cliente['nombre']}_{cliente['apellido']}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    nombre_archivo = nombre_archivo.replace(" ", "_")

    return send_file(
        buf,
        as_attachment=True,
        download_name=nombre_archivo,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@clientes_bp.route("/clientes/exportar")
def exportar_clientes_excel():
    import io
    from datetime import datetime
    from flask import send_file
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from clientes import obtener_clientes

    incluir_eliminados = request.args.get("eliminados") == "1"

    clientes = obtener_clientes(limit=99999, offset=0,
                                incluir_eliminados=True)

    C = {
        "azul":    "1E7FD6", "azul_cl": "E6F3FF",
        "blanco":  "FFFFFF", "gris":    "F8FBFF",
        "verde":   "22C55E", "verde_cl":"DCFCE7",
        "rojo":    "E53935", "rojo_cl": "FEE2E2",
        "gris_txt":"6B7280", "dark":    "1F2937",
    }
    borde = Border(
        left=Side(style="thin", color="CFD8E3"),
        right=Side(style="thin", color="CFD8E3"),
        top=Side(style="thin", color="CFD8E3"),
        bottom=Side(style="thin", color="CFD8E3"),
    )

    def cell(ws, r, col, value="", bold=False, fg=None, color=None,
             align="left", num_fmt=None, size=9):
        c = ws.cell(row=r, column=col, value=value)
        c.font      = Font(bold=bold, color=color or C["dark"], name="Arial", size=size)
        if fg: c.fill = PatternFill("solid", fgColor=fg)
        c.alignment = Alignment(horizontal=align, vertical="center")
        c.border    = borde
        if num_fmt: c.number_format = num_fmt
        return c

    def head(ws, r, col, value):
        return cell(ws, r, col, value, bold=True, fg=C["azul"],
                    color=C["blanco"], align="center")

    def row_bg(i): return C["gris"] if i % 2 == 0 else C["blanco"]

    wb = Workbook()
    ws = wb.active
    ws.title = "Clientes"
    ws.freeze_panes = "A4"

    NCOLS = 6
    ws.merge_cells(f"A1:{get_column_letter(NCOLS)}1")
    t = ws["A1"]
    t.value     = "Clientes — Fresh Steps"
    t.font      = Font(bold=True, color=C["blanco"], name="Arial", size=13)
    t.fill      = PatternFill("solid", fgColor=C["azul"])
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    ws.merge_cells(f"A2:{get_column_letter(NCOLS)}2")
    s = ws["A2"]
    s.value     = "Incluye eliminados" if incluir_eliminados else "Solo clientes activos"
    s.font      = Font(italic=True, color=C["gris_txt"], name="Arial", size=9)
    s.fill      = PatternFill("solid", fgColor=C["azul_cl"])
    s.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[2].height = 16

    HEADERS = ["Nombre", "Apellido", "Teléfono", "Correo", "Dirección", "Estado"]
    for ci, h in enumerate(HEADERS, 1): head(ws, 3, ci, h)
    ws.row_dimensions[3].height = 22

    for i, cl in enumerate(clientes):
        r  = i + 4
        bg = row_bg(i)
        cell(ws, r, 1, cl.get("nombre", ""),    fg=bg, bold=True)
        cell(ws, r, 2, cl.get("apellido", ""),  fg=bg, bold=True)
        cell(ws, r, 3, cl.get("telefono", "—"), fg=bg)
        cell(ws, r, 4, cl.get("correo", "—"),   fg=bg)
        cell(ws, r, 5, cl.get("direccion", "—"),fg=bg)
        activo = 1 if cl.get("activo", 1) else 0
        ce = ws.cell(row=r, column=6, value=activo)
        ce.font      = Font(bold=True, color=C["verde"] if activo else C["rojo"],
                            name="Arial", size=9)
        ce.fill      = PatternFill("solid", fgColor=C["verde_cl"] if activo else C["rojo_cl"])
        ce.alignment = Alignment(horizontal="center", vertical="center")
        ce.border    = borde
        ws.row_dimensions[r].height = 16

    for ci, w in enumerate([20, 20, 14, 28, 30, 11], 1):
        ws.column_dimensions[get_column_letter(ci)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    nombre = f"clientes_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(buf, as_attachment=True, download_name=nombre,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")