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

- `routes/`, `app.py` and `middleware/` import exclusively from `services/` — never directly from `models/`.
- Excel exports: the service builds and returns an `openpyxl.Workbook` (e.g. `exportar_gastos_excel_service`); the route only calls `send_excel(wb, nombre)` from `services/excel_helpers.py`.
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

Middleware in `middleware/auth_middleware.py` enforces session validity (the `session_token` in the cookie must match `usuario.session_token`) and per-role inactivity timeouts from `config.py` (`TIMEOUT_ADMIN` = 10 min, `TIMEOUT_CAJA` = 60 min). Caja users can only reach endpoints listed in `RUTAS_CAJA`; admin-only routes also carry `@admin_required`.

- Deactivating a user clears its `session_token`, which logs it out on the next request.
- PIN failures are counted per terminal (IP) under `CLAVE_PIN_TERMINAL`; a repeat lockout within 24 h lasts `BLOQUEO_REINCIDENTE_MIN_PIN`. Behind a reverse proxy set `TRUST_PROXY=1` so `remote_addr` is the real terminal IP.
- `logout` is POST-only (form in `base.html`).
- `historial_usuario` must never store `password_hash`, `pin_hash` or `session_token` — use `_snapshot_usuario()` in `services/usuarios_service.py`.

## Database

- Production DB: `freshstepsproduccion`
- Dates in SQL: never wrap an indexed column in `DATE()`; filter by range (`col >= %s AND col < DATE_ADD(%s, INTERVAL 1 DAY)`) and pass "today" from Python (`date.today()`), not `CURDATE()`. Python and MySQL (`DB_TIMEZONE`, default `-06:00`) must agree on the time zone.
- MySQL 8.0 does not support `CREATE INDEX IF NOT EXISTS`; for existing DBs use the `information_schema` pattern in `migrations/007_indices_faltantes.sql`.
- Test DB: `freshsteps` (configured in `scripts/.env.test`)
- Full schema: `migrations/001_schema_completo.sql` — apply to an empty DB with `mysql -u user -p freshsteps < migrations/001_schema_completo.sql`. It already contains every incremental migration; `002+` files are only for existing DBs (CI applies only `001`).

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

## Frontend state (static/js/pages/ventas_state.js)

All mutable state of the "crear venta" page lives in a single sealed object exported from `ventas_state.js`:

```javascript
ventaState.contadorArticulos   // int
ventaState.serviciosGlobales   // array
ventaState.negocioSeleccionado // string
ventaState.enProceso           // bool
```

The CSP is `script-src 'self'` with no `unsafe-inline`: templates must not use inline `<script>` or `on*=` handlers — wire events in the JS modules. Use `escapeHtml()` from `static/js/base/helpers.js` for any user data placed into `innerHTML` (it also escapes quotes, so it is safe inside attributes).

## Business rules enforced server-side

- A venta can only be delivered (`marcar_entregada`) when it is `lista`, not deleted and has no saldo pendiente; otherwise it must go through `registrar_pago_final_y_entregar`.
- Excel exports go through `xl_cell` / `texto_seguro` in `services/excel_helpers.py`, which neutralizes cell values starting with `= + - @` (formula injection).
