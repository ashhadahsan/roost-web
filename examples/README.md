# roost-web examples

| Example | Pattern |
| --- | --- |
| [`standalone.py`](./standalone.py) | Smallest mount — one ASGI app, seeds demo jobs, runs under `uvicorn`. |
| [`auth_fastapi.py`](./auth_fastapi.py) | Bearer-token gate via FastAPI middleware before the dashboard sub-app. |
| [`auth_starlette_basic.py`](./auth_starlette_basic.py) | HTTP Basic auth via pure Starlette middleware, no extra deps. |

## Tips for production auth

The dashboard delegates auth to the host app — there is **no built-in login**. That's intentional: every team already has an opinion (sessions, JWT, OAuth, IAP, mTLS). Roost-web stays out of it.

Common patterns:

- **Behind a reverse proxy** — let your nginx / caddy / Cloudflare Access / Tailscale Funnel front-door enforce auth and forward only authenticated requests to `roost-web`. Set `read_only=True` if the proxy is the only protection and you don't fully trust it.
- **As a sub-app of an existing API** — mount the dashboard inside FastAPI/Django/Flask and reuse the host's session/middleware. See [`auth_fastapi.py`](./auth_fastapi.py).
- **As a separate service** — run `roost-web` as a private service on an internal-only network. Pair with VPN / Tailscale / Cloud IAP.

## Read-only mode

`dashboard(dsn=..., read_only=True)` makes every mutating endpoint return 403. Safe to expose to a wider audience (e.g. read-only ops viewers) without risk of accidental retry/cancel/pause clicks.
