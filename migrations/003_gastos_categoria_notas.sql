-- Migración 003: Categoría y notas en gastos
-- Aplicar con: mysql -u user -p freshsteps < migrations/003_gastos_categoria_notas.sql

CREATE TABLE IF NOT EXISTS categoria_gasto (
    id_categoria  INT          NOT NULL AUTO_INCREMENT,
    nombre        VARCHAR(100) NOT NULL,
    PRIMARY KEY (id_categoria)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO categoria_gasto (nombre) VALUES
    ('Materia Prima'),
    ('Servicios (luz, agua, internet)'),
    ('Nómina'),
    ('Renta'),
    ('Transporte'),
    ('Mantenimiento'),
    ('Publicidad'),
    ('Equipo y Herramientas'),
    ('Otros');

ALTER TABLE gastos
    ADD COLUMN id_categoria INT  NULL DEFAULT NULL AFTER id_negocio,
    ADD COLUMN notas        TEXT NULL DEFAULT NULL AFTER tipo_pago,
    ADD CONSTRAINT fk_gastos_categoria
        FOREIGN KEY (id_categoria) REFERENCES categoria_gasto (id_categoria)
        ON UPDATE CASCADE ON DELETE SET NULL;
