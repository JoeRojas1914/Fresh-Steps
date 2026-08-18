document.addEventListener("DOMContentLoaded", () => {

    const filtroNegocio = document.getElementById("filtro-negocio");
    const inputCliente  = document.getElementById("buscador-cliente");
    const inputTicket   = document.getElementById("buscador-ticket");
    const form          = filtroNegocio?.form || inputCliente?.form || inputTicket?.form;
    const container     = document.getElementById("tabla-paginada");

    if (!form || !container) return;

    function buildUrl() {
        const params = new URLSearchParams(new FormData(form));
        for (const [k, v] of [...params.entries()]) {
            if (!v) params.delete(k);
        }
        const qs = params.toString();
        return qs ? `${form.action}?${qs}` : form.action;
    }

    async function cargarTabla(url) {
        const fetchUrl = new URL(url, window.location.href);
        fetchUrl.searchParams.set("partial", "1");

        container.style.opacity       = "0.5";
        container.style.pointerEvents = "none";

        try {
            const resp = await fetch(fetchUrl.toString());
            if (!resp.ok) throw new Error(resp.status);
            container.innerHTML = await resp.text();
            history.pushState(null, "", url);
            if (window.lucide) window.lucide.createIcons();
        } catch {
            window.location.href = url;
        } finally {
            container.style.opacity       = "";
            container.style.pointerEvents = "";
        }
    }

    let debounceTimer = null;

    function autoBuscar() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => cargarTabla(buildUrl()), 300);
    }

    if (filtroNegocio) filtroNegocio.addEventListener("change", () => cargarTabla(buildUrl()));
    if (inputCliente)  inputCliente.addEventListener("input", autoBuscar);
    if (inputTicket)   inputTicket.addEventListener("input", autoBuscar);

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        clearTimeout(debounceTimer);
        cargarTabla(buildUrl());
    });

});
