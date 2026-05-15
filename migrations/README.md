# Migraciones de Base de Datos — Fresh Steps

## Cómo aplicar una migración

```bash
mysql -u FreshStepsTest -p freshsteps < migrations/001_schema_completo.sql
```

## Convención de numeración

```
migrations/
  001_schema_completo.sql       ← Estado inicial completo (mayo 2026)
  002_agregar_campo_xxx.sql     ← Cambios incrementales
  003_nueva_tabla_yyy.sql
```

Cada archivo debe:
- Usar `IF NOT EXISTS` o `IF EXISTS` para ser idempotente cuando sea posible
- Incluir un comentario con la fecha y una descripción del cambio

## Crear una nueva migración

1. Copiar el número siguiente al último archivo existente
2. Nombrar el archivo descriptivamente: `NNN_descripcion_breve.sql`
3. Incluir solo el cambio incremental (no el esquema completo)

Ejemplo:
```sql
-- Migración 002: agregar campo notas a clientes — junio 2026
ALTER TABLE cliente ADD COLUMN notas TEXT AFTER direccion;
```
