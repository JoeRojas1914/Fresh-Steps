document.addEventListener("DOMContentLoaded", () => {

    const inputCliente  = document.getElementById("buscador-cliente");
    const inputTicket   = document.getElementById("buscador-ticket");
    const form          = inputCliente?.form || inputTicket?.form;
    const container     = document.getElementById("tabla-paginada");

    window.initFiltroAjax(form, container);
});
