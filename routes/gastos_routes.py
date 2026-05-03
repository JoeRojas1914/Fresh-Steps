from flask import Blueprint, render_template, request, redirect, flash, url_for, session, jsonify

from services.gastos_service import (
    listar_gastos,
    guardar_gasto_service,
    eliminar_gasto_service,
    obtener_historial_gasto,
    restaurar_gasto_service
)

from negocio import obtener_negocios


gastos_bp = Blueprint("gastos", __name__)


@gastos_bp.route("/gastos")
def gastos():

    id_negocio = request.args.get("id_negocio")
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")
    pagina = request.args.get("pagina", 1, type=int)
    incluir_eliminados = request.args.get("eliminados") == "1"
    tipo_comprobante = request.args.get("tipo_comprobante")


    data = listar_gastos(
        id_negocio=id_negocio,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        pagina=pagina,
        incluir_eliminados=incluir_eliminados
    )

    return render_template(
        "gastos.html",
        gastos=data["gastos"],
        negocios=obtener_negocios(),
        pagina=pagina,
        total_paginas=data["total_paginas"],
        incluir_eliminados=incluir_eliminados
    )


@gastos_bp.route("/gastos/guardar", methods=["POST"])
def guardar_gasto():

    id_gasto = request.form.get("id_gasto")

    id_usuario = session["id_usuario"]

    datos = (
        request.form["id_negocio"],
        request.form["descripcion"],
        request.form["proveedor"],
        request.form["total"],
        request.form["fecha_registro"],
        request.form["tipo_comprobante"],
        request.form["tipo_pago"]
    )


    resultado = guardar_gasto_service(id_gasto, datos, id_usuario)

    if resultado == "actualizado":
        flash("✅ Gasto editado correctamente.", "success")
    else:
        flash("✅ Gasto creado correctamente.", "success")

    return redirect(url_for("gastos.gastos"))


@gastos_bp.route("/gastos/eliminar/<int:id_gasto>")
def eliminar_gasto(id_gasto):

    id_usuario = session["id_usuario"]

    eliminar_gasto_service(id_gasto, id_usuario)

    flash("✅ Gasto eliminado correctamente.", "success")
    return redirect(url_for("gastos.gastos"))


@gastos_bp.route("/gastos/<int:id_gasto>/historial")
def historial_gasto(id_gasto):
    data = obtener_historial_gasto(id_gasto)
    return jsonify(data)


@gastos_bp.route("/gastos/restaurar/<int:id_gasto>")
def restaurar_gasto_route(id_gasto):

    id_usuario = session["id_usuario"]

    restaurar_gasto_service(id_gasto, id_usuario)

    flash("♻️ Gasto restaurado correctamente.", "success")

    return redirect(request.referrer or url_for("gastos.gastos"))


@gastos_bp.route("/gastos/exportar")
def exportar_gastos_excel():
    import io
    from datetime import datetime
    from flask import send_file
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from gastos import obtener_gastos

    id_negocio        = request.args.get("id_negocio")  or None
    fecha_inicio      = request.args.get("fecha_inicio") or None
    fecha_fin         = request.args.get("fecha_fin")    or None
    incluir_eliminados = request.args.get("eliminados") == "1"

    gastos = obtener_gastos(
        id_negocio, fecha_inicio, fecha_fin,
        limit=99999, offset=0,
        incluir_eliminados=incluir_eliminados
    )

    C = {
        "azul":     "1E7FD6", "azul_cl":  "E6F3FF",
        "blanco":   "FFFFFF", "gris":     "F8FBFF",
        "verde":    "22C55E", "verde_cl": "DCFCE7",
        "rojo":     "E53935", "rojo_cl":  "FEE2E2",
        "gris_txt": "6B7280", "dark":     "1F2937",
    }
    borde = Border(
        left=Side(style="thin", color="CFD8E3"),
        right=Side(style="thin", color="CFD8E3"),
        top=Side(style="thin", color="CFD8E3"),
        bottom=Side(style="thin", color="CFD8E3"),
    )

    def cell(ws, r, col, value="", bold=False, fg=None, color=None,
             align="left", num_fmt=None, italic=False, size=9):
        c = ws.cell(row=r, column=col, value=value)
        c.font      = Font(bold=bold, italic=italic, color=color or C["dark"], name="Arial", size=size)
        if fg: c.fill = PatternFill("solid", fgColor=fg)
        c.alignment = Alignment(horizontal=align, vertical="center")
        c.border    = borde
        if num_fmt: c.number_format = num_fmt
        return c

    def head(ws, r, col, value):
        return cell(ws, r, col, value, bold=True, fg=C["azul"], color=C["blanco"], align="center")

    def row_bg(i): return C["gris"] if i % 2 == 0 else C["blanco"]

    PAGO_LABEL = {"efectivo": "Efectivo", "transferencia": "Transferencia", "TDC": "Tarjeta de crédito"}
    COMP_LABEL = {"factura": "Factura", "ticket": "Ticket"}

    wb = Workbook()
    ws = wb.active
    ws.title = "Gastos"
    ws.freeze_panes = "A4"

    NCOLS = 9
    ws.merge_cells(f"A1:{get_column_letter(NCOLS)}1")
    t = ws["A1"]
    t.value     = "Gastos — Fresh Steps"
    t.font      = Font(bold=True, color=C["blanco"], name="Arial", size=13)
    t.fill      = PatternFill("solid", fgColor=C["azul"])
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    ws.merge_cells(f"A2:{get_column_letter(NCOLS)}2")
    subtexto = "  ".join(filter(None, [
        f"Negocio ID: {id_negocio}" if id_negocio else "",
        f"Desde: {fecha_inicio}"    if fecha_inicio else "",
        f"Hasta: {fecha_fin}"       if fecha_fin    else "",
    ])) or "Sin filtros — todos los registros"
    s = ws["A2"]
    s.value     = subtexto
    s.font      = Font(italic=True, color=C["gris_txt"], name="Arial", size=9)
    s.fill      = PatternFill("solid", fgColor=C["azul_cl"])
    s.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[2].height = 16

    HEADERS = ["Negocio", "Descripción", "Proveedor", "Total ($)",
               "Comprobante", "Método de pago", "Fecha registro", "Registrado por", "Estado"]
    for ci, h in enumerate(HEADERS, 1): head(ws, 3, ci, h)
    ws.row_dimensions[3].height = 22

    for i, g in enumerate(gastos):
        r  = i + 4
        bg = row_bg(i)
        cell(ws, r, 1, g.get("negocio", ""), fg=bg)
        cell(ws, r, 2, g.get("descripcion", ""), fg=bg)
        cell(ws, r, 3, g.get("proveedor", ""), fg=bg)
        cell(ws, r, 4, float(g.get("total") or 0), fg=bg, bold=True,
             align="right", num_fmt='"$"#,##0.00')
        cell(ws, r, 5, COMP_LABEL.get(g.get("tipo_comprobante",""), g.get("tipo_comprobante","")), fg=bg)
        cell(ws, r, 6, PAGO_LABEL.get(g.get("tipo_pago",""), g.get("tipo_pago","")), fg=bg)
        fr = g.get("fecha_registro")
        cell(ws, r, 7, fr.strftime("%d/%m/%Y") if fr else "—", fg=bg)
        cell(ws, r, 8, g.get("creado_por", "—"), fg=bg)

        activo = g.get("activo", 1)
        ce = ws.cell(row=r, column=9, value="Activo" if activo else "Eliminado")
        ce.font      = Font(bold=True, color=C["verde"] if activo else C["rojo"], name="Arial", size=9)
        ce.fill      = PatternFill("solid", fgColor=C["verde_cl"] if activo else C["rojo_cl"])
        ce.alignment = Alignment(horizontal="center", vertical="center")
        ce.border    = borde
        ws.row_dimensions[r].height = 16

    if gastos:
        tr = len(gastos) + 4
        ws.merge_cells(f"A{tr}:{get_column_letter(3)}{tr}")
        ct = ws.cell(row=tr, column=1, value="TOTAL")
        ct.font      = Font(bold=True, color=C["blanco"], name="Arial", size=10)
        ct.fill      = PatternFill("solid", fgColor=C["azul"])
        ct.alignment = Alignment(horizontal="right", vertical="center")
        ct.border    = borde
        L  = get_column_letter(4)
        tc = ws.cell(row=tr, column=4,
                     value=f"=SUM({L}4:{L}{len(gastos)+3})")
        tc.font         = Font(bold=True, color=C["blanco"], name="Arial", size=10)
        tc.fill         = PatternFill("solid", fgColor=C["azul"])
        tc.alignment    = Alignment(horizontal="right", vertical="center")
        tc.number_format = '"$"#,##0.00'
        tc.border        = borde
        for col in range(5, NCOLS + 1):
            ec = ws.cell(row=tr, column=col)
            ec.fill   = PatternFill("solid", fgColor=C["azul"])
            ec.border = borde
        ws.row_dimensions[tr].height = 20

    for ci, w in enumerate([18, 28, 22, 13, 13, 18, 16, 18, 11], 1):
        ws.column_dimensions[get_column_letter(ci)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    nombre = f"gastos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(buf, as_attachment=True, download_name=nombre,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")