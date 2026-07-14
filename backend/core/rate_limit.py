"""Shared slowapi Limiter instance.

Lives in its own module (not main.py or endpoints.py) because both of those
need it: main.py registers it on app.state and wires the 429 exception
handler, endpoints.py applies it to individual routes via @limiter.limit(...).
Defining it in either of those two would create a circular import - main.py
already imports the router from endpoints.py.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Keys by client IP (request.client.host). Behind a reverse proxy (e.g. the
# Caddy setup in docker-compose.prod.yml), this only sees the proxy's IP
# unless uvicorn is run with --proxy-headers so Starlette rewrites
# request.client from X-Forwarded-For - without that, every client behind
# the proxy shares one bucket and the limit becomes effectively global
# rather than per-IP. Worth fixing before this is actually deployed behind
# Caddy; out of scope for this change since it touches the Dockerfile/CMD,
# not main.py/endpoints.py.
limiter = Limiter(key_func=get_remote_address)
