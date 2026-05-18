document.addEventListener("DOMContentLoaded", () => {

    const filtroNegocio = document.getElementById("filtro-negocio");
    if (filtroNegocio) {
        filtroNegocio.addEventListener("change", () => filtroNegocio.form.submit());
    }

    const inputBusqueda = document.getElementById("buscador-cliente");
    const tabla = document.querySelector("#tabla-ventas table");

    if (!inputBusqueda || !tabla) return;

    const filas = tabla.querySelectorAll("tbody tr");

    function aplicarFiltro() {

        const textoBusqueda = normalizar(inputBusqueda.value);

        filas.forEach(fila => {

            if (fila.classList.contains("table--details")) return;

            const columnas = fila.querySelectorAll("td");
            if (columnas.length < 3) return;

            const cliente = normalizar(columnas[2].innerText);
            const mostrar = cliente.includes(textoBusqueda);

            fila.style.display = mostrar ? "" : "none";

            const idVenta = columnas[0].innerText.replace("#", "").trim();
            const filaDetalles = document.getElementById(`detalles-${idVenta}`);

            if (filaDetalles) {
                filaDetalles.style.display = "none";
            }

        });
    }

    inputBusqueda.addEventListener("input", aplicarFiltro);

});
