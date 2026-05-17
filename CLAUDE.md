# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
# Development (uses .env in project root)
python app.py

# Tests (uses scripts/.env.test — DB: freshsteps, never freshstepsproduccion)
python -m pytest
python -m pytest tests/test_ventas_service.py -v
python -m pytest tests/test_ventas_service.py::test_venta_calzado_valida_crea_registro -v
```

## Architecture

Three-layer: **routes/** (Flask Blueprints) → **services/** (business logic) → **models/** (data access).

- `routes/` import exclusively from `services/` — never directly from `models/`.
- `services/ventas_service.py` re-exports `marcar_entregada`, `obtener_venta`, `obtener_detalles_venta` from `models/ventas.py` so routes stay in one layer.
- `db.py` exposes `get_connection()` (raw connection) and `get_db()` (context manager with auto-commit/rollback). Pool size: 20, `autocommit=False`.

## Multi-business model

Three negocios with fixed IDs (referenced in code):

| id | tipo |
|----|------|
| 1 | calzado |
| 2 | confeccion |
| 3 | maquila |

`TIPOS_POR_NEGOCIO` in `models/ventas.py` maps these IDs to article types. A `venta` belongs to exactly one negocio and only accepts articles of the matching type.

## Authentication

Two flows, both using `werkzeug.security.check_password_hash`:
- **Admin** — username + password via `login_password_service()`
- **Caja** — PIN-only via `login_pin_service()`

Middleware in `middleware/auth_middleware.py` enforces session validity and per-role timeouts (15 min admin, 20 min caja). `ultima_actividad` must be set in session or the request is rejected.

## Database

- Production DB: `freshstepsproduccion`
- Test DB: `freshsteps` (configured in `scripts/.env.test`)
- Full schema: `migrations/001_schema_completo.sql` — apply to an empty DB with `mysql -u user -p freshsteps < migrations/001_schema_completo.sql`

## Tests

Integration tests against real MySQL — no mocks. `tests/conftest.py` loads `scripts/.env.test` before importing the app. Fixtures use `yield` + DELETE for cleanup.

If a test run is interrupted mid-teardown, test users (`test_admin_pytest`, `test_caja_pytest`) may be left in the DB and cause `Duplicate entry` errors on the next run. Fix by manually deleting them:

```python
# python -c "..."
from dotenv import load_dotenv; import os
load_dotenv(os.path.join('scripts', '.env.test'), override=True)
from db import get_connection
conn = get_connection(); cur = conn.cursor()
for u in ('test_admin_pytest', 'test_caja_pytest'):
    cur.execute('SELECT id_usuario FROM usuario WHERE usuario = %s', (u,))
    row = cur.fetchone()
    if row:
        uid = row[0]
        cur.execute('DELETE FROM historial_usuario WHERE id_usuario = %s', (uid,))
        cur.execute('DELETE FROM login_log WHERE id_usuario = %s', (uid,))
        cur.execute('DELETE FROM login_intentos WHERE usuario = %s', (u,))
        cur.execute('DELETE FROM usuario WHERE id_usuario = %s', (uid,))
conn.commit()
```

## Frontend state (static/js/pages/ventas_crear.js)

All mutable state lives in a single object `ventaState` (declared once with `typeof` guard):

```javascript
ventaState.contadorArticulos   // int
ventaState.serviciosGlobales   // array
ventaState.negocioSeleccionado // string
ventaState.enProceso           // bool
```

Template files call JS functions directly via `oninput`/`onclick` — do not rename public functions without updating the Jinja templates.
