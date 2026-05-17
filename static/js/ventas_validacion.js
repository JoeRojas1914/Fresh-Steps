/* ─── Fecha ─────────────────────────────────────────────────────────────── */

function bloquearFechaMinima() {
    const input = document.getElementById("fecha_estimada_fecha");
    const hoy = new Date();
    const yyyy = hoy.getFullYear();
    const mm = String(hoy.getMonth() + 1).padStart(2, "0");
    const dd = String(hoy.getDate()).padStart(2, "0");
    input.min = `${yyyy}-${mm}-${dd}`;
}

function actualizarFechaEstimadaCompleta() {
    const fecha = document.getElementById("fecha_estimada_fecha").value;
    const hora  = document.getElementById("fecha_estimada_hora").value;
    document.getElementById("fecha_estimada").value =
        (fecha && hora) ? `${fecha} ${hora}:00` : "";
}

/* ─── Prepago / Descuento ────────────────────────────────────────────────── */

function togglePrepago() {
    const checked = document.getElementById("togglePrepago").checked;
    document.getElementById("prepago").value = checked ? "si" : "no";
    const fields = document.getElementById("prepago-fields");
    fields.classList.toggle("visible", checked);
    if (checked) {
        setTimeout(() => fields.scrollIntoView({ behavior: "smooth", block: "nearest" }), 50);
    } else {
        document.getElementById("monto_prepago").value = "";
        document.getElementById("tipo_pago").value = "";
        document.getElementById("errorPrepago").style.display = "none";
    }
}

function toggleDescuento() {
    const checked = document.getElementById("toggleDescuento").checked;
    document.getElementById("aplica_descuento").value = checked ? "si" : "no";
    const fields = document.getElementById("descuento-fields");
    fields.classList.toggle("visible", checked);
    if (checked) {
        setTimeout(() => fields.scrollIntoView({ behavior: "smooth", block: "nearest" }), 50);
    } else {
        document.getElementById("cantidad_descuento").value = "";
    }
    validarFormulario();
    actualizarTotal();
}

/* ─── Cálculo de totales ─────────────────────────────────────────────────── */

function calcularTotal(bruto = false) {
    const negocio = document.getElementById("id_negocio").value;
    let total = 0;

    if (negocio === "1") {
        document.querySelectorAll(".servicio-item").forEach(fila => {
            const sel    = fila.querySelector("select");
            const precio = fila.querySelector(".precio-aplicado");
            if (sel && sel.value) total += parseFloat(precio?.value || 0);
        });
    }

    if (negocio === "2") {
        document.querySelectorAll(".articulo-item").forEach(articulo => {
            const cantidad = parseFloat(
                articulo.querySelector("input[name$='[cantidad]']")?.value || 1
            );
            articulo.querySelectorAll(".servicio-item").forEach(fila => {
                const sel    = fila.querySelector("select");
                const precio = fila.querySelector(".precio-aplicado");
                if (sel && sel.value) total += cantidad * parseFloat(precio?.value || 0);
            });
        });
    }

    if (negocio === "3") {
        document.querySelectorAll(".articulo-item").forEach(item => {
            const cantidad = parseFloat(
                item.querySelector("input[name$='[cantidad]']")?.value || 0
            );
            const precio = parseFloat(
                item.querySelector("input[name$='[precio_unitario]']")?.value || 0
            );
            total += cantidad * precio;
        });
    }

    if (bruto) return total;

    const aplicaDesc = document.getElementById("aplica_descuento").value === "si";
    const desc = parseFloat(document.getElementById("cantidad_descuento")?.value || 0);
    if (aplicaDesc && desc > 0) total = Math.max(0, total - desc);

    return total;
}

function actualizarTotal() {
    const total = calcularTotal();
    document.getElementById("totalVenta").innerText =
        `Total: $${total.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/* ─── Validación ─────────────────────────────────────────────────────────── */

function articulosCompletos() {
    const articulos = document.querySelectorAll(".articulo-item");
    if (articulos.length === 0) return false;

    const negocio = document.getElementById("id_negocio").value;

    for (const art of articulos) {
        for (const campo of art.querySelectorAll("input, select, textarea")) {
            if (campo.offsetParent === null) continue;
            const name = campo.name || "";
            if (negocio === "1" && (name.includes("[color_secundario]") || name.includes("[color_agujetas]"))) continue;
            if (negocio === "2" && name.includes("[color_secundario]")) continue;
            if (campo.hasAttribute("required") && (!campo.value || campo.value.trim() === "")) return false;
        }
    }
    return true;
}

function obtenerMotivosBloqueo() {
    const motivos = [];

    if (!document.getElementById("id_cliente").value)    motivos.push("Seleccionar un cliente");
    if (!document.getElementById("id_negocio").value)    motivos.push("Eligir un negocio");
    if (!document.getElementById("fecha_estimada").value) motivos.push("Definir fecha y hora");

    const articulos = document.querySelectorAll(".articulo-item");
    if (articulos.length === 0) {
        motivos.push("Agregar al menos un artículo");
    } else if (!articulosCompletos()) {
        motivos.push("Completar los datos de los artículos");
    }

    const prepago = document.getElementById("prepago").value;
    if (prepago === "si") {
        const tipoPago = document.getElementById("tipo_pago").value;
        const monto    = parseFloat(document.getElementById("monto_prepago").value || 0);
        if (!tipoPago) motivos.push("Seleccionar el tipo de pago");
        if (monto <= 0) motivos.push("Ingresar un monto de prepago válido");
        if (monto > calcularTotal()) motivos.push("El prepago supera el total");
    }

    const aplicaDesc = document.getElementById("aplica_descuento").value === "si";
    if (aplicaDesc) {
        const desc       = parseFloat(document.getElementById("cantidad_descuento").value || 0);
        const totalBruto = calcularTotal(true);
        if (desc <= 0)          motivos.push("El descuento debe ser mayor a 0");
        else if (desc > totalBruto) motivos.push("El descuento supera el total");
    }

    return motivos;
}

function validarFormulario() {
    const negocio      = document.getElementById("id_negocio").value;
    const fechaEstimada = document.getElementById("fecha_estimada").value;
    const prepago      = document.getElementById("prepago").value;
    const tipoPago     = document.getElementById("tipo_pago").value;
    const montoPrepago = parseFloat(document.getElementById("monto_prepago")?.value || 0);
    const aplicaDesc   = document.getElementById("aplica_descuento").value === "si";
    const descuento    = parseFloat(document.getElementById("cantidad_descuento")?.value || 0);

    let valido = !!(negocio && fechaEstimada);

    if (document.querySelectorAll(".articulo-item").length === 0 || !articulosCompletos()) valido = false;

    if (negocio === "1" || negocio === "2") {
        document.querySelectorAll(".servicios-box").forEach(box => {
            let cantidadSeleccionados = 0;
            let hayVacio = false;
            box.querySelectorAll("select").forEach(sel => {
                if (sel.value && sel.value.trim() !== "") cantidadSeleccionados++;
                else hayVacio = true;
            });
            if (cantidadSeleccionados === 0 || hayVacio) valido = false;
        });
    }

    if (prepago === "si") {
        if (!tipoPago || montoPrepago <= 0) valido = false;
        if (montoPrepago > calcularTotal()) {
            document.getElementById("errorPrepago").style.display = "block";
            valido = false;
        } else {
            document.getElementById("errorPrepago").style.display = "none";
        }
    } else {
        document.getElementById("errorPrepago").style.display = "none";
    }

    if (aplicaDesc) {
        const totalBruto = calcularTotal(true);
        if (descuento <= 0 || descuento > totalBruto) {
            document.getElementById("errorDescuento").style.display = "block";
            valido = false;
        } else {
            document.getElementById("errorDescuento").style.display = "none";
        }
    } else {
        document.getElementById("errorDescuento").style.display = "none";
    }

    const motivos = obtenerMotivosBloqueo();
    const btn     = document.getElementById("btnCrear");
    const msg     = document.getElementById("mensajeBloqueo");

    btn.disabled = !valido || motivos.length > 0;
    if (motivos.length > 0) {
        msg.innerText      = "Falta: " + motivos.join(" · ");
        msg.style.display  = "block";
    } else {
        msg.style.display = "none";
    }
}
