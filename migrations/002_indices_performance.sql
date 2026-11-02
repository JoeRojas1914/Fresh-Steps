CREATE INDEX IF NOT EXISTS idx_usuario_rol_activo
    ON usuario(rol, activo);
