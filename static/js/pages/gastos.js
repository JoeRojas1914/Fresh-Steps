document.addEventListener("DOMContentLoaded", () => {

    const toggleEliminados = document.getElementById("toggle-eliminados-gastos");
    if (toggleEliminados) {
        toggleEliminados.addEventListener("change", () => toggleEliminados.form.submit());
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
        }
    });

});


const _eliminarGasto = crearEliminarHandler("modalConfirmarEliminarGasto");
window.confirmarEliminarGasto = id => _eliminarGasto.confirmar(`/gastos/eliminar/${id}`);
window.ejecutarEliminarGasto  = ()  => _eliminarGasto.ejecutar();


window.editarGasto = function (id, id_negocio, descripcion, proveedor, total, fecha_registro, tipo_comprobante, tipo_pago) {
    abrirModal("modalGasto");
    document.getElementById("modalGasto_title").innerText = "Editar gasto";
    document.getElementById("id_gasto").value = id;
    document.getElementById("id_negocio").value = id_negocio;
    document.querySelector("[name=descripcion]").value = descripcion;
    document.querySelector("[name=proveedor]").value = proveedor;
    document.querySelector("[name=total]").value = total;
    document.querySelector("[name=fecha_registro]").value = fecha_registro || "";
    document.querySelector("[name=tipo_comprobante]").value = tipo_comprobante;
    document.querySelector("[name=tipo_pago]").value = tipo_pago;
};

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
    if (btnEliminar) { confirmarEliminarGasto(parseInt(btnEliminar.dataset.id)); return; }

    const btnEjecutar = e.target.closest(".js-ejecutar-eliminar-gasto");
    if (btnEjecutar) { ejecutarEliminarGasto(); return; }
});




window.verHistorial = function (id) {
    abrirHistorial(
        `/gastos/${id}/historial`,
        "modalHistorial",
        "#tablaHistorial",
        h => renderDiff(h, "Gasto")
    );
};
