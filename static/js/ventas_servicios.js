/* ─── Carga de servicios por negocio ─────────────────────────────────────── */

async function cargarServicios() {
    const idNegocio = document.getElementById("id_negocio").value;
    if (!idNegocio) { ventaState.serviciosGlobales = []; return; }
    try {
        const res = await fetch(`/api/servicios?id_negocio=${idNegocio}`);
        if (!res.ok) throw new Error("Error de red");
        ventaState.serviciosGlobales = await res.json();
    } catch {
        ventaState.serviciosGlobales = [];
    }
}

async function seleccionarNegocio() {
    const select      = document.getElementById("id_negocio");
    const nuevoNegocio = select.value;
    const hayArticulos = document.querySelectorAll(".articulo-item").length > 0;

    if (hayArticulos && ventaState.negocioSeleccionado && nuevoNegocio !== ventaState.negocioSeleccionado) {
        select.value = ventaState.negocioSeleccionado;
        document.getElementById("errorNegocio").style.display = "block";
        return;
    }

    document.getElementById("errorNegocio").style.display = "none";
    ventaState.negocioSeleccionado = nuevoNegocio;

    await cargarServicios();

    if (!hayArticulos) {
        document.querySelectorAll("#articulosContainer .articulo-item").forEach(el => el.remove());
        ventaState.contadorArticulos = 0;
        actualizarEmptyState();
        actualizarTotal();
        validarFormulario();
    }
}

/* ─── Helpers para generar HTML de servicios ─────────────────────────────── */

function _opcionesServiciosHTML() {
    let html = `<option value="">-- Selecciona servicio --</option>`;
    ventaState.serviciosGlobales.forEach(s => {
        const precio = s.precio_base ?? s.precio ?? 0;
        html += `<option value="${s.id_servicio}" data-precio="${precio}">${s.nombre} ($${precio})</option>`;
    });
    return html;
}

function crearServiciosSelect(indexArticulo) {
    return `
        <div class="form-group servicios-box" data-articulo="${indexArticulo}">
            <div class="servicios-header">
                <label class="form-label">Servicios</label>
                <button type="button" class="btn btn--info btn--sm"
                        onclick="agregarServicio(${indexArticulo})">
                    <i data-lucide="plus" width="14" height="14"></i> Agregar servicio
                </button>
            </div>
            <div class="servicios-lista" id="serviciosLista_${indexArticulo}">
                ${crearFilaServicio(indexArticulo, 0, _opcionesServiciosHTML())}
            </div>
        </div>
    `;
}

function crearFilaServicio(indexArticulo, indexServicio, opcionesHTML) {
    return `
        <div class="servicio-item" data-index-servicio="${indexServicio}">
            <select name="articulos[${indexArticulo}][servicios][${indexServicio}][id_servicio]"
                    onchange="onChangeServicio(this, ${indexArticulo}); validarFormulario(); actualizarTotal(); validarArticuloVisual(this.closest('.articulo-item'))">
                ${opcionesHTML}
            </select>
            <input type="number" min="0" step="0.01"
                   class="precio-aplicado"
                   name="articulos[${indexArticulo}][servicios][${indexServicio}][precio_aplicado]"
                   placeholder="Precio aplicado"
                   value="" disabled data-editado="0"
                   oninput="marcarPrecioEditado(this); validarFormulario(); actualizarTotal()">
            <button type="button" class="btn btn--danger btn--sm"
                    onclick="eliminarServicioPro(this, ${indexArticulo})">
                <i data-lucide="x" width="14" height="14"></i>
            </button>
        </div>
    `;
}

/* ─── CRUD de filas de servicio ──────────────────────────────────────────── */

function marcarPrecioEditado(input) {
    input.dataset.editado = "1";
}

function agregarServicio(indexArticulo) {
    const contenedor    = document.getElementById(`serviciosLista_${indexArticulo}`);
    const indexServicio = contenedor.querySelectorAll(".servicio-item").length;
    contenedor.insertAdjacentHTML("beforeend", crearFilaServicio(indexArticulo, indexServicio, _opcionesServiciosHTML()));
    if (window.lucide) lucide.createIcons();
    actualizarOpcionesServiciosDelArticulo(indexArticulo);
    validarFormulario();
    actualizarTotal();
}

function eliminarServicioPro(btn, indexArticulo) {
    const fila       = btn.closest(".servicio-item");
    const contenedor = fila.parentElement;
    fila.remove();

    if (contenedor.querySelectorAll(".servicio-item").length === 0) {
        contenedor.insertAdjacentHTML("beforeend", crearFilaServicio(indexArticulo, 0, _opcionesServiciosHTML()));
    }

    actualizarOpcionesServiciosDelArticulo(indexArticulo);
    validarFormulario();
    actualizarTotal();
}

function onChangeServicio(select, indexArticulo) {
    const fila       = select.closest(".servicio-item");
    const inputPrecio = fila.querySelector(".precio-aplicado");
    const opt        = select.selectedOptions[0];

    if (!opt || !opt.value) {
        inputPrecio.value            = "";
        inputPrecio.disabled         = true;
        inputPrecio.dataset.editado  = "0";
        actualizarOpcionesServiciosDelArticulo(indexArticulo);
        actualizarTotal();
        return;
    }

    inputPrecio.disabled = false;
    if (inputPrecio.dataset.editado !== "1") {
        inputPrecio.value = parseFloat(opt.dataset.precio || 0);
    }

    if (hayServicioRepetidoEnArticulo(indexArticulo)) {
        mostrarFeedback("No puedes repetir el mismo servicio en el mismo artículo.", "error");
        select.value                 = "";
        inputPrecio.value            = "";
        inputPrecio.disabled         = true;
        inputPrecio.dataset.editado  = "0";
    }

    actualizarOpcionesServiciosDelArticulo(indexArticulo);
    actualizarTotal();
}

function hayServicioRepetidoEnArticulo(indexArticulo) {
    const contenedor = document.getElementById(`serviciosLista_${indexArticulo}`);
    const vistos     = new Set();
    for (const sel of contenedor.querySelectorAll("select")) {
        if (sel.value) {
            if (vistos.has(sel.value)) return true;
            vistos.add(sel.value);
        }
    }
    return false;
}

function actualizarOpcionesServiciosDelArticulo(indexArticulo) {
    const contenedor = document.getElementById(`serviciosLista_${indexArticulo}`);
    if (!contenedor) return;

    const selects = contenedor.querySelectorAll("select");
    const usados  = new Set();
    selects.forEach(sel => { if (sel.value) usados.add(sel.value); });

    selects.forEach(sel => {
        const valorActual = sel.value;
        Array.from(sel.options).forEach(opt => {
            if (!opt.value) return;
            opt.disabled = usados.has(opt.value) && opt.value !== valorActual;
        });
    });
}
