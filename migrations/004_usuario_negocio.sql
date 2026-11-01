

CREATE TABLE IF NOT EXISTS usuario_negocio (
    id_usuario INT NOT NULL,
    id_negocio INT NOT NULL,
    PRIMARY KEY (id_usuario, id_negocio),
    CONSTRAINT fk_usuario_negocio_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario) ON DELETE CASCADE,
    CONSTRAINT fk_usuario_negocio_negocio
        FOREIGN KEY (id_negocio) REFERENCES negocio (id_negocio) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


INSERT IGNORE INTO usuario_negocio (id_usuario, id_negocio)
SELECT u.id_usuario, n.id_negocio
FROM usuario u
CROSS JOIN negocio n
WHERE u.rol = 'caja';
