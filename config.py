# Timeouts de sesión por rol (minutos de inactividad)
TIMEOUT_ADMIN = 15
TIMEOUT_CAJA  = 20

# Control de intentos de login fallidos — contraseña admin
MAX_INTENTOS_LOGIN = 5
BLOQUEO_MIN_LOGIN  = 10

# Control de intentos fallidos — PIN caja (más estricto: PIN es de 4-6 dígitos)
MAX_INTENTOS_PIN = 3
BLOQUEO_MIN_PIN  = 30

# Paginación
POR_PAGINA_HISTORIAL_VENTAS = 20
POR_PAGINA_VENTAS_ACTIVAS   = 30

# Exportaciones Excel: máximo de filas para evitar agotamiento de RAM
MAX_FILAS_EXPORTAR = 10_000

# Métodos de pago válidos en ventas
METODOS_PAGO_VALIDOS = {"efectivo", "transferencia"}

# Etiquetas legibles para exportaciones y reportes
PAGO_LABEL = {"efectivo": "Efectivo", "transferencia": "Transferencia", "TDC": "Tarjeta de crédito"}
COMPROBANTE_LABEL = {"factura": "Factura", "ticket": "Ticket"}
