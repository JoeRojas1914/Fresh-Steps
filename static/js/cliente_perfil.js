document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".btn-detalles[data-id]").forEach(btn => {
        btn.addEventListener("click", () => toggleDetalles(btn.dataset.id, btn));
    });
});