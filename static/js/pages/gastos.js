import { abrirModal } from '../components/modal.js';
import { mostrarFeedback, crearEliminarHandler } from '../base/helpers.js';
import { validarRequerido, validarPrecio } from '../base/form_validators.js';
import { renderDiff, abrirHistorial } from '../base/historial_helpers.js';

document.addEventListener("DOMContentLoaded", () => {

    const toggleEliminados = document.getElementById("toggle-eliminados-gastos");
    if (toggleEliminados) {
        toggleEliminados.addEventListener("change", () => {
            const url = new URL(window.location.href);
            if (toggleEliminados.checked) {
                url.searchParams.set("eliminados", "1");
            } else {
                url.searchParams.delete("eliminados");
            }
            window.location.href = url.toString();
        });
    }

    const form = document.querySelector(".modal-form");
    if (!form) return;

    form.addEventListener("submit", function (e) {
        const descripcion = document.querySelector("[name=descripcion]").value;
        const proveedor   = document.querySelector("[name=proveedor]").value;
        const total       = document.querySelector("[name=total]").value;

        if (!validarRequerido(descripcion) || !validarRequerido(proveedor) || !validarRequerido(total)) {
            mostrarFeedback("Descripción, proveedor y total son obligatorios.", "error");
            e.preventDefault();
            return;
        }

        if (!validarPrecio(total)) {
            mostrarFeedback("El total no puede ser negativo.", "error");
            e.preventDefault();
            return;
        }

        const btn = this.querySelector('[type="submit"]');
        if (btn) { btn.disabled = true; btn.textContent = "Guardando..."; }
    });

});


const _eliminarGasto = crearEliminarHandler("modalConfirmarEliminarGasto");
function confirmarEliminarGasto(id) { _eliminarGasto.confirmar(`/gastos/eliminar/${id}`); }
function ejecutarEliminarGasto()    { _eliminarGasto.ejecutar(); }


function editarGasto(id, id_negocio, descripcion, proveedor, total, fecha_registro, tipo_comprobante, tipo_pago) {
    abrirModal("modalGasto");
    document.getElementById("modalGasto_title").innerText           = "Editar gasto";
    document.getElementById("id_gasto").value                       = id;
    document.getElementById("id_negocio").value                     = id_negocio;
    document.querySelector("[name=descripcion]").value              = descripcion;
    document.querySelector("[name=proveedor]").value                = proveedor;
    document.querySelector("[name=total]").value                    = total;
    document.querySelector("[name=fecha_registro]").value           = fecha_registro || "";
    document.querySelector("[name=tipo_comprobante]").value         = tipo_comprobante;
    document.querySelector("[name=tipo_pago]").value                = tipo_pago;
}

document.addEventListener("click", function (e) {
    const btnEditar = e.target.closest(".js-editar-gasto");
    if (btnEditar) {
        const d = btnEditar.dataset;
        editarGasto(d.id, d.idNegocio, d.descripcion, d.proveedor, d.total, d.fecha, d.tipoComprobante, d.tipoPago);
        return;
    }

    const btnHistorial = e.target.closest(".js-ver-historial-gasto");
    if (btnHistorial) { verHistorial(parseInt(btnHistorial.dataset.id)); return; }

    const btnEliminar = e.target.closest(".js-confirmar-eliminar-gasto");
    if (btnEliminar) {
        const el = document.getElementById("gastoNombreEliminar");
        if (el) el.innerHTML = `¿Seguro que deseas eliminar?<br><span>${btnEliminar.dataset.descripcion}</span>`;
        _eliminarGasto.confirmar(`/gastos/eliminar/${btnEliminar.dataset.id}`, btnEliminar.closest("tr"));
        return;
    }

    const btnEjecutar = e.target.closest(".js-ejecutar-eliminar-gasto");
    if (btnEjecutar) { ejecutarEliminarGasto(); return; }
});


function verHistorial(id) {
    abrirHistorial(
        `/gastos/${id}/historial`,
        "modalHistorial",
        "#tablaHistorial",
        h => renderDiff(h, "Gasto")
    );
}
