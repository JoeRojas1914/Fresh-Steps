export function abrirModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  if (modal.parentElement !== document.body) {
    document.body.appendChild(modal);
  }
  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");
  document.documentElement.classList.add("modal-open");
  const focusable = modal.querySelector("button, input, select, textarea, [tabindex]");
  if (focusable) focusable.focus({ preventScroll: true });
}

export function cerrarModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.add("is-closing");
  modal.addEventListener("animationend", () => {
    modal.classList.remove("is-open", "is-closing");
    modal.setAttribute("aria-hidden", "true");
    if (!document.querySelector(".modal.is-open")) {
      document.documentElement.classList.remove("modal-open");
    }
  }, { once: true });
}

document.addEventListener("click", e => {
  const btnOpen = e.target.closest("[data-modal-open]");
  if (btnOpen) { abrirModal(btnOpen.dataset.modalOpen); return; }

  const btnClose = e.target.closest("[data-modal-close]");
  if (btnClose) { cerrarModal(btnClose.dataset.modalClose); return; }

  const modal = e.target.closest(".modal.is-open");
  if (!modal) return;
  if (e.target === modal) cerrarModal(modal.id);
});
