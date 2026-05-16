-- Migración 002: Índices para mejorar rendimiento en consultas frecuentes
-- Aplicar con: mysql -u user -p freshsteps < migrations/002_indexes.sql
-- Idempotente: usa CREATE INDEX IF NOT EXISTS (MySQL 8.0+)
-- Si usas MySQL 5.7, ignora los errores "Duplicate key name".

-- ── usuario ─────────────────────────────────────────────────────────────────
-- Búsqueda en login por nombre de usuario
CREATE INDEX IF NOT EXISTS idx_usuario_usuario ON usuario(usuario);

-- ── cliente ──────────────────────────────────────────────────────────────────
-- Búsqueda/autocomplete por nombre y apellido
CREATE INDEX IF NOT EXISTS idx_cliente_nombre_apellido ON cliente(nombre, apellido);
-- FK: clientes creados por cada usuario
CREATE INDEX IF NOT EXISTS idx_cliente_id_usuario ON cliente(id_usuario);

-- ── venta ────────────────────────────────────────────────────────────────────
-- FK: ventas de un cliente (filtro + conteo de ventas por cliente)
CREATE INDEX IF NOT EXISTS idx_venta_id_cliente ON venta(id_cliente, eliminado);
-- FK: ventas por negocio (reportes y filtros)
CREATE INDEX IF NOT EXISTS idx_venta_id_negocio ON venta(id_negocio, eliminado);
-- Filtros por fecha en historial y entregas pendientes/listas
CREATE INDEX IF NOT EXISTS idx_venta_fecha_recibo ON venta(fecha_recibo);
CREATE INDEX IF NOT EXISTS idx_venta_fecha_lista ON venta(fecha_lista);

-- ── articulo ─────────────────────────────────────────────────────────────────
-- FK: artículos de una venta (carga de detalle de venta)
CREATE INDEX IF NOT EXISTS idx_articulo_id_venta ON articulo(id_venta);

-- ── articulo_servicio ─────────────────────────────────────────────────────────
-- FK: servicios aplicados en un artículo
CREATE INDEX IF NOT EXISTS idx_articulo_servicio_id_articulo ON articulo_servicio(id_articulo);

-- ── pago_venta ───────────────────────────────────────────────────────────────
-- FK: pagos de una venta
CREATE INDEX IF NOT EXISTS idx_pago_venta_id_venta ON pago_venta(id_venta);

-- ── gastos ───────────────────────────────────────────────────────────────────
-- Filtros por fecha en listado de gastos
CREATE INDEX IF NOT EXISTS idx_gastos_fecha_registro ON gastos(fecha_registro);
-- FK: gastos por negocio
CREATE INDEX IF NOT EXISTS idx_gastos_id_negocio ON gastos(id_negocio, eliminado);

-- ── login_intentos ───────────────────────────────────────────────────────────
-- Consulta de intentos fallidos por usuario+IP (ya tiene UNIQUE, verificar)
CREATE INDEX IF NOT EXISTS idx_login_intentos_usuario ON login_intentos(usuario);
