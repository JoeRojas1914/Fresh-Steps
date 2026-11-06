# Timeouts de sesión por rol (minutos de inactividad)
TIMEOUT_ADMIN = 10
TIMEOUT_CAJA  = 60

MAX_INTENTOS_LOGIN = 5
BLOQUEO_MIN_LOGIN  = 10


MAX_INTENTOS_PIN = 5
BLOQUEO_MIN_PIN  = 5
CLAVE_PIN_TERMINAL = "__pin_terminal__"

# Paginación
POR_PAGINA_HISTORIAL_VENTAS = 20
POR_PAGINA_VENTAS_ACTIVAS   = 30

# Exportaciones Excel: máximo de filas para evitar agotamiento de RAM
MAX_FILAS_EXPORTAR = 10_000

# Métodos de pago válidos en ventas
METODOS_PAGO_VALIDOS = {"efectivo", "transferencia", "tarjeta"}

# Tipos de pago en la tabla pago_venta (columna tipo_pago_venta)
TIPO_PAGO_PREPAGO = "prepago"
TIPO_PAGO_FINAL   = "final"

# Etiquetas legibles para exportaciones y reportes
PAGO_LABEL = {"efectivo": "Efectivo", "transferencia": "Transferencia", "TDC": "Tarjeta de crédito"}
COMPROBANTE_LABEL = {"factura": "Factura", "ticket": "Ticket"}
