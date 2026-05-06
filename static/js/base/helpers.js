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