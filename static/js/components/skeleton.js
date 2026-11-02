(function () {

    const ANCHOS = ["w75", "w50", "w65", "w40", "w85", "w55", "w60", "w45", "w70", "w30"];

    function linea(i, extra = "") {
        return `<div class="skeleton skeleton--line skeleton--${ANCHOS[i % ANCHOS.length]}${extra}"></div>`;
    }

    function filas(columnas, n = 5) {
        let html = "";
        for (let f = 0; f < n; f++) {
            html += `<tr class="skeleton-row" aria-hidden="true">`;
            for (let c = 0; c < columnas; c++) html += `<td>${linea(f * 3 + c)}</td>`;
            html += `</tr>`;
        }
        return html;
    }

    function lineas(n = 2) {
        let html = "";
        for (let i = 0; i < n; i++) {
            html += `<li class="skeleton-li" aria-hidden="true">${linea(i * 2)}${linea(i * 2 + 1)}</li>`;
        }
        return html;
    }

    function tabla(contenedor) {
        const tbody = contenedor?.querySelector("table tbody");
        if (!tbody) return false;
        const columnas = contenedor.querySelectorAll("table thead th").length || 4;
        const visibles = tbody.querySelectorAll(":scope > tr:not(.table--details)").length;
        tbody.innerHTML = filas(columnas, Math.min(Math.max(visibles, 3), 8));
        contenedor.setAttribute("aria-busy", "true");
        return true;
    }

    window.Skeleton = { filas, lineas, tabla };
})();
