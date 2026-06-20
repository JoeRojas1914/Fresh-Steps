import { abrirModal, cerrarModal } from '../components/modal.js';
import { mostrarFeedback, recargarConFeedback, csrfFetch, confirmarEliminarVenta } from '../base/helpers.js';

let ventaEntregaActual  = null;
let saldoPendienteActual = 0;
let ventaRevertirActual  = null;

document.addEventListener("DOMContentLoaded", () => {

    document.addEventListener("click", function (e) {
        const btn = e.target.closest(".btn-eliminar");
        if (!btn) return;
        confirmarEliminarVenta(btn.dataset.id);
    });

    document.addEventListener("click", function (e) {
        const btn = e.target.closest(".btn-revertir");
        if (!btn) return;
        ventaRevertirActual = parseInt(btn.dataset.id);
        abrirModal("modalRevertir");
    });

    const btnConfirmarRevertir = document.getElementById("btnConfirmarRevertir");
    if (btnConfirmarRevertir) {
        btnConfirmarRevertir.addEventListener("click", confirmarRevertir);
    }

    document.querySelectorAll(".btn-entregar").forEach(btn => {
        btn.addEventListener("click", () => {
            const idVenta = parseInt(btn.dataset.id);
            const deuda   = parseFloat(btn.dataset.deuda);
            const pagado  = parseFloat(btn.dataset.pagado);
            const total   = parseFloat(btn.dataset.total);

            abrirModalEntrega(idVenta, deuda, pagado, total);
        });
    });

    const metodoPagoFinal = document.getElementById("metodoPagoFinal");
    if (metodoPagoFinal) {
        metodoPagoFinal.addEventListener("change", function () {
            if (saldoPendienteActual > 0) {
                document.getElementById("btnConfirmarEntrega").disabled = !this.value;
            }
        });
    }

});


function abrirModalEntrega(idVenta, deuda, pagado, total) {
    ventaEntregaActual   = idVenta;
    saldoPendienteActual = deuda;

    abrirModal("modalEntrega");

    const bloquePago    = document.getElementById("bloquePago");
    const textoSinDeuda = document.getElementById("textoSinDeuda");
    const btnConfirmar  = document.getElementById("btnConfirmarEntrega");

    if (deuda <= 0) {
        textoSinDeuda.style.display = "block";
        bloquePago.style.display    = "none";
        btnConfirmar.onclick        = confirmarEntregaSinPago;
    } else {
        textoSinDeuda.style.display = "none";
        bloquePago.style.display    = "block";

        document.getElementById("montoPendiente").innerText = `$${deuda.toFixed(2)}`;
        btnConfirmar.disabled = true;
        btnConfirmar.onclick  = confirmarPagoYEntrega;
    }
}


function confirmarEntregaSinPago() {
    const btn = document.getElementById("btnConfirmarEntrega");
    if (btn?.disabled) return;
    const textoOriginal = btn?.textContent;
    if (btn) { btn.disabled = true; btn.textContent = "Procesando..."; }

    csrfFetch(`/ventas/entregar/${ventaEntregaActual}`, { method: "POST" })
        .then(r => r.json())
        .then(res => {
            if (res.ok) {
                cerrarModalEntrega();
                recargarConFeedback(res.message, "success");
            } else {
                if (btn) { btn.disabled = false; btn.textContent = textoOriginal; }
                mostrarFeedback(res.error || "Error al entregar", "error");
            }
        })
        .catch(() => {
            if (btn) { btn.disabled = false; btn.textContent = textoOriginal; }
            mostrarFeedback("Error de conexión al entregar la venta.", "error");
        });
}


function confirmarPagoYEntrega() {
    const metodo = document.getElementById("metodoPagoFinal").value;

    if (!metodo) {
        mostrarFeedback("Selecciona un método de pago.", "error");
        return;
    }

    const btn = document.getElementById("btnConfirmarEntrega");
    if (btn?.disabled) return;
    const textoOriginal = btn?.textContent;
    if (btn) { btn.disabled = true; btn.textContent = "Procesando..."; }

    csrfFetch("/ventas/pago-final", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id_venta:    ventaEntregaActual,
            monto:       saldoPendienteActual,
            metodo_pago: metodo
        })
    })
    .then(r => r.json())
    .then(res => {
        if (res.ok) {
            cerrarModalEntrega();
            recargarConFeedback(res.message, "success");
        } else {
            if (btn) { btn.disabled = false; btn.textContent = textoOriginal; }
            mostrarFeedback(res.error || "Error al registrar pago", "error");
        }
    })
    .catch(() => {
        if (btn) { btn.disabled = false; btn.textContent = textoOriginal; }
        mostrarFeedback("Error de conexión al registrar el pago.", "error");
    });
}


function cerrarModalEntrega() {
    cerrarModal("modalEntrega");

    const metodo = document.getElementById("metodoPagoFinal");
    if (metodo) metodo.value = "";

    const btnConfirmar = document.getElementById("btnConfirmarEntrega");
    if (btnConfirmar) btnConfirmar.disabled = false;

    const texto  = document.getElementById("textoSinDeuda");
    const bloque = document.getElementById("bloquePago");

    if (texto)  texto.style.display  = "none";
    if (bloque) bloque.style.display = "none";
}


function confirmarRevertir() {
    if (!ventaRevertirActual) return;
    const btn = document.getElementById("btnConfirmarRevertir");
    if (btn?.disabled) return;
    const textoOriginal = btn?.textContent;
    if (btn) { btn.disabled = true; btn.textContent = "Procesando..."; }

    csrfFetch(`/ventas/revertir-lista/${ventaRevertirActual}`, { method: "POST" })
        .then(r => r.json())
        .then(res => {
            cerrarModal("modalRevertir");
            if (res.ok) {
                recargarConFeedback(res.message, "success");
            } else {
                if (btn) { btn.disabled = false; btn.textContent = textoOriginal; }
                mostrarFeedback(res.error || "Error al revertir la venta", "error");
            }
        })
        .catch(() => {
            cerrarModal("modalRevertir");
            if (btn) { btn.disabled = false; btn.textContent = textoOriginal; }
            mostrarFeedback("Error de conexión al revertir la venta.", "error");
        });
}
