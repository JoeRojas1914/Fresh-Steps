document.addEventListener("DOMContentLoaded", () => {

    const inputBusqueda = document.getElementById("buscador-cliente");
    const selectNegocio = document.getElementById("filtro-negocio");
    const tabla = document.querySelector("#tabla-ventas table");

    if (!inputBusqueda || !selectNegocio || !tabla) return;

    const filas = tabla.querySelectorAll("tbody tr");

    function aplicarFiltro() {

        const textoBusqueda = normalizar(inputBusqueda.value);
        const negocioSeleccionado = normalizar(selectNegocio.value);

        filas.forEach(fila => {

            if (fila.classList.contains("table--details")) return;

            const columnas = fila.querySelectorAll("td");
            if (columnas.length < 3) return;

            const negocio = normalizar(columnas[1].innerText);
            const cliente = normalizar(columnas[2].innerText);

            const coincideCliente = cliente.includes(textoBusqueda);
            const coincideNegocio =
                !negocioSeleccionado || negocio.includes(negocioSeleccionado);

            const mostrar = coincideCliente && coincideNegocio;

            fila.style.display = mostrar ? "" : "none";

            const idVenta = columnas[0].innerText.replace("#", "").trim();
            const filaDetalles = document.getElementById(`detalles-${idVenta}`);

            if (filaDetalles) {
                filaDetalles.style.display = "none";
            }

        });
    }

    inputBusqueda.addEventListener("input", aplicarFiltro);
    selectNegocio.addEventListener("change", aplicarFiltro);

});