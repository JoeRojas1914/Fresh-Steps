(function () {

    function actualizarTexto(det) {
        const marcados = [...det.querySelectorAll("input[type=checkbox]:checked")]
            .map(cb => cb.nextElementSibling?.textContent.trim() || cb.value);
        const txt = det.querySelector(".multi-select__txt");
        if (txt) txt.textContent = marcados.length ? marcados.join(", ") : det.dataset.placeholder;
    }

    function actualizarMultiSelects() {
        document.querySelectorAll("details.multi-select").forEach(actualizarTexto);
    }

    document.addEventListener("change", function (e) {
        const det = e.target.closest("details.multi-select");
        if (det) actualizarTexto(det);
    });

    document.addEventListener("click", function (e) {
        document.querySelectorAll("details.multi-select[open]").forEach(det => {
            if (!det.contains(e.target)) det.open = false;
        });
    });

    document.addEventListener("DOMContentLoaded", actualizarMultiSelects);

    window.actualizarMultiSelects = actualizarMultiSelects;
})();
