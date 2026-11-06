lucide.createIcons();

(function () {
    const loader = document.getElementById("page-loader");
    if (!loader) return;

    window.addEventListener("pageshow", () => {
        loader.className = "is-done";
        setTimeout(() => { loader.className = ""; }, 500);
    });

    document.addEventListener("click", e => {
        const link = e.target.closest("a[href]");
        if (!link) return;
        const href = link.getAttribute("href");
        if (!href || href.startsWith("#") || href.startsWith("javascript") ||
            link.target === "_blank" || link.hasAttribute("download") ||
            e.ctrlKey || e.metaKey || e.shiftKey) return;
        setTimeout(() => {
            if (!e.defaultPrevented) loader.className = "is-loading";
        }, 0);
    });
}());

document.addEventListener("click", function(e) {
    const exportLink = e.target.closest("a[href*='exportar']");
    if (exportLink && !exportLink.dataset.exporting) {
        exportLink.dataset.exporting = "1";
        const originalHTML = exportLink.innerHTML;
        exportLink.innerHTML = '<span class="spinner spinner--sm"></span> Generando...';
        exportLink.style.pointerEvents = "none";
        setTimeout(() => {
            exportLink.innerHTML = "✓ Descargado";
            setTimeout(() => {
                exportLink.innerHTML = originalHTML;
                exportLink.style.pointerEvents = "";
                delete exportLink.dataset.exporting;
                if (window.lucide) lucide.createIcons();
            }, 1200);
        }, 1500);
    }
});
