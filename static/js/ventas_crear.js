if (typeof ventaState === "undefined") {
    var ventaState = {
        contadorArticulos: 0,
        serviciosGlobales: [],
        negocioSeleccionado: "",
        enProceso: false,
    };

    document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("buscarCliente").addEventListener("input", buscarClientes);

    document.getElementById("btnCambiarCliente").addEventListener("click", () => {
        document.getElementById("id_cliente").value = "";
        document.getElementById("clienteSeleccionado").innerText = "";

        document.getElementById("clienteBox").style.display = "none";

        document.getElementById("busquedaCliente").style.display = "block";

        document.getElementById("buscarCliente").value = "";
        document.getElementById("listaClientes").innerHTML = "";

        
        validarFormulario();
    });

    document.addEventListener("click", function(e){

        if(e.target.closest("#btnAgregarArticulo")) return;

        const abierto = document.querySelector(".articulo-item.abierto");
        if(!abierto) return;

        if(abierto.contains(e.target)) return;

        cerrarArticulo(abierto);
    });


    document.getElementById("formNuevoCliente").addEventListener("submit", crearCliente);

    document.getElementById("formVenta").addEventListener("submit", async function(e) {
        e.preventDefault();

        if (ventaState.enProceso) return;
        ventaState.enProceso = true;

        const btnCrear = document.getElementById("btnCrear");
        const textoOriginal = btnCrear?.textContent;
        if (btnCrear) { btnCrear.disabled = true; btnCrear.textContent = "Guardando..."; }

        const form = e.target;
        const formData = new FormData(form);


        const nuevaPestana = window.open("", "_blank");

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

            const res = await fetch("/ventas/guardar", {
                method: "POST",
                headers: csrfToken ? { "X-CSRFToken": csrfToken } : {},
                body: formData
            });

            const data = await res.json();

            if (!data.ok) {
                if (nuevaPestana) nuevaPestana.close();
                ventaState.enProceso = false;
                if (btnCrear) { btnCrear.disabled = false; btnCrear.textContent = textoOriginal; }
                mostrarFeedback("❌ Error: " + (data.error || "No se pudo guardar la venta"), "error");
                return;
            }

            if (nuevaPestana) {
                nuevaPestana.location.href = `/ventas/ticket/${data.id_venta}`;
            } else {
                window.open(`/ventas/ticket/${data.id_venta}`, "_blank");
            }

            window.location.href = "/ventas/pendientes";

        } catch (err) {
            if (nuevaPestana) nuevaPestana.close();
            ventaState.enProceso = false;
            if (btnCrear) { btnCrear.disabled = false; btnCrear.textContent = textoOriginal; }
            mostrarFeedback("❌ Error inesperado al guardar la venta.", "error");
            console.error(err);
        }
    });


    document.getElementById("clienteBox").style.display = "none";
    document.getElementById("busquedaCliente").style.display = "block";

    document.getElementById("togglePrepago").addEventListener("change", () => {
        togglePrepago();
        validarFormulario();
        actualizarTotal();
    });

    document.getElementById("toggleDescuento").addEventListener("change", () => {
        toggleDescuento();
    });

    bloquearFechaMinima();
    togglePrepago();
    toggleDescuento();
    validarFormulario();
});

} 


function bloquearFechaMinima() {
    const input = document.getElementById("fecha_estimada_fecha");
    const hoy = new Date();
    const yyyy = hoy.getFullYear();
    const mm = String(hoy.getMonth() + 1).padStart(2, "0");
    const dd = String(hoy.getDate()).padStart(2, "0");
    const todayStr = `${yyyy}-${mm}-${dd}`;
    input.min = todayStr;
}

async function buscarClientes() {
    const q = this.value.trim();
    const lista = document.getElementById("listaClientes");
    lista.innerHTML = "";
    if (q.length < 2) return;

    let clientes;
    try {
        const res = await fetch(`/api/clientes?q=${q}`);
        if (!res.ok) throw new Error("Error de red");
        clientes = await res.json();
    } catch {
        lista.innerHTML = "<div class='result-item'>Error al buscar clientes.</div>";
        return;
    }

    clientes.forEach(c => {
        const item = document.createElement("div");
        item.className = "result-item";
        const iniciales = ((c.nombre||'')[0]||"").toUpperCase() + ((c.apellido||'')[0]||"").toUpperCase();
        const ventasLabel = c.total_ventas > 0
            ? `${c.total_ventas} venta${c.total_ventas !== 1 ? 's' : ''}`
            : 'Cliente nuevo';
        item.innerHTML = `
            <div class="result-avatar">${iniciales}</div>
            <div class="result-info">
                <div class="result-name">${c.nombre} ${c.apellido}</div>
                <div class="result-tel">${c.telefono || ''}</div>
            </div>
            <div class="result-ventas-badge ${c.total_ventas > 0 ? 'has-ventas' : 'no-ventas'}">${ventasLabel}</div>
        `;
        item.onclick = () => seleccionarCliente(c);
        lista.appendChild(item);
    });
}

function seleccionarCliente(cliente) {
    document.getElementById("id_cliente").value = cliente.id_cliente;

    const ventas = cliente.total_ventas || 0;
    const ventasText = ventas > 0
        ? `${ventas} venta${ventas !== 1 ? 's' : ''} anteriores`
        : 'Cliente nuevo';

    document.getElementById("clienteSeleccionado").innerHTML =
        `<span>${escapeHtml(cliente.nombre)} ${escapeHtml(cliente.apellido)}</span>`
        + `<span class="cliente-ventas-badge ${ventas > 0 ? 'has-ventas' : 'no-ventas'}">${escapeHtml(ventasText)}</span>`;

    document.getElementById("listaClientes").innerHTML = "";

    document.getElementById("clienteBox").style.display = "flex";

    document.getElementById("busquedaCliente").style.display = "none";

    validarFormulario();
}

function cerrarModalCliente() {
    cerrarModal("modalCliente");
    document.getElementById("formNuevoCliente").reset();
}


async function crearCliente(e) {
    e.preventDefault();

    const nombre = document.getElementById("cliente_nombre").value.trim();
    const apellido = document.getElementById("cliente_apellido").value.trim();
    const telefono = document.getElementById("cliente_telefono").value.trim();
    const errorBox = document.getElementById("errorClienteNuevo");

    if (!nombre || !apellido || !telefono) {
        errorBox.innerText = "Nombre, apellido y teléfono son obligatorios.";
        errorBox.style.display = "block";
        return;
    }

    if (!/^\d{10}$/.test(telefono)) {
        errorBox.innerText = "El teléfono debe contener exactamente 10 dígitos.";
        errorBox.style.display = "block";
        return;
    }

    errorBox.style.display = "none";

    const formData = new FormData(e.target);

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

    const res = await fetch("/api/clientes/crear", {
        method: "POST",
        headers: csrfToken ? { "X-CSRFToken": csrfToken } : {},
        body: formData
    });

    if (!res.ok) {
        errorBox.innerText = "❌ Error al crear el cliente.";
        errorBox.style.display = "block";
        return;
    }

    const cliente = await res.json();

    cerrarModalCliente();
    seleccionarCliente(cliente);
}


async function cargarServicios() {
    const idNegocio = document.getElementById("id_negocio").value;

    if (!idNegocio) {
        ventaState.serviciosGlobales = [];
        return;
    }

    try {
        const res = await fetch(`/api/servicios?id_negocio=${idNegocio}`);
        if (!res.ok) throw new Error("Error de red");
        ventaState.serviciosGlobales = await res.json();
    } catch {
        ventaState.serviciosGlobales = [];
    }
}

async function seleccionarNegocio() {
    const select = document.getElementById("id_negocio");
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
        document.getElementById("articulosContainer").innerHTML = "";
        ventaState.contadorArticulos = 0;
        actualizarTotal();
        validarFormulario();
    }
}

function agregarArticulo() {
    const idNegocio = document.getElementById("id_negocio").value;
    if (!idNegocio) {
        mostrarFeedback("Primero selecciona un negocio.", "error");
        return;
    }

    const index = ventaState.contadorArticulos;
    const tipoArticulo = obtenerTipoArticuloPorNegocio(idNegocio);

    const div = document.createElement("div");
    div.className = "articulo-item";
    const negocioNombre = document.getElementById("id_negocio")?.selectedOptions[0]?.text || "";
    div.innerHTML = `
    <div class="articulo-resumen" style="display:none;"></div>

    <div class="articulo-detalle">
    <div class="zapato-header">
        <div class="zapato-titulo">🧾 Artículo ${index + 1}${negocioNombre ? `<span class="zapato-titulo-badge">${negocioNombre}</span>` : ""}</div>
        <button type="button" class="btn btn--danger btn--sm" onclick="eliminarArticulo(this)">✕</button>
    </div>
        <input type="hidden" name="articulos[${index}][tipo_articulo]" value="${tipoArticulo}">
        ${crearCamposArticulo(index, tipoArticulo)}
    </div>
    </div>
`;


    document.getElementById("articulosContainer").appendChild(div);
    const resumenDiv = div.querySelector(".articulo-resumen");
    resumenDiv.addEventListener("click", () => abrirArticuloDesdeResumen(resumenDiv));

    ventaState.contadorArticulos++;

    document.querySelectorAll(".articulo-item.abierto").forEach(a=>{
        cerrarArticulo(a);
    });

    div.classList.add("abierto");

    const detalle = div.querySelector(".articulo-detalle");
    const resumen = div.querySelector(".articulo-resumen");

    if(detalle) detalle.style.display = "block";
    if(resumen) resumen.style.display = "none";

    actualizarOpcionesServiciosDelArticulo(index);
    validarArticuloVisual(div);
    validarFormulario();
    actualizarTotal();
}

function eliminarArticulo(btn) {
    btn.closest(".articulo-item").remove();
    renumerarArticulos();
    validarFormulario();
    actualizarTotal();
}

function renumerarArticulos() {
    document.querySelectorAll(".articulo-item").forEach((item, i) => {
        item.querySelector(".zapato-titulo").innerText = `🧾 Artículo ${i + 1}`;
    });
    ventaState.contadorArticulos = document.querySelectorAll(".articulo-item").length;

    if (ventaState.contadorArticulos === 0) {
        document.getElementById("errorNegocio").style.display = "none";
    }
}

function obtenerTipoArticuloPorNegocio(idNegocio) {
    if (idNegocio === "1") return "calzado";
    if (idNegocio === "2") return "confeccion";
    if (idNegocio === "3") return "maquila";
    return "";
}

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
                ${inputConLabel("Tipo", `articulos[${index}][tipo]`, "Tenis, Bota...", true)}
                ${inputConLabel("Marca", `articulos[${index}][marca]`, "Nike, Puma...", true)}
                ${inputConLabel("Material", `articulos[${index}][material]`, "Gamuza, Piel...", true)}
                ${inputConLabel("Color base", `articulos[${index}][color_base]`, "Negro, Blanco...", true)}
                ${inputConLabel("Color secundario (Opcional)", `articulos[${index}][color_secundario]`, "Negro, Blanco...", false)}
                ${inputConLabel("Color agujetas (Opcional)", `articulos[${index}][color_agujetas]`, "Negro, Blanco...", false)}
            </div>

            ${crearServiciosSelect(index)}

            ${inputConLabel("Comentario", `articulos[${index}][comentario]`, "(opcional)", false)}
        `;
    }

    if (tipoArticulo === "confeccion") {
        return `
            <div class="form-group form-row articulo-row">
                ${inputConLabel("Tipo", `articulos[${index}][tipo]`, "Pantalón, Falda...", true)}
                ${inputConLabel("Marca", `articulos[${index}][marca]`, "Zara, Levis...", true)}
                ${inputConLabel("Material", `articulos[${index}][material]`, "Mezclilla, Gamuza...", true)}
                ${inputConLabel("Color base", `articulos[${index}][color_base]`, "Negro, Blanco...", true)}
                ${inputConLabel("Color secundario (Opcional)", `articulos[${index}][color_secundario]`, "Negro, Blanco...", false)}
                ${inputConLabel("Cantidad", `articulos[${index}][cantidad]`, "1,2...", true, "number", `min="1"`)}

            </div>

            ${crearServiciosSelect(index)}

            ${inputConLabel("Comentario", `articulos[${index}][comentario]`, "(opcional)", false)}
        `;
    }

    return `
        <div class="form-group form-row articulo-row">
            ${inputConLabel("Tipo", `articulos[${index}][tipo]`, "Mandil, Bata...", true)}
            ${inputConLabel("Cantidad", `articulos[${index}][cantidad]`, "1,2...", true, "number", `min="1"`)}

            ${inputConLabel("Precio unitario", `articulos[${index}][precio_unitario]`, "$10.00", true, "number", `min="0"`)}

        </div>

        ${inputConLabel("Comentario", `articulos[${index}][comentario]`, "(opcional)", false)}
    `;
}

function crearServiciosSelect(indexArticulo) {
    let opciones = `<option value="">-- Selecciona servicio --</option>`;
    ventaState.serviciosGlobales.forEach(s => {
        const precio = s.precio_base ?? s.precio ?? 0;
        opciones += `<option value="${s.id_servicio}" data-precio="${precio}">
            ${s.nombre} ($${precio})
        </option>`;
    });

    return `
        <div class="form-group servicios-box" data-articulo="${indexArticulo}">
            
            <div class="servicios-header">
                <label class="form-label">Servicios</label>

                <button type="button"
                        class="btn btn--info btn--sm"
                        onclick="agregarServicio(${indexArticulo})">
                    ➕ Agregar servicio
                </button>

            </div>

            <div class="servicios-lista" id="serviciosLista_${indexArticulo}">
                ${crearFilaServicio(indexArticulo, 0, opciones)}
            </div>
        </div>
    `;
}

function crearFilaServicio(indexArticulo, indexServicio, opcionesHTML) {
    return `
        <div class="servicio-item" data-index-servicio="${indexServicio}"
             style="display:flex; gap:10px; align-items:center; margin-bottom:8px;">

            <select name="articulos[${indexArticulo}][servicios][${indexServicio}][id_servicio]"
                    onchange="onChangeServicio(this, ${indexArticulo}); validarFormulario(); actualizarTotal(); validarArticuloVisual(this.closest('.articulo-item'))">
                ${opcionesHTML}
            </select>

            <input type="number"
                   min="0"
                   step="0.01"
                   class="precio-aplicado"
                   name="articulos[${indexArticulo}][servicios][${indexServicio}][precio_aplicado]"
                   placeholder="Precio aplicado"
                   value=""
                   disabled
                   data-editado="0"
                   oninput="marcarPrecioEditado(this); validarFormulario(); actualizarTotal()"
                   style="width:150px;">

            <button type="button"
                    class="btn btn--danger btn--sm"
                    onclick="eliminarServicioPro(this, ${indexArticulo})">
                ✕
            </button>
        </div>
    `;
}

function marcarPrecioEditado(input) {
    input.dataset.editado = "1";
}

function agregarServicio(indexArticulo) {
    const contenedor = document.getElementById(`serviciosLista_${indexArticulo}`);

    let opciones = `<option value="">-- Selecciona servicio --</option>`;
    ventaState.serviciosGlobales.forEach(s => {
        const precio = s.precio_base ?? s.precio ?? 0;
        opciones += `<option value="${s.id_servicio}" data-precio="${precio}">
            ${s.nombre} ($${precio})
        </option>`;
    });

    const indexServicio = contenedor.querySelectorAll(".servicio-item").length;
    contenedor.insertAdjacentHTML("beforeend", crearFilaServicio(indexArticulo, indexServicio, opciones));

    actualizarOpcionesServiciosDelArticulo(indexArticulo);
    validarFormulario();
    actualizarTotal();
}

function eliminarServicioPro(btn, indexArticulo) {
    const fila = btn.closest(".servicio-item");
    const contenedor = fila.parentElement;

    fila.remove();

    if (contenedor.querySelectorAll(".servicio-item").length === 0) {
        let opciones = `<option value="">-- Selecciona servicio --</option>`;
        ventaState.serviciosGlobales.forEach(s => {
            const precio = s.precio_base ?? s.precio ?? 0;
            opciones += `<option value="${s.id_servicio}" data-precio="${precio}">
                ${s.nombre} ($${precio})
            </option>`;
        });

        contenedor.insertAdjacentHTML("beforeend", crearFilaServicio(indexArticulo, 0, opciones));
    }

    actualizarOpcionesServiciosDelArticulo(indexArticulo);
    validarFormulario();
    actualizarTotal();
}

function onChangeServicio(select, indexArticulo) {
    const fila = select.closest(".servicio-item");
    const inputPrecio = fila.querySelector(".precio-aplicado");
    const opt = select.selectedOptions[0];

    if (!opt || !opt.value) {
        inputPrecio.value = "";
        inputPrecio.disabled = true;
        inputPrecio.dataset.editado = "0";
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
        select.value = "";
        inputPrecio.value = "";
        inputPrecio.disabled = true;
        inputPrecio.dataset.editado = "0";
    }

    actualizarOpcionesServiciosDelArticulo(indexArticulo);
    actualizarTotal(); 
}

function hayServicioRepetidoEnArticulo(indexArticulo) {
    const contenedor = document.getElementById(`serviciosLista_${indexArticulo}`);
    const selects = contenedor.querySelectorAll("select");

    const vistos = new Set();
    for (const sel of selects) {
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

    const usados = new Set();
    selects.forEach(sel => {
        if (sel.value) usados.add(sel.value);
    });

    selects.forEach(sel => {
        const valorActual = sel.value;

        Array.from(sel.options).forEach(opt => {
            if (!opt.value) return;

            if (usados.has(opt.value) && opt.value !== valorActual) {
                opt.disabled = true;
            } else {
                opt.disabled = false;
            }
        });
    });
}

function togglePrepago() {
    const checked = document.getElementById("togglePrepago").checked;
    document.getElementById("prepago").value = checked ? "si" : "no";
    const fields = document.getElementById("prepago-fields");
    fields.style.display = checked ? "flex" : "none";
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
    fields.style.display = checked ? "flex" : "none";
    if (checked) {
        setTimeout(() => fields.scrollIntoView({ behavior: "smooth", block: "nearest" }), 50);
    } else {
        document.getElementById("cantidad_descuento").value = "";
    }
    validarFormulario();
    actualizarTotal();
}


function articulosCompletos() {
    const articulos = document.querySelectorAll(".articulo-item");
    if (articulos.length === 0) return false;

    const negocio = document.getElementById("id_negocio").value;

    for (const art of articulos) {
        const campos = art.querySelectorAll("input, select, textarea");

        for (const campo of campos) {
            if (campo.offsetParent === null) continue;

            const name = campo.name || "";

            if (negocio === "1") {
                if (
                    name.includes("[color_secundario]") ||
                    name.includes("[color_agujetas]")
                ) {
                    continue;
                }
            }

            if (negocio === "2") {
                if (name.includes("[color_secundario]")) {
                    continue;
                }
            }

            if (campo.hasAttribute("required")) {
                if (!campo.value || campo.value.trim() === "") {
                    return false;
                }
            }
        }
    }

    return true;
}


function validarFormulario() {
    let valido = true;

    const cliente = document.getElementById("id_cliente").value;
    const negocio = document.getElementById("id_negocio").value;
    const fechaEstimada = document.getElementById("fecha_estimada").value;

    const prepago = document.getElementById("prepago").value;
    const tipoPago = document.getElementById("tipo_pago").value;
    const montoPrepago = parseFloat(document.getElementById("monto_prepago")?.value || 0);

    const aplicaDesc = document.getElementById("aplica_descuento").value === "si";
    const descuento = parseFloat(document.getElementById("cantidad_descuento")?.value || 0);


    /* ---------- Negocio y fecha ---------- */
    if (!negocio || !fechaEstimada) {
        valido = false;
    }

    /* ---------- Artículos ---------- */
    const articulos = document.querySelectorAll(".articulo-item");
    if (articulos.length === 0 || !articulosCompletos()) {
        valido = false;
    }

    /* ---------- Servicios obligatorios ---------- */
    if (negocio === "1" || negocio === "2") {
        document.querySelectorAll(".servicios-box").forEach(box => {
            const selects = box.querySelectorAll("select");

            let cantidadSeleccionados = 0;
            let hayVacio = false;

            selects.forEach(sel => {
                if (sel.value && sel.value.trim() !== "") {
                    cantidadSeleccionados++;
                } else {
                    hayVacio = true;
                }
            });

            if (cantidadSeleccionados === 0 || hayVacio) {
                valido = false;
            }
        });
    }

    /* ---------- Prepago ---------- */
    if (prepago === "si") {
        if (!tipoPago || montoPrepago <= 0) {
            valido = false;
        }

        if (montoPrepago > calcularTotal()) {
            document.getElementById("errorPrepago").style.display = "block";
            valido = false;
        } else {
            document.getElementById("errorPrepago").style.display = "none";
        }
    } else {
        document.getElementById("errorPrepago").style.display = "none";
    }

    /* ---------- Descuento ---------- */
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

    /* ---------- MENSAJE DE BLOQUEO ---------- */
    const motivos = obtenerMotivosBloqueo();
    const btn = document.getElementById("btnCrear");
    const msg = document.getElementById("mensajeBloqueo");

    btn.disabled = !valido || motivos.length > 0;

    if (motivos.length > 0) {
        msg.innerText = "Falta: " + motivos.join(" · ");
        msg.style.display = "block";
    } else {
        msg.style.display = "none";
    }
}



function calcularTotal(bruto = false) {
    const negocio = document.getElementById("id_negocio").value;
    let total = 0;

    if (negocio === "1") {
        document.querySelectorAll(".servicio-item").forEach(fila => {
            const sel = fila.querySelector("select");
            const precio = fila.querySelector(".precio-aplicado");

            if (sel && sel.value) {
                total += parseFloat(precio?.value || 0);
            }
        });
    }

    if (negocio === "2") {
        document.querySelectorAll(".articulo-item").forEach(articulo => {
            const cantidad = parseFloat(
                articulo.querySelector("input[name$='[cantidad]']")?.value || 1
            );

            articulo.querySelectorAll(".servicio-item").forEach(fila => {
                const sel = fila.querySelector("select");
                const precio = fila.querySelector(".precio-aplicado");

                if (sel && sel.value) {
                    total += cantidad * parseFloat(precio?.value || 0);
                }
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

    if (aplicaDesc && desc > 0) {
        total -= desc;
        if (total < 0) total = 0;
    }

    return total;
}



function actualizarTotal() {
    const total = calcularTotal();
    document.getElementById("totalVenta").innerText = `Total: $${total.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function actualizarFechaEstimadaCompleta() {
    const fecha = document.getElementById("fecha_estimada_fecha").value;
    const hora = document.getElementById("fecha_estimada_hora").value;

    if (fecha && hora) {
        document.getElementById("fecha_estimada").value = `${fecha} ${hora}:00`;
    } else {
        document.getElementById("fecha_estimada").value = "";
    }
}


function obtenerMotivosBloqueo() {
    const motivos = [];

    if (!document.getElementById("id_cliente").value) {
        motivos.push("Seleccionar un cliente");
    }

    if (!document.getElementById("id_negocio").value) {
        motivos.push("Eligir un negocio");
    }

    if (!document.getElementById("fecha_estimada").value) {
        motivos.push("Definir fecha y hora");
    }

    const articulos = document.querySelectorAll(".articulo-item");
    if (articulos.length === 0) {
        motivos.push("Agregar al menos un artículo");
    } else if (!articulosCompletos()) {
        motivos.push("Completar los datos de los artículos");
    }

    const prepago = document.getElementById("prepago").value;
    if (prepago === "si") {
        const tipoPago = document.getElementById("tipo_pago").value;
        const monto = parseFloat(document.getElementById("monto_prepago").value || 0);

        if (!tipoPago) {
            motivos.push("Seleccionar el tipo de pago");
        }
        if (monto <= 0) {
            motivos.push("Ingresar un monto de prepago válido");
        }
        if (monto > calcularTotal()) {
            motivos.push("El prepago supera el total");
        }
    }

    const aplicaDesc = document.getElementById("aplica_descuento").value === "si";
    if (aplicaDesc) {
        const desc = parseFloat(document.getElementById("cantidad_descuento").value || 0);
        const totalBruto = calcularTotal(true);

        if (desc <= 0) {
            motivos.push("El descuento debe ser mayor a 0");
        } else if (desc > totalBruto) {
            motivos.push("El descuento supera el total");
        }
    }

    return motivos;
}

function toggleArticulo(btn){
    const item = btn.closest(".articulo-item");
    const detalle = item.querySelector(".articulo-detalle");
    const resumen = item.querySelector(".articulo-resumen");

    const abierto = detalle.style.display !== "none";

    if(abierto){
        generarResumenArticulo(item);
        detalle.style.display = "none";
        resumen.style.display = "block";
        btn.innerText = "Editar";
        item.classList.remove("abierto");
    }else{
        document.querySelectorAll(".articulo-item.abierto").forEach(a=>{
            if(a !== item) cerrarArticulo(a);
        });
        detalle.style.display = "block";
        resumen.style.display = "none";
        btn.innerText = "Minimizar";
        item.classList.add("abierto");
    }
}



function generarResumenArticulo(item){
    const resumen = item.querySelector(".articulo-resumen");

    const tipo   = item.querySelector("input[name$='[tipo]']")?.value || "";
    const marca  = item.querySelector("input[name$='[marca]']")?.value || "";
    const color  = item.querySelector("input[name$='[color_base]']")?.value || "";
    const mat    = item.querySelector("input[name$='[material]']")?.value || "";
    const cant   = item.querySelector("input[name$='[cantidad]']")?.value || "";
    const precio = calcularTotalArticulo(item);

    const svcs = [...item.querySelectorAll(".servicio-item select")]
        .filter(s => s.value)
        .map(s => s.selectedOptions[0]?.text.split(" ($")[0] || "")
        .join(", ");

    const partes = [color, mat, cant ? `x${cant}` : ""].filter(Boolean);
    const detalle = partes.join(" · ");

    const negSel = document.getElementById("id_negocio");
    const negNombre = negSel?.selectedOptions[0]?.text || "";

    const titulo = item.querySelector(".zapato-titulo")?.innerText || "Artículo";

    const btnEl = item.querySelector(".btn--danger")?.outerHTML || "";
    resumen.innerHTML = `
        <div class="resumen-header-bar">
            <span class="resumen-header-label">${titulo}</span>
            <div style="display:flex;align-items:center;gap:6px">
                <span class="resumen-header-badge">${negNombre}</span>
                ${btnEl}
            </div>
        </div>
        <div class="resumen-body">
            <div class="resumen-linea">
                <div>
                    <div class="resumen-nombre">${tipo} ${marca}</div>
                    ${detalle ? `<div class="resumen-detalle">${detalle}</div>` : ""}
                    ${svcs ? `<div class="resumen-detalle resumen-svcs">🔧 ${svcs}</div>` : ""}
                </div>
                <div class="resumen-precio">$${precio.toFixed(2)}</div>
            </div>
            <div class="resumen-hint">✏️ Toca para editar</div>
        </div>
    `;
}
function calcularTotalArticulo(item){
    const negocio = document.getElementById("id_negocio").value;
    let total = 0;

    if(negocio === "1"){
        item.querySelectorAll(".servicio-item").forEach(fila=>{
            const sel = fila.querySelector("select");
            const precio = fila.querySelector(".precio-aplicado");

            if(sel && sel.value){
                total += parseFloat(precio?.value || 0);
            }
        });
    }

    if(negocio === "2"){
        const cantidad = parseFloat(
            item.querySelector("input[name$='[cantidad]']")?.value || 1
        );

        item.querySelectorAll(".servicio-item").forEach(fila=>{
            const sel = fila.querySelector("select");
            const precio = fila.querySelector(".precio-aplicado");

            if(sel && sel.value){
                total += cantidad * parseFloat(precio?.value || 0);
            }
        });
    }

    if(negocio === "3"){
        const cantidad = parseFloat(
            item.querySelector("input[name$='[cantidad]']")?.value || 0
        );
        const precio = parseFloat(
            item.querySelector("input[name$='[precio_unitario]']")?.value || 0
        );

        total = cantidad * precio;
    }

    return total;
}



function cerrarArticulo(item){
    const detalle = item.querySelector(".articulo-detalle");
    const resumen = item.querySelector(".articulo-resumen");

    generarResumenArticulo(item);
    detalle.style.display = "none";
    resumen.style.display = "block";

    item.classList.remove("abierto");
    validarArticuloVisual(item);
}


function articuloCompleto(item){
    const negocio = document.getElementById("id_negocio").value;

    const campos = item.querySelectorAll("input[required], select[required]");

    for(const c of campos){
        if(!c.value || c.value.trim() === ""){
            return false;
        }
    }

    if(negocio === "1" || negocio === "2"){
        const selects = item.querySelectorAll(".servicio-item select");

        let cantidadSeleccionados = 0;
        let hayVacio = false;

        selects.forEach(sel=>{
            if(sel.value && sel.value.trim() !== ""){
                cantidadSeleccionados++;
            }else{
                hayVacio = true;
            }
        });

        if(cantidadSeleccionados === 0 || hayVacio){
            return false;
        }
    }

    return true;
}


function abrirArticuloDesdeResumen(resumenDiv){
    const item = resumenDiv.closest(".articulo-item");

    document.querySelectorAll(".articulo-item.abierto").forEach(a=>{
        if(a !== item) cerrarArticulo(a);
    });

    const detalle = item.querySelector(".articulo-detalle");
    const resumen = item.querySelector(".articulo-resumen");

    detalle.style.display = "block";
    resumen.style.display = "none";

    item.classList.add("abierto");
}

function validarArticuloVisual(item){
    const completo = articuloCompleto(item);

    item.classList.remove("completo", "incompleto");

    if(completo){
        item.classList.add("completo");
    }else{
        item.classList.add("incompleto");
    }
}