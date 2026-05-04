document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".btn--info[data-id]").forEach(btn => {
        btn.addEventListener("click", () => toggleDetalles(btn.dataset.id));
    });
});