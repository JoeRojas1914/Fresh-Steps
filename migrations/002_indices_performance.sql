-- =============================================================
-- Fresh Steps — Índices de performance
-- Aplica sobre la BD existente (idempotente con IF NOT EXISTS)
-- =============================================================

-- Filtra usuarios por rol en login y en obtener_usuarios_caja_activos()
-- Los índices anteriores solo cubren usuario(usuario) — no rol+activo
CREATE INDEX IF NOT EXISTS idx_usuario_rol_activo
    ON usuario(rol, activo);
