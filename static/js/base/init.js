lucide.createIcons();

document.addEventListener("click", function(e) {
    const btn = e.target.closest(".btn");
    if (!btn || btn.disabled) return;
    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x    = e.clientX - rect.left - size / 2;
    const y    = e.clientY - rect.top  - size / 2;
    const span = document.createElement("span");
    span.className = "btn-ripple";
    span.style.cssText = "width:" + size + "px;height:" + size + "px;left:" + x + "px;top:" + y + "px";
    btn.appendChild(span);
    span.addEventListener("animationend", function() { span.remove(); }, { once: true });
});
