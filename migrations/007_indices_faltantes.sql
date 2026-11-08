-- 007 — noviembre 2026
-- Crea los índices de 001_schema_completo.sql que falten en una BD existente.
-- MySQL 8.0 no soporta `CREATE INDEX IF NOT EXISTS` (es sintaxis de MariaDB): por eso
-- 001 fallaba en el primer índice. Este script revisa information_schema y solo crea
-- los que no existen, así que se puede correr varias veces.
-- Nuevo: idx_venta_fecha_entrega (KPIs y estadísticas de entregas).

-- idx_usuario_usuario
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'usuario' AND index_name = 'idx_usuario_usuario');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_usuario_usuario ON usuario(usuario)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_cliente_nombre_apellido
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'cliente' AND index_name = 'idx_cliente_nombre_apellido');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_cliente_nombre_apellido ON cliente(nombre, apellido)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_cliente_id_usuario
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'cliente' AND index_name = 'idx_cliente_id_usuario');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_cliente_id_usuario ON cliente(id_usuario)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_venta_id_cliente
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'venta' AND index_name = 'idx_venta_id_cliente');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_venta_id_cliente ON venta(id_cliente, eliminado)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_venta_id_negocio
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'venta' AND index_name = 'idx_venta_id_negocio');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_venta_id_negocio ON venta(id_negocio, eliminado)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_venta_fecha_recibo
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'venta' AND index_name = 'idx_venta_fecha_recibo');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_venta_fecha_recibo ON venta(fecha_recibo)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_venta_fecha_lista
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'venta' AND index_name = 'idx_venta_fecha_lista');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_venta_fecha_lista ON venta(fecha_lista)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_venta_fecha_entrega
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'venta' AND index_name = 'idx_venta_fecha_entrega');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_venta_fecha_entrega ON venta(fecha_entrega)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_articulo_id_venta
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'articulo' AND index_name = 'idx_articulo_id_venta');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_articulo_id_venta ON articulo(id_venta)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_articulo_servicio_id_articulo
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'articulo_servicio' AND index_name = 'idx_articulo_servicio_id_articulo');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_articulo_servicio_id_articulo ON articulo_servicio(id_articulo)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_pago_venta_id_venta
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'pago_venta' AND index_name = 'idx_pago_venta_id_venta');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_pago_venta_id_venta ON pago_venta(id_venta)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_pago_venta_fecha_pago
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'pago_venta' AND index_name = 'idx_pago_venta_fecha_pago');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_pago_venta_fecha_pago ON pago_venta(fecha_pago)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_gastos_fecha_registro
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'gastos' AND index_name = 'idx_gastos_fecha_registro');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_gastos_fecha_registro ON gastos(fecha_registro)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_gastos_id_negocio
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'gastos' AND index_name = 'idx_gastos_id_negocio');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_gastos_id_negocio ON gastos(id_negocio, activo)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_usuario_rol_activo
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'usuario' AND index_name = 'idx_usuario_rol_activo');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_usuario_rol_activo ON usuario(rol, activo)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_login_intentos_usuario
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'login_intentos' AND index_name = 'idx_login_intentos_usuario');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_login_intentos_usuario ON login_intentos(usuario)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_venta_fecha_recibo_eliminado
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'venta' AND index_name = 'idx_venta_fecha_recibo_eliminado');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_venta_fecha_recibo_eliminado ON venta(fecha_recibo, eliminado)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- idx_venta_id_cliente_fecha_recibo
SET @existe := (SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = DATABASE() AND table_name = 'venta' AND index_name = 'idx_venta_id_cliente_fecha_recibo');
SET @sql := IF(@existe = 0, 'CREATE INDEX idx_venta_id_cliente_fecha_recibo ON venta(id_cliente, fecha_recibo, eliminado)', 'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
