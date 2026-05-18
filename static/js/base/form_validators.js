window.validarTelefono  = v => /^\d{10}$/.test((v || "").trim());
window.validarRequerido = v => (v || "").trim().length > 0;
window.validarUsername  = v => /^[a-zA-Z0-9_]{3,}$/.test((v || "").trim());
window.validarPassword  = v => /^(?=.*\d).{6,}$/.test((v || "").trim());
window.validarPin       = v => /^\d{4}$/.test((v || "").trim());
window.validarPrecio    = v => !isNaN(parseFloat(v)) && parseFloat(v) >= 0;
