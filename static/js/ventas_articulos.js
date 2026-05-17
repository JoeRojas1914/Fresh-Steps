/* ─── Tipo de artículo por negocio ───────────────────────────────────────── */

function obtenerTipoArticuloPorNegocio(idNegocio) {
    if (idNegocio === "1") return "calzado";
    if (idNegocio === "2") return "confeccion";
    if (idNegocio === "3") return "maquila";
    return "";
}

/* ─── Helpers de HTML ────────────────────────────────────────────────────── */

function inputConLabel(label, name, placeholder = "", required = false, type = "text", extra = "") {
    return `
        <div class="campo-item">
            <label class="form-label">${label}</label>
            <input
                type="${type}"
                name="${name}"
                placeholder="${placeholder}"
                ${required ? "required" : ""}
                ${extra}
                oninput="validarFormulario(); actualizarTotal(); validarArticuloVisual(this.closest('.articulo-item'))"
            >
        </div>
    `;
}

function crearCamposArticulo(index, tipoArticulo) {
    if (tipoArticulo === "calzado") {
        return `
            <div class="form-group form-row articulo-row">
                ${inputConLabel("Tipo",                           `articulos[${index}][tipo]`,             "Tenis, Bota...",    true)}
                ${inputConLabel("Marca",                          `articulos[${index}][marca]`,            "Nike, Puma...",     true)}
                ${inputConLabel("Material",                       `articulos[${index}][material]`,         "Gamuza, Piel...",   true)}
                ${inputConLabel("Color base",                     `articulos[${index}][color_base]`,       "Negro, Blanco...",  true)}
                ${inputConLabel("Color secundario (Opcional)",    `articulos[${index}][color_secundario]`, "Negro, Blanco...",  false)}
                ${inputConLabel("Color agujetas (Opcional)",      `articulos[${index}][color_agujetas]`,   "Negro, Blanco...",  false)}
            </div>
            ${crearServiciosSelect(index)}
            ${inputConLabel("Comentario", `articulos[${index}][comentario]`, "(opcional)", false)}
        `;
    }

    if (tipoArticulo === "confeccion") {
        return `
            <div class="form-group form-row articulo-row">
                ${inputConLabel("Tipo",                        `articulos[${index}][tipo]`,             "Pantalón, Falda...",    true)}
                ${inputConLabel("Marca",                       `articulos[${index}][marca]`,            "Zara, Levis...",        true)}
                ${inputConLabel("Material",                    `articulos[${index}][material]`,         "Mezclilla, Gamuza...", true)}
                ${inputConLabel("Color base",                  `articulos[${index}][color_base]`,       "Negro, Blanco...",      true)}
                ${inputConLabel("Color secundario (Opcional)", `articulos[${index}][color_secundario]`, "Negro, Blanco...",      false)}
                ${inputConLabel("Cantidad",                    `articulos[${index}][cantidad]`,         "1,2...",                true, "number", `min="1"`)}
            </div>
            ${crearServiciosSelect(index)}
            ${inputConLabel("Comentario", `articulos[${index}][comentario]`, "(opcional)", false)}
        `;
    }

    return `
        <div class="form-group form-row articulo-row">
            ${inputConLabel("Tipo",            `articulos[${index}][tipo]`,           "Mandil, Bata...", true)}
            ${inputConLabel("Cantidad",        `articulos[${index}][cantidad]`,       "1,2...",          true, "number", `min="1"`)}
            ${inputConLabel("Precio unitario", `articulos[${index}][precio_unitario]`,"$10.00",          true, "number", `min="0"`)}
        </div>
        ${inputConLabel("Comentario", `articulos[${index}][comentario]`, "(opcional)", false)}
    `;
}

/* ─── CRUD de artículos ──────────────────────────────────────────────────── */

function agregarArticulo() {
    const idNegocio = document.getElementById("id_negocio").value;
    if (!idNegocio) {
        mostrarFeedback("Primero selecciona un negocio.", "error");
        return;
    }

    const index        = ventaState.contadorArticulos;
    const tipoArticulo = obtenerTipoArticuloPorNegocio(idNegocio);
    const negNombre    = document.getElementById("id_negocio")?.selectedOptions[0]?.text || "";

    const div       = document.createElement("div");
    div.className   = "articulo-item";
    div.innerHTML   = `
        <div class="articulo-resumen"></div>
        <div class="articulo-detalle">
            <div class="zapato-header">
                <div class="zapato-titulo">
                    <i data-lucide="receipt" width="14" height="14"></i> Artículo ${index + 1}${negNombre ? `<span class="zapato-titulo-badge">${negNombre}</span>` : ""}
                </div>
                <button type="button" class="btn btn--danger btn--sm" onclick="eliminarArticulo(this)">
                    <i data-lucide="x" width="14" height="14"></i>
                </button>
            </div>
            <input type="hidden" name="articulos[${index}][tipo_articulo]" value="${tipoArticulo}">
            ${crearCamposArticulo(index, tipoArticulo)}
        </div>
    `;

    document.getElementById("articulosContainer").appendChild(div);
    actualizarEmptyState();
    if (window.lucide) lucide.createIcons();

    div.querySelector(".articulo-resumen").addEventListener("click", function () {
        abrirArticuloDesdeResumen(this);
    });

    ventaState.contadorArticulos++;

    document.querySelectorAll(".articulo-item.abierto").forEach(a => cerrarArticulo(a));
    div.classList.add("abierto");

    const detalle = div.querySelector(".articulo-detalle");
    const resumen = div.querySelector(".articulo-resumen");
    if (detalle) detalle.style.display = "block";
    if (resumen) resumen.style.display = "none";

    actualizarOpcionesServiciosDelArticulo(index);
    validarArticuloVisual(div);
    validarFormulario();
    actualizarTotal();
}

function eliminarArticulo(btn) {
    btn.closest(".articulo-item").remove();
    renumerarArticulos();
    actualizarEmptyState();
    validarFormulario();
    actualizarTotal();
}

function renumerarArticulos() {
    document.querySelectorAll(".articulo-item").forEach((item, i) => {
        item.querySelector(".zapato-titulo").innerHTML =
            `<i data-lucide="receipt" width="14" height="14"></i> Artículo ${i + 1}`;
    });
    ventaState.contadorArticulos = document.querySelectorAll(".articulo-item").length;

    if (ventaState.contadorArticulos === 0) {
        document.getElementById("errorNegocio").style.display = "none";
    }
}

function actualizarEmptyState() {
    const empty = document.getElementById("emptyArticulos");
    if (!empty) return;

    if (document.querySelectorAll(".articulo-item").length) {
        empty.style.display = "none";
        return;
    }

    empty.style.display = "flex";
    const msg  = document.getElementById("emptyArticulosMsg");
    const icon = document.getElementById("emptyArticulosIcon");

    if (ventaState.negocioSeleccionado) {
        if (msg)  msg.textContent = "Agrega el primer artículo para comenzar";
        if (icon) icon.setAttribute("data-lucide", "package");
    } else {
        if (msg)  msg.textContent = "Selecciona un negocio para comenzar";
        if (icon) icon.setAttribute("data-lucide", "store");
    }
    if (window.lucide) lucide.createIcons();
}

/* ─── Accordion (abrir/cerrar/toggle) ───────────────────────────────────── */

function toggleArticulo(btn) {
    const item    = btn.closest(".articulo-item");
    const detalle = item.querySelector(".articulo-detalle");
    const resumen = item.querySelector(".articulo-resumen");
    const abierto = detalle.style.display !== "none";

    if (abierto) {
        generarResumenArticulo(item);
        detalle.style.display = "none";
        resumen.style.display = "block";
        btn.innerText = "Editar";
        item.classList.remove("abierto");
    } else {
        document.querySelectorAll(".articulo-item.abierto").forEach(a => {
            if (a !== item) cerrarArticulo(a);
        });
        detalle.style.display = "block";
        resumen.style.display = "none";
        btn.innerText = "Minimizar";
        item.classList.add("abierto");
    }
}

function cerrarArticulo(item) {
    const detalle = item.querySelector(".articulo-detalle");
    const resumen = item.querySelector(".articulo-resumen");

    generarResumenArticulo(item);
    detalle.style.display = "none";
    resumen.style.display = "block";
    if (window.lucide) lucide.createIcons();

    item.classList.remove("abierto");
    validarArticuloVisual(item);
}

function abrirArticuloDesdeResumen(resumenDiv) {
    const item = resumenDiv.closest(".articulo-item");

    document.querySelectorAll(".articulo-item.abierto").forEach(a => {
        if (a !== item) cerrarArticulo(a);
    });

    item.querySelector(".articulo-detalle").style.display = "block";
    item.querySelector(".articulo-resumen").style.display = "none";
    item.classList.add("abierto");
}

/* ─── Resumen y validación visual ───────────────────────────────────────── */

function calcularTotalArticulo(item) {
    const negocio = document.getElementById("id_negocio").value;
    let total = 0;

    if (negocio === "1") {
        item.querySelectorAll(".servicio-item").forEach(fila => {
            const sel    = fila.querySelector("select");
            const precio = fila.querySelector(".precio-aplicado");
            if (sel && sel.value) total += parseFloat(precio?.value || 0);
        });
    }

    if (negocio === "2") {
        const cantidad = parseFloat(
            item.querySelector("input[name$='[cantidad]']")?.value || 1
        );
        item.querySelectorAll(".servicio-item").forEach(fila => {
            const sel    = fila.querySelector("select");
            const precio = fila.querySelector(".precio-aplicado");
            if (sel && sel.value) total += cantidad * parseFloat(precio?.value || 0);
        });
    }

    if (negocio === "3") {
        const cantidad = parseFloat(item.querySelector("input[name$='[cantidad]']")?.value || 0);
        const precio   = parseFloat(item.querySelector("input[name$='[precio_unitario]']")?.value || 0);
        total = cantidad * precio;
    }

    return total;
}

function generarResumenArticulo(item) {
    const resumen = item.querySelector(".articulo-resumen");

    const tipo   = item.querySelector("input[name$='[tipo]']")?.value       || "";
    const marca  = item.querySelector("input[name$='[marca]']")?.value      || "";
    const color  = item.querySelector("input[name$='[color_base]']")?.value || "";
    const mat    = item.querySelector("input[name$='[material]']")?.value   || "";
    const cant   = item.querySelector("input[name$='[cantidad]']")?.value   || "";
    const precio = calcularTotalArticulo(item);

    const svcs = [...item.querySelectorAll(".servicio-item select")]
        .filter(s => s.value)
        .map(s => s.selectedOptions[0]?.text.split(" ($")[0] || "")
        .join(", ");

    const partes = [color, mat, cant ? `x${cant}` : ""].filter(Boolean);
    const detalle = partes.join(" · ");

    const negNombre = document.getElementById("id_negocio")?.selectedOptions[0]?.text || "";
    const titulo    = item.querySelector(".zapato-titulo")?.innerText || "Artículo";
    const btnEl     = item.querySelector(".btn--danger")?.outerHTML   || "";

    resumen.innerHTML = `
        <div class="resumen-header-bar">
            <span class="resumen-header-label">${titulo}</span>
            <div class="resumen-header-actions">
                <span class="resumen-header-badge">${negNombre}</span>
                ${btnEl}
            </div>
        </div>
        <div class="resumen-body">
            <div class="resumen-linea">
                <div>
                    <div class="resumen-nombre">${tipo} ${marca}</div>
                    ${detalle ? `<div class="resumen-detalle">${detalle}</div>` : ""}
                    ${svcs    ? `<div class="resumen-detalle resumen-svcs"><i data-lucide="wrench" width="12" height="12"></i> ${svcs}</div>` : ""}
                </div>
                <div class="resumen-precio">$${precio.toFixed(2)}</div>
            </div>
            <div class="resumen-hint"><i data-lucide="pencil" width="11" height="11"></i> Toca para editar</div>
        </div>
    `;
}

function articuloCompleto(item) {
    const negocio = document.getElementById("id_negocio").value;

    for (const c of item.querySelectorAll("input[required], select[required]")) {
        if (!c.value || c.value.trim() === "") return false;
    }

    if (negocio === "1" || negocio === "2") {
        let seleccionados = 0;
        let hayVacio      = false;
        item.querySelectorAll(".servicio-item select").forEach(sel => {
            if (sel.value && sel.value.trim() !== "") seleccionados++;
            else hayVacio = true;
        });
        if (seleccionados === 0 || hayVacio) return false;
    }

    return true;
}

function validarArticuloVisual(item) {
    if (!item) return;
    item.classList.remove("completo", "incompleto");
    item.classList.add(articuloCompleto(item) ? "completo" : "incompleto");
}
