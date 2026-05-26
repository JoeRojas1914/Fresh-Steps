import { ventaState } from './ventas_state.js';
import { mostrarFeedback } from '../base/helpers.js';
import { buscarClientes, crearCliente } from './ventas_clientes.js';
import { seleccionarNegocio, agregarServicio, eliminarServicioPro, onChangeServicio, marcarPrecioEditado } from './ventas_servicios.js';
import { agregarArticulo, cerrarArticulo, eliminarArticulo, validarArticuloVisual } from './ventas_articulos.js';
import { validarFormulario, togglePrepago, toggleDescuento, actualizarTotal, bloquearFechaMinima, actualizarFechaEstimadaCompleta } from './ventas_validacion.js';

document.addEventListener("DOMContentLoaded", () => {

    /* ── Búsqueda de cliente con debounce ── */
    let _buscarTimer;
    document.getElementById("buscar-cliente").addEventListener("input", () => {
        clearTimeout(_buscarTimer);
        const q     = document.getElementById("buscar-cliente").value.trim();
        const lista = document.getElementById("lista-clientes");
        if (q.length < 2) { lista.innerHTML = ""; return; }
        lista.innerHTML = `<div class="result-item resultado-buscando">Buscando...</div>`;
        _buscarTimer = setTimeout(buscarClientes, 350);
    });

    /* ── Cambiar cliente ── */
    document.getElementById("btn-cambiar-cliente").addEventListener("click", () => {
        document.getElementById("id_cliente").value               = "";
        document.getElementById("cliente-seleccionado").innerText = "";
        document.getElementById("cliente-box").style.display      = "none";
        document.getElementById("busqueda-cliente").style.display = "block";
        document.getElementById("buscar-cliente").value           = "";
        document.getElementById("lista-clientes").innerHTML       = "";
        validarFormulario();
    });

    /* ── Cerrar artículo al hacer clic fuera ── */
    document.addEventListener("click", e => {
        if (e.target.closest("#btn-agregar-articulo")) return;
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

        const btnCrear      = document.getElementById("btn-crear");
        const textoOriginal = btnCrear?.textContent;
        if (btnCrear) { btnCrear.disabled = true; btnCrear.textContent = "Guardando..."; }

        const csrfToken    = document.querySelector('meta[name="csrf-token"]')?.content;
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
                nuevaPestana.location.href = `/ventas/ticket/${data.id_venta}?copias=2`;
            } else {
                window.open(`/ventas/ticket/${data.id_venta}?copias=2`, "_blank");
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
    document.getElementById("cliente-box").style.display      = "none";
    document.getElementById("busqueda-cliente").style.display = "block";

    /* ── Otros listeners ── */
    document.getElementById("toggle-prepago").addEventListener("change", () => {
        togglePrepago();
        validarFormulario();
        actualizarTotal();
    });
    document.getElementById("toggle-descuento").addEventListener("change", toggleDescuento);
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
    document.getElementById("btn-agregar-articulo").addEventListener("click", agregarArticulo);

    /* ── Event delegation para artículos ── */
    const articulosContainer = document.getElementById("articulos-container");

    articulosContainer.addEventListener("change", e => {
        const sel = e.target;
        if (sel.tagName !== "SELECT" || !sel.closest(".servicio-item")) return;
        const box           = sel.closest(".servicios-box");
        const indexArticulo = parseInt(box?.dataset?.articulo ?? "0");
        onChangeServicio(sel, indexArticulo);
        validarFormulario();
        actualizarTotal();
        validarArticuloVisual(sel.closest(".articulo-item"));
    });

    articulosContainer.addEventListener("input", e => {
        const target = e.target;
        if (target.classList.contains("precio-aplicado")) {
            marcarPrecioEditado(target);
        }
        validarFormulario();
        actualizarTotal();
        const art = target.closest(".articulo-item");
        if (art) validarArticuloVisual(art);
    });

    articulosContainer.addEventListener("click", e => {
        const btn = e.target.closest("[data-action]");
        if (!btn) return;
        const action = btn.dataset.action;
        if (action === "delete-article") {
            eliminarArticulo(btn);
        } else if (action === "add-service") {
            const box           = btn.closest(".servicios-box");
            const indexArticulo = parseInt(box?.dataset?.articulo ?? "0");
            agregarServicio(indexArticulo);
        } else if (action === "delete-service") {
            const box           = btn.closest(".servicios-box");
            const indexArticulo = parseInt(box?.dataset?.articulo ?? "0");
            eliminarServicioPro(btn, indexArticulo);
        }
    });

    /* ── Inicialización ── */
    bloquearFechaMinima();
    togglePrepago();
    toggleDescuento();
    validarFormulario();
});
