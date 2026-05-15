-- =============================================================
-- Fresh Steps — Esquema completo de base de datos
-- Migración 001: estado del esquema a mayo 2026
-- Aplicar sobre una BD vacía: mysql -u user -p freshsteps < 001_schema_completo.sql
-- =============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- -------------------------------------------------------------
-- Negocios
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS negocio (
    id_negocio INT AUTO_INCREMENT PRIMARY KEY,
    nombre     VARCHAR(100) NOT NULL
);

-- Datos iniciales (IDs fijos — el código los referencia directamente)
INSERT IGNORE INTO negocio (id_negocio, nombre) VALUES
    (1, 'Calzado'),
    (2, 'Confección'),
    (3, 'Maquila');

-- -------------------------------------------------------------
-- Usuarios
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuario (
    id_usuario    INT AUTO_INCREMENT PRIMARY KEY,
    usuario       VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255),
    pin_hash      VARCHAR(255),
    rol           ENUM('admin', 'caja', 'empleado') NOT NULL DEFAULT 'caja',
    nombre        VARCHAR(100),
    apellido      VARCHAR(100),
    telefono      VARCHAR(20),
    correo        VARCHAR(150),
    cp            VARCHAR(10),
    activo        TINYINT(1) NOT NULL DEFAULT 1,
    creado_en     DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- -------------------------------------------------------------
-- Clientes
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cliente (
    id_cliente     INT AUTO_INCREMENT PRIMARY KEY,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    nombre         VARCHAR(100) NOT NULL,
    apellido       VARCHAR(100),
    correo         VARCHAR(150),
    telefono       VARCHAR(20),
    direccion      VARCHAR(255),
    activo         TINYINT(1) NOT NULL DEFAULT 1,
    id_usuario     INT,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
);

CREATE TABLE IF NOT EXISTS clientes_historial (
    id_historial  INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente    INT NOT NULL,
    accion        VARCHAR(50) NOT NULL,   -- CREADO | EDITADO | ELIMINADO | RESTAURADO
    id_usuario    INT,
    datos_antes   JSON,
    datos_despues JSON,
    fecha         DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente),
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
);

-- -------------------------------------------------------------
-- Servicios
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS servicio (
    id_servicio INT AUTO_INCREMENT PRIMARY KEY,
    id_negocio  INT NOT NULL,
    nombre      VARCHAR(100) NOT NULL,
    precio      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    activo      TINYINT(1) NOT NULL DEFAULT 1,
    FOREIGN KEY (id_negocio) REFERENCES negocio(id_negocio)
);

CREATE TABLE IF NOT EXISTS servicios_historial (
    id_historial  INT AUTO_INCREMENT PRIMARY KEY,
    id_servicio   INT NOT NULL,
    accion        VARCHAR(50) NOT NULL,
    id_usuario    INT,
    datos_antes   JSON,
    datos_despues JSON,
    fecha         DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_servicio) REFERENCES servicio(id_servicio),
    FOREIGN KEY (id_usuario)  REFERENCES usuario(id_usuario)
);

-- -------------------------------------------------------------
-- Ventas
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS venta (
    id_venta           INT AUTO_INCREMENT PRIMARY KEY,
    id_negocio         INT NOT NULL,
    id_cliente         INT,
    fecha_recibo       DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_estimada     DATETIME,
    fecha_lista        DATETIME,
    fecha_entrega      DATETIME,
    aplica_descuento   TINYINT(1) NOT NULL DEFAULT 0,
    cantidad_descuento DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total              DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    id_usuario_creo    INT,
    id_usuario_entrego INT,
    eliminado          TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (id_negocio)         REFERENCES negocio(id_negocio),
    FOREIGN KEY (id_cliente)         REFERENCES cliente(id_cliente),
    FOREIGN KEY (id_usuario_creo)    REFERENCES usuario(id_usuario),
    FOREIGN KEY (id_usuario_entrego) REFERENCES usuario(id_usuario)
);

CREATE TABLE IF NOT EXISTS venta_historial (
    id_historial  INT AUTO_INCREMENT PRIMARY KEY,
    id_venta      INT NOT NULL,
    accion        VARCHAR(50) NOT NULL,
    id_usuario    INT,
    datos_antes   JSON,
    datos_despues JSON,
    fecha         DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_venta)   REFERENCES venta(id_venta),
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
);

-- -------------------------------------------------------------
-- Artículos (tabla abstracta + especializaciones por tipo)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS articulo (
    id_articulo  INT AUTO_INCREMENT PRIMARY KEY,
    id_venta     INT NOT NULL,
    tipo_articulo ENUM('calzado', 'confeccion', 'maquila') NOT NULL,
    comentario   TEXT,
    FOREIGN KEY (id_venta) REFERENCES venta(id_venta)
);

CREATE TABLE IF NOT EXISTS articulo_calzado (
    id_articulo      INT PRIMARY KEY,
    tipo             VARCHAR(100),
    marca            VARCHAR(100),
    material         VARCHAR(100),
    color_base       VARCHAR(50),
    color_secundario VARCHAR(50),
    color_agujetas   VARCHAR(50),
    FOREIGN KEY (id_articulo) REFERENCES articulo(id_articulo)
);

CREATE TABLE IF NOT EXISTS articulo_confeccion (
    id_articulo      INT PRIMARY KEY,
    tipo             VARCHAR(100),
    marca            VARCHAR(100),
    material         VARCHAR(100),
    color_base       VARCHAR(50),
    color_secundario VARCHAR(50),
    cantidad         INT NOT NULL DEFAULT 1,
    agujetas         TINYINT(1) DEFAULT 0,
    FOREIGN KEY (id_articulo) REFERENCES articulo(id_articulo)
);

CREATE TABLE IF NOT EXISTS articulo_maquila (
    id_articulo    INT PRIMARY KEY,
    tipo           VARCHAR(100),
    cantidad       INT NOT NULL DEFAULT 1,
    precio_unitario DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    FOREIGN KEY (id_articulo) REFERENCES articulo(id_articulo)
);

CREATE TABLE IF NOT EXISTS articulo_servicio (
    id_articulo_servicio INT AUTO_INCREMENT PRIMARY KEY,
    id_articulo          INT NOT NULL,
    id_servicio          INT NOT NULL,
    precio_aplicado      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    FOREIGN KEY (id_articulo) REFERENCES articulo(id_articulo),
    FOREIGN KEY (id_servicio) REFERENCES servicio(id_servicio)
);

-- -------------------------------------------------------------
-- Pagos
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pago_venta (
    id_pago_venta  INT AUTO_INCREMENT PRIMARY KEY,
    id_venta       INT NOT NULL,
    fecha_pago     DATETIME DEFAULT CURRENT_TIMESTAMP,
    monto          DECIMAL(10,2) NOT NULL,
    tipo_pago      VARCHAR(50),        -- efectivo | tarjeta | transferencia
    tipo_pago_venta VARCHAR(50),       -- prepago | final
    id_usuario_cobro INT,
    FOREIGN KEY (id_venta)         REFERENCES venta(id_venta),
    FOREIGN KEY (id_usuario_cobro) REFERENCES usuario(id_usuario)
);

-- -------------------------------------------------------------
-- Gastos
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gastos (
    id_gasto         INT AUTO_INCREMENT PRIMARY KEY,
    id_negocio       INT NOT NULL,
    descripcion      TEXT,
    proveedor        VARCHAR(150),
    total            DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    fecha_registro   DATE,
    tipo_comprobante VARCHAR(50),
    tipo_pago        VARCHAR(50),
    id_usuario       INT,
    eliminado        TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (id_negocio) REFERENCES negocio(id_negocio),
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
);

CREATE TABLE IF NOT EXISTS gastos_historial (
    id_historial  INT AUTO_INCREMENT PRIMARY KEY,
    id_gasto      INT NOT NULL,
    accion        VARCHAR(50) NOT NULL,
    id_usuario    INT,
    datos_antes   JSON,
    datos_despues JSON,
    fecha         DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_gasto)   REFERENCES gastos(id_gasto),
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
);

-- -------------------------------------------------------------
-- Historial de usuarios
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS historial_usuario (
    id_historial         INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario_modificado INT NOT NULL,
    accion               VARCHAR(50) NOT NULL,
    id_usuario_ejecuto   INT,
    datos_antes          JSON,
    datos_despues        JSON,
    fecha                DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario_modificado) REFERENCES usuario(id_usuario),
    FOREIGN KEY (id_usuario_ejecuto)    REFERENCES usuario(id_usuario)
);

-- -------------------------------------------------------------
-- Autenticación y seguridad
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS login_log (
    id_log     INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT,
    usuario    VARCHAR(100),
    metodo     VARCHAR(50),       -- password_admin | pin_caja
    exito      TINYINT(1) NOT NULL DEFAULT 0,
    ip         VARCHAR(50),
    user_agent TEXT,
    fecha      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
);

CREATE TABLE IF NOT EXISTS login_intentos (
    id_intento     INT AUTO_INCREMENT PRIMARY KEY,
    usuario        VARCHAR(100) NOT NULL,
    ip             VARCHAR(50)  NOT NULL,
    intentos       INT NOT NULL DEFAULT 0,
    bloqueado_hasta DATETIME,
    UNIQUE KEY uq_usuario_ip (usuario, ip)
);

SET FOREIGN_KEY_CHECKS = 1;
