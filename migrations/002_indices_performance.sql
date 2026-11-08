-- Incluido en 001 y en 007_indices_faltantes.sql (que es idempotente).
-- idx_usuario_rol_activo
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'usuario' AND index_name = 'idx_usuario_rol_activo');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_usuario_rol_activo ON usuario(rol, activo)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
