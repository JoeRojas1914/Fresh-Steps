document.addEventListener("DOMContentLoaded", () => {

    let ventaSeleccionada = null;

    const detallesCargados = {};


    document.querySelectorAll(".btn--info").forEach(btn => {
        btn.addEventListener("click", () => {
            toggleDetalles(btn.dataset.id);
        });
    });

    document.querySelectorAll(".btn-marcar-lista").forEach(btn => {
        btn.addEventListener("click", () => {
            ventaSeleccionada = btn.dataset.id;
            abrirModal("modalProcesado"); 
        });
    });

    const btnConfirmar = document.getElementById("btnConfirmarLista");

    if (btnConfirmar) {
        btnConfirmar.addEventListener("click", () => {

            if (!ventaSeleccionada) return;

            csrfFetch(`/ventas/marcar-lista/${ventaSeleccionada}`, {
                method: "POST"
            })
            .then(r => r.json())
            .then(res => {

                if (res.ok) {
                    cerrarModal("modalProcesado");
                    mostrarFeedback(res.message, "success");

                    setTimeout(() => location.reload(), 1000);

                } else {
                    mostrarFeedback(res.error || "Error al marcar como lista", "error");
                }

            });
        });
    }

        document.querySelectorAll(".btn-eliminar").forEach(btn => {
    btn.addEventListener("click", () => {

        const idVenta = btn.dataset.id;

        const confirmar = confirm(
            "¿Seguro que deseas eliminar esta venta?\n\n" +
            "Se eliminarán artículos y pagos relacionados.\n" +
            "Esta acción NO se puede deshacer."
        );

        if (!confirmar) return;

        csrfFetch(`/ventas/eliminar/${idVenta}`, {
            method: "POST"
        })
        .then(r => r.json())
        .then(res => {

            if (res.ok) {
                mostrarFeedback(res.message || "Venta eliminada", "success");

                setTimeout(() => {
                    location.reload();
                }, 800);
            } else {
                mostrarFeedback(res.error || "Error al eliminar", "error");
            }

        })
        .catch(() => {
            mostrarFeedback("Error de conexión", "error");
        });

    });
});


});