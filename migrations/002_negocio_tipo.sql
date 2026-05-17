-- =============================================================
-- Agrega columna `tipo` a la tabla negocio
-- Permite que el código cargue los tipos dinámicamente desde la BD
-- Aplicar: mysql -u user -p freshsteps < migrations/002_negocio_tipo.sql
-- =============================================================

ALTER TABLE negocio
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(30) NULL AFTER nombre;

UPDATE negocio SET tipo = 'calzado'    WHERE id_negocio = 1 AND tipo IS NULL;
UPDATE negocio SET tipo = 'confeccion' WHERE id_negocio = 2 AND tipo IS NULL;
UPDATE negocio SET tipo = 'maquila'    WHERE id_negocio = 3 AND tipo IS NULL;
