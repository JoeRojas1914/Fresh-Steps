export function validarTelefono(v)  { return /^\d{10}$/.test((v || "").trim()); }
export function validarRequerido(v) { return (v || "").trim().length > 0; }
export function validarUsername(v)  { return /^[a-zA-Z0-9_]{3,}$/.test((v || "").trim()); }
export function validarPassword(v)  { return /^(?=.*\d).{6,}$/.test((v || "").trim()); }
export function validarPin(v)       { return /^\d{4}$/.test((v || "").trim()); }
export function validarPrecio(v)    { return !isNaN(parseFloat(v)) && parseFloat(v) >= 0; }
