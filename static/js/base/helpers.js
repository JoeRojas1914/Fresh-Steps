window.csrfFetch = function (url, options = {}) {

    const tokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (!tokenMeta) {
        console.error("CSRF token not found");
        return fetch(url, options);
    }

    const token = tokenMeta.getAttribute("content");

    options.headers = {
        ...options.headers,
        "X-CSRFToken": token,
        "Content-Type": "application/json"
    };

    return fetch(url, options);
};


window.mostrarFeedback = function (texto, tipo = "success") {
    const anchor =
        document.querySelector(".page-content > .filtro-box") ||
        document.querySelector(".page-content > h1") ||
        document.querySelector(".page-content");

    const div = document.createElement("div");
    div.className = `alert ${tipo}`;
    div.textContent = texto;
    div.style.animation = "slideIn 0.25s ease";

    if (anchor && anchor.parentNode) {
        anchor.parentNode.insertBefore(div, anchor);
    } else {
        document.body.prepend(div);
    }

    setTimeout(() => {
        div.style.transition = "opacity 0.5s ease, transform 0.5s ease";
        div.style.opacity    = "0";
        div.style.transform  = "translateX(10px)";
    }, 4500);

    setTimeout(() => div.remove(), 5000);
};


document.addEventListener("DOMContentLoaded", () => {
    const alerts = document.querySelectorAll(".alert");

    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.5s ease, transform 0.5s ease";
            alert.style.opacity    = "0";
            alert.style.transform  = "translateX(10px)";
        }, 4500);

        setTimeout(() => {
            alert.style.display = "none";
        }, 5000);
    });
});