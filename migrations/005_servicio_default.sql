ALTER TABLE negocio
    ADD COLUMN id_servicio_default INT NULL AFTER tipo,
    ADD CONSTRAINT fk_negocio_servicio_default
        FOREIGN KEY (id_servicio_default) REFERENCES servicio (id_servicio) ON DELETE SET NULL;
