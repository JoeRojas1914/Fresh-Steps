import { abrirModal } from '../components/modal.js';
import { mostrarFeedback, crearEliminarHandler } from '../base/helpers.js';
import { validarRequerido, validarTelefono } from '../base/form_validators.js';
import { renderDiff, abrirHistorial } from '../base/historial_helpers.js';

document.addEventListener("DOMContentLoaded", () => {

    const form = document.querySelector(".modal-form");

    if (form) form.addEventListener("submit", function (e) {
        const nombre   = document.querySelector("[name=nombre]").value;
        const apellido = document.querySelector("[name=apellido]").value;
        const telefono = document.querySelector("[name=telefono]").value;

        if (!validarRequerido(nombre) || !validarRequerido(apellido) || !validarRequerido(telefono)) {
            mostrarFeedback("Nombre, apellido y teléfono son obligatorios.", "error");
            e.preventDefault();
            return;
        }

        if (!validarTelefono(telefono)) {
            mostrarFeedback("El teléfono debe tener exactamente 10 dígitos.", "error");
            e.preventDefault();
        }
    });

});


function editarClienteBtn(e, btn) {
    e.stopPropagation();

    const modal = document.getElementById("modalCliente");

    abrirModal("modalCliente");

    modal.querySelector(".modal__title").innerText = "Editar cliente";

    modal.querySelector("#id_cliente").value          = btn.dataset.id;
    modal.querySelector("[name=nombre]").value        = btn.dataset.nombre;
    modal.querySelector("[name=apellido]").value      = btn.dataset.apellido;
    modal.querySelector("[name=correo]").value        = btn.dataset.correo || "";
    modal.querySelector("[name=telefono]").value      = btn.dataset.telefono;
    modal.querySelector("[name=direccion]").value     = btn.dataset.direccion || "";
}


function verHistorialCliente(e, id) {
    e.stopPropagation();
    abrirHistorial(
        `/clientes/${id}/historial`,
        "modalHistorialCliente",
        "#tablaHistorialCliente tbody",
        h => renderDiff(h, "Cliente")
    );
}


const _eliminarCliente = crearEliminarHandler("modalConfirmarEliminarCliente");
function confirmarEliminarCliente(id) { _eliminarCliente.confirmar(`/clientes/eliminar/${id}`); }
function ejecutarEliminarCliente()    { _eliminarCliente.ejecutar(); }

function restaurarCliente(idCliente) {
    window.location.href = `/clientes/restaurar/${idCliente}`;
}

document.addEventListener("click", function (e) {
    const btnEditar = e.target.closest(".js-editar-cliente");
    if (btnEditar) { e.stopPropagation(); editarClienteBtn(e, btnEditar); return; }

    const btnHistorial = e.target.closest(".js-ver-historial-cliente");
    if (btnHistorial) { e.stopPropagation(); verHistorialCliente(e, parseInt(btnHistorial.dataset.id)); return; }

    const btnEliminar = e.target.closest(".js-confirmar-eliminar-cliente");
    if (btnEliminar) { confirmarEliminarCliente(parseInt(btnEliminar.dataset.id)); return; }

    const btnRestaurar = e.target.closest(".js-restaurar-cliente");
    if (btnRestaurar) { restaurarCliente(parseInt(btnRestaurar.dataset.id)); return; }

    const btnEjecutar = e.target.closest(".js-ejecutar-eliminar-cliente");
    if (btnEjecutar) { ejecutarEliminarCliente(); return; }

    if (e.target.closest(".modal")) return;
    const row = e.target.closest("tr[data-href]");
    if (!row) return;
    if (e.target.closest(".no-row-click")) return;
    if (e.target.tagName === "BUTTON" || e.target.tagName === "A") return;
    window.location.href = row.dataset.href;
});


(function () {
    const input = document.getElementById("buscar-cliente-input");
    if (!input) return;

    let debounceTimer;
    input.addEventListener("input", () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            const url = new URL(window.location.href);
            const q = input.value.trim();
            if (q) {
                url.searchParams.set("q", q);
            } else {
                url.searchParams.delete("q");
            }
            url.searchParams.delete("pagina");
            window.location.href = url.toString();
        }, 400);
    });
}());

(function () {
    const toggle = document.getElementById("toggle-eliminados");
    if (!toggle) return;

    toggle.addEventListener("change", () => {
        const url = new URL(window.location.href);
        if (toggle.checked) {
            url.searchParams.set("eliminados", "1");
        } else {
            url.searchParams.delete("eliminados");
        }
        url.searchParams.delete("pagina");
        window.location.href = url.toString();
    });
}());
