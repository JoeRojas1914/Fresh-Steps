if (typeof ventaState === "undefined") {
    var ventaState = {
        contadorArticulos:    0,
        serviciosGlobales:    [],
        negocioSeleccionado:  "",
        enProceso:            false,
    };
}

document.addEventListener("DOMContentLoaded", () => {

    /* ── Búsqueda de cliente con debounce ── */
    let _buscarTimer;
    document.getElementById("buscarCliente").addEventListener("input", () => {
        clearTimeout(_buscarTimer);
        const q     = document.getElementById("buscarCliente").value.trim();
        const lista = document.getElementById("listaClientes");
        if (q.length < 2) { lista.innerHTML = ""; return; }
        lista.innerHTML = `<div class="result-item resultado-buscando">Buscando...</div>`;
        _buscarTimer = setTimeout(buscarClientes, 350);
    });

    /* ── Cambiar cliente ── */
    document.getElementById("btnCambiarCliente").addEventListener("click", () => {
        document.getElementById("id_cliente").value          = "";
        document.getElementById("clienteSeleccionado").innerText = "";
        document.getElementById("clienteBox").style.display      = "none";
        document.getElementById("busquedaCliente").style.display = "block";
        document.getElementById("buscarCliente").value           = "";
        document.getElementById("listaClientes").innerHTML        = "";
        validarFormulario();
    });

    /* ── Cerrar artículo al hacer clic fuera ── */
    document.addEventListener("click", e => {
        if (e.target.closest("#btnAgregarArticulo")) return;
        const abierto = document.querySelector(".articulo-item.abierto");
        if (!abierto || abierto.contains(e.target)) return;
        cerrarArticulo(abierto);
    });

    /* ── Formulario de cliente rápido ── */
    document.getElementById("formNuevoCliente").addEventListener("submit", crearCliente);

    /* ── Envío del formulario de venta ── */
    document.getElementById("formVenta").addEventListener("submit", async e => {
        e.preventDefault();

        if (ventaState.enProceso) return;
        ventaState.enProceso = true;

        const btnCrear       = document.getElementById("btnCrear");
        const textoOriginal  = btnCrear?.textContent;
        if (btnCrear) { btnCrear.disabled = true; btnCrear.textContent = "Guardando..."; }

        const csrfToken  = document.querySelector('meta[name="csrf-token"]')?.content;
        const nuevaPestana = window.open("", "_blank");

        try {
            const res  = await fetch("/ventas/guardar", {
                method:  "POST",
                headers: csrfToken ? { "X-CSRFToken": csrfToken } : {},
                body:    new FormData(e.target),
            });
            const data = await res.json();

            if (!data.ok) {
                if (nuevaPestana) nuevaPestana.close();
                ventaState.enProceso = false;
                if (btnCrear) { btnCrear.disabled = false; btnCrear.textContent = textoOriginal; }
                mostrarFeedback("Error: " + (data.error || "No se pudo guardar la venta"), "error");
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
            mostrarFeedback("Error inesperado al guardar la venta.", "error");
            console.error(err);
        }
    });

    /* ── Estado inicial ── */
    document.getElementById("clienteBox").style.display      = "none";
    document.getElementById("busquedaCliente").style.display = "block";

    /* ── Otros listeners ── */
    document.getElementById("togglePrepago").addEventListener("change", () => {
        togglePrepago();
        validarFormulario();
        actualizarTotal();
    });
    document.getElementById("toggleDescuento").addEventListener("change", toggleDescuento);
    document.getElementById("id_negocio").addEventListener("change", seleccionarNegocio);
    document.getElementById("fecha_estimada_fecha").addEventListener("change", () => {
        actualizarFechaEstimadaCompleta();
        validarFormulario();
    });
    document.getElementById("fecha_estimada_hora").addEventListener("change", () => {
        actualizarFechaEstimadaCompleta();
        validarFormulario();
    });
    document.getElementById("tipo_pago").addEventListener("change", () => {
        validarFormulario();
        actualizarTotal();
    });
    document.getElementById("monto_prepago").addEventListener("input", () => {
        validarFormulario();
        actualizarTotal();
    });
    document.getElementById("cantidad_descuento").addEventListener("input", () => {
        validarFormulario();
        actualizarTotal();
    });
    document.getElementById("btnAgregarArticulo").addEventListener("click", agregarArticulo);

    /* ── Inicialización ── */
    bloquearFechaMinima();
    togglePrepago();
    toggleDescuento();
    validarFormulario();
});
