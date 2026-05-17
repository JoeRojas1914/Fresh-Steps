# Migraciones de Base de Datos — Fresh Steps

## Aplicar el esquema completo (BD nueva)

```bash
mysql -u FreshStepsTest -p freshsteps < migrations/001_schema_completo.sql
```

`001_schema_completo.sql` es el único archivo necesario para levantar una BD desde cero.
Contiene tablas, datos iniciales e índices. Es idempotente (`IF NOT EXISTS`).

## Agregar una migración incremental

Cuando el esquema cambie en producción (una BD ya existente):

1. Crear `migrations/002_descripcion_breve.sql` con solo el cambio incremental.
2. Aplicarlo en producción: `mysql -u user -p freshstepsproduccion < migrations/002_descripcion_breve.sql`
3. Incorporar el cambio también en `001_schema_completo.sql` para que las BDs nuevas lo incluyan.

```sql
-- Ejemplo 002: agregar campo notas a clientes — junio 2026
ALTER TABLE cliente ADD COLUMN notas TEXT AFTER direccion;
```
