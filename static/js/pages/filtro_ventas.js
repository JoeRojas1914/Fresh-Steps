document.addEventListener("DOMContentLoaded", () => {

    const filtroNegocio = document.getElementById("filtro-negocio");
    const inputCliente  = document.getElementById("buscador-cliente");
    const inputTicket   = document.getElementById("buscador-ticket");
    const form          = filtroNegocio?.form || inputCliente?.form || inputTicket?.form;
    const container     = document.getElementById("tabla-paginada");

    window.initFiltroAjax(form, container);
});
