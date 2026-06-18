document.addEventListener("DOMContentLoaded", () => {

    const filtroNegocio = document.getElementById("filtro-negocio");
    if (filtroNegocio) {
        filtroNegocio.addEventListener("change", () => filtroNegocio.form.submit());
    }

    let debounceTimer = null;

    function autoSubmit(input) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => input.form.submit(), 500);
    }

    const inputCliente = document.getElementById("buscador-cliente");
    const inputTicket  = document.getElementById("buscador-ticket");

    if (inputCliente) inputCliente.addEventListener("input", () => autoSubmit(inputCliente));
    if (inputTicket)  inputTicket.addEventListener("input",  () => autoSubmit(inputTicket));

});
