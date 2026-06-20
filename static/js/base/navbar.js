document.addEventListener("DOMContentLoaded", () => {

    const navToggle = document.getElementById("navToggle");
    const navbar    = document.getElementById("navbar");

    const navbarBottom = navbar.getBoundingClientRect().bottom + window.scrollY;
    let placeholder = null;

    window.addEventListener("scroll", () => {
        if (window.scrollY > navbarBottom) {
            if (!navbar.classList.contains("navbar--fixed")) {
                navbar.classList.add("navbar--fixed");
                placeholder = document.createElement("div");
                placeholder.style.height = navbar.offsetHeight + "px";
                navbar.parentNode.insertBefore(placeholder, navbar);
            }
        } else {
            if (navbar.classList.contains("navbar--fixed")) {
                navbar.classList.remove("navbar--fixed");
                placeholder?.remove();
                placeholder = null;
            }
        }
    }, { passive: true });

    if (navToggle && navbar) {
        navToggle.addEventListener("click", () => {
            if (navbar.classList.contains("open")) {
                const items = navbar.querySelectorAll(".nav-group a, .nav-right");
                items.forEach((el, i) => {
                    el.style.animationDelay = (i * 20) + "ms";
                });
                navbar.classList.add("nav-closing");
                setTimeout(() => {
                    navbar.classList.remove("open", "nav-closing");
                    items.forEach(el => el.style.animationDelay = "");
                    navToggle.setAttribute("aria-expanded", "false");
                    navToggle.setAttribute("aria-label", "Abrir menú de navegación");
                }, items.length * 20 + 160);
            } else {
                navbar.classList.add("open");
                const items = navbar.querySelectorAll(".nav-group a, .nav-right");
                items.forEach((el, i) => {
                    el.style.animationDelay = (i * 35) + "ms";
                });
                navToggle.setAttribute("aria-expanded", "true");
                navToggle.setAttribute("aria-label", "Cerrar menú de navegación");
            }
        });
    }

    const userBtn      = document.getElementById("userBtn");
    const userMenu     = document.getElementById("userMenu");
    const userDropdown = document.getElementById("userDropdown");

    if (userBtn && userMenu && userDropdown) {
        userBtn.addEventListener("click", () => {
            const show = userMenu.classList.toggle("show");
            userBtn.setAttribute("aria-expanded", show ? "true" : "false");
        });

        document.addEventListener("click", (e) => {
            if (!userDropdown.contains(e.target)) {
                userMenu.classList.remove("show");
                userBtn.setAttribute("aria-expanded", "false");
            }
        });
    }

});