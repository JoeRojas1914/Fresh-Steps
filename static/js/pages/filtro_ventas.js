import { normalizar } from '../base/helpers.js';

document.addEventListener("DOMContentLoaded", () => {

    const filtroNegocio = document.getElementById("filtro-negocio");
    if (filtroNegocio) {
        filtroNegocio.addEventListener("change", () => filtroNegocio.form.submit());
    }

    const inputBusqueda = document.getElementById("buscador-cliente");
    const inputTicket   = document.getElementById("buscador-ticket");
    const tabla         = document.querySelector("#tabla-ventas table");

    if (!tabla) return;

    const filas = tabla.querySelectorAll("tbody tr");

    function aplicarFiltro() {
        const textoBusqueda = inputBusqueda ? normalizar(inputBusqueda.value) : "";
        const textoTicket   = inputTicket   ? inputTicket.value.trim()        : "";

        filas.forEach(fila => {
            if (fila.classList.contains("table--details")) return;

            const columnas = fila.querySelectorAll("td");
            if (columnas.length < 3) return;

            const ticket  = columnas[0].innerText.replace("#", "").trim();
            const cliente = normalizar(columnas[2].innerText);

            const coincideNombre = !textoBusqueda || cliente.includes(textoBusqueda);
            const coincideTicket = !textoTicket   || ticket.startsWith(textoTicket);
            const mostrar        = coincideNombre && coincideTicket;

            fila.style.display = mostrar ? "" : "none";

            const filaDetalles = document.getElementById(`detalles-${ticket}`);
            if (filaDetalles) filaDetalles.style.display = "none";
        });
    }

    if (inputBusqueda) inputBusqueda.addEventListener("input", aplicarFiltro);
    if (inputTicket)   inputTicket.addEventListener("input",   aplicarFiltro);

});
