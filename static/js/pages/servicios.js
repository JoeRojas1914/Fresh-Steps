document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector(".modal-form");
    if (form) {
        form.addEventListener("submit", function (e) {
            const negocio = document.getElementById("id_negocio").value;
            const nombre = document.querySelector("[name=nombre]").value.trim();
            const precio = document.querySelector("[name=precio]").value;

            if (!negocio || !nombre || precio === "") {
                mostrarFeedback("Negocio, nombre y precio son obligatorios.", "error");
                e.preventDefault();
                return;
            }

            if (parseFloat(precio) < 0) {
                mostrarFeedback("El precio no puede ser negativo.", "error");
                e.preventDefault();
            }
        });
    }

    const select = document.getElementById("select-negocio-servicios");
    const toggle = document.getElementById("toggle-eliminados-servicios");
    const formFiltro = document.getElementById("form-filtro-servicios");

    if (formFiltro) {
        if (select) {
            select.addEventListener("change", () => formFiltro.submit());
        }

        if (toggle) {
            toggle.addEventListener("change", () => formFiltro.submit());
        }
    }
});


const _eliminarServicio = crearEliminarHandler("modalConfirmarEliminarServicio");
window.confirmarEliminarServicio = id => _eliminarServicio.confirmar(`/servicios/eliminar/${id}`);
window.ejecutarEliminarServicio  = ()  => _eliminarServicio.ejecutar();


window.abrirNuevoServicio = function () {
    abrirModal("modalServicio");

    document.getElementById("modalServicio_title").innerText = "Agregar servicio";
    document.getElementById("id_servicio").value = "";

    document.querySelector(".modal-form").reset();
};


window.editarServicio = function (btn) {
    abrirModal("modalServicio");

    document.getElementById("modalServicio_title").innerText = "Editar servicio";

    document.getElementById("id_servicio").value = btn.dataset.id;
    document.getElementById("id_negocio").value = btn.dataset.negocio;
    document.querySelector("[name=nombre]").value = btn.dataset.nombre;
    document.querySelector("[name=precio]").value = btn.dataset.precio;
};


window.verHistorialServicio = function (id) {
    abrirHistorial(
        `/servicios/${id}/historial`,
        "modalHistorialServicio",
        "#tablaHistorialServicio",
        h => renderDiff(h, "Servicio")
    );
};

document.addEventListener("click", function (e) {
    const btnNuevo = e.target.closest(".js-abrir-nuevo-servicio");
    if (btnNuevo) { abrirNuevoServicio(); return; }

    const btnEditar = e.target.closest(".js-editar-servicio");
    if (btnEditar) { editarServicio(btnEditar); return; }

    const btnHistorial = e.target.closest(".js-ver-historial-servicio");
    if (btnHistorial) { verHistorialServicio(parseInt(btnHistorial.dataset.id)); return; }

    const btnEliminar = e.target.closest(".js-confirmar-eliminar-servicio");
    if (btnEliminar) { confirmarEliminarServicio(parseInt(btnEliminar.dataset.id)); return; }

    const btnEjecutar = e.target.closest(".js-ejecutar-eliminar-servicio");
    if (btnEjecutar) { ejecutarEliminarServicio(); return; }
});