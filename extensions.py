import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# La app corre en un solo proceso (app.run / waitress), así que los contadores en
# memoria son correctos. Si se usan varios procesos (gunicorn -w N), definir
# RATELIMIT_STORAGE_URI=redis://... para que compartan los límites.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
)
