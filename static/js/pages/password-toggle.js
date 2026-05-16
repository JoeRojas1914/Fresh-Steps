const _SVG_OJO_ABIERTO = `
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
    <circle cx="12" cy="12" r="3"/>`;

const _SVG_OJO_CERRADO = `
    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
    <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
    <line x1="1" y1="1" x2="23" y2="23"/>`;

document.addEventListener("DOMContentLoaded", function () {
    [
        { toggle: "togglePwd", input: "passwordInput", icon: "iconoOjo" },
        { toggle: "togglePin", input: "pinInput",      icon: "iconoOjoPin" },
    ].forEach(function ({ toggle, input, icon }) {
        const btn = document.getElementById(toggle);
        if (!btn) return;
        btn.addEventListener("click", function () {
            const inp     = document.getElementById(input);
            const showing = inp.type === "password";
            inp.type      = showing ? "text" : "password";
            document.getElementById(icon).innerHTML = showing ? _SVG_OJO_CERRADO : _SVG_OJO_ABIERTO;
            this.style.color = showing ? "#1e7fd6" : "#94a3b8";
        });
    });

    if (window.lucide) lucide.createIcons();
});
