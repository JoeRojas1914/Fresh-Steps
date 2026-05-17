/* ─── Búsqueda de cliente ────────────────────────────────────────────────── */

async function buscarClientes() {
    const q     = document.getElementById("buscarCliente").value.trim();
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
        const item     = document.createElement("div");
        item.className = "result-item";
        const iniciales   = ((c.nombre || "")[0] || "").toUpperCase() + ((c.apellido || "")[0] || "").toUpperCase();
        const ventasLabel = c.total_ventas > 0
            ? `${c.total_ventas} venta${c.total_ventas !== 1 ? "s" : ""}`
            : "Cliente nuevo";
        item.innerHTML = `
            <div class="result-avatar">${escapeHtml(iniciales)}</div>
            <div class="result-info">
                <div class="result-name">${escapeHtml(c.nombre)} ${escapeHtml(c.apellido)}</div>
                <div class="result-tel">${escapeHtml(c.telefono || "")}</div>
            </div>
            <div class="result-ventas-badge ${c.total_ventas > 0 ? "has-ventas" : "no-ventas"}">${ventasLabel}</div>
        `;
        item.onclick = () => seleccionarCliente(c);
        lista.appendChild(item);
    });
}

/* ─── Selección de cliente ───────────────────────────────────────────────── */

function seleccionarCliente(cliente) {
    document.getElementById("id_cliente").value = cliente.id_cliente;

    const ventas     = cliente.total_ventas || 0;
    const ventasText = ventas > 0
        ? `${ventas} venta${ventas !== 1 ? "s" : ""} anteriores`
        : "Cliente nuevo";

    document.getElementById("clienteSeleccionado").innerHTML =
        `<span>${escapeHtml(cliente.nombre)} ${escapeHtml(cliente.apellido)}</span>`
        + `<span class="cliente-ventas-badge ${ventas > 0 ? "has-ventas" : "no-ventas"}">${escapeHtml(ventasText)}</span>`;

    document.getElementById("listaClientes").innerHTML  = "";
    document.getElementById("clienteBox").style.display  = "flex";
    document.getElementById("busquedaCliente").style.display = "none";

    validarFormulario();
}

/* ─── Crear cliente rápido ───────────────────────────────────────────────── */

function cerrarModalCliente() {
    cerrarModal("modalCliente");
    document.getElementById("formNuevoCliente").reset();
}

async function crearCliente(e) {
    e.preventDefault();

    const nombre   = document.getElementById("cliente_nombre").value.trim();
    const apellido = document.getElementById("cliente_apellido").value.trim();
    const telefono = document.getElementById("cliente_telefono").value.trim();
    const errorBox = document.getElementById("errorClienteNuevo");

    if (!nombre || !apellido || !telefono) {
        errorBox.innerText     = "Nombre, apellido y teléfono son obligatorios.";
        errorBox.style.display = "block";
        return;
    }

    if (!/^\d{10}$/.test(telefono)) {
        errorBox.innerText     = "El teléfono debe contener exactamente 10 dígitos.";
        errorBox.style.display = "block";
        return;
    }

    errorBox.style.display = "none";

    const formData  = new FormData(e.target);
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

    const res = await fetch("/api/clientes/crear", {
        method:  "POST",
        headers: csrfToken ? { "X-CSRFToken": csrfToken } : {},
        body:    formData,
    });

    if (!res.ok) {
        errorBox.innerText     = "Error al crear el cliente.";
        errorBox.style.display = "block";
        return;
    }

    const cliente = await res.json();
    cerrarModalCliente();
    seleccionarCliente(cliente);
    mostrarFeedback("Cliente creado correctamente.", "success");
}
