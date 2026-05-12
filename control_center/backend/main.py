# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/main.py
#
# FastAPI application entry point for Stylo Control Center.
#
# Startup:
#   The lifespan context manager runs create_tables() once when the server
#   starts — creates any missing DB tables using SQLAlchemy metadata.
#
# Routers mounted:
#   /api/servers    — Server CRUD + SSH health check
#   /api/sites      — Site CRUD + per-site detail, logs
#   /api/clients    — Client CRUD
#   /api/licenses   — User license issue / revoke / renew / delete
#   /api/deploy/*   — Provision / update / suspend / resume / terminate via SSH
#   /api/lbalancer  — Traefik config generation + SSH push
#   /api/sync       — Endpoint called by stylo_core benches for user sync
#   /api/alerts     — Alert config + test-send
#
# Inline endpoints:
#   POST /api/auth/login — returns a JWT for the admin UI
#   GET  /health         — simple liveness probe for Docker health checks
#
# CORS is open (*) — restrict to the frontend origin in production.
# ─────────────────────────────────────────────────────────────────────────────
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import LoginRequest, TokenResponse, create_access_token
from config import settings
from database import create_tables
from routers import alerts, clients, deploy, lbalancer, licenses, servers, sites, sync


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(title="Stylo Control Center", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(servers.router)
app.include_router(sites.router)
app.include_router(clients.router)
app.include_router(licenses.router)
app.include_router(deploy.router)
app.include_router(lbalancer.router)
app.include_router(sync.router)
app.include_router(alerts.router)


@app.post("/api/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(body: LoginRequest):
    from fastapi import HTTPException

    # In production, load admin credentials from DB or env vars
    admin_user = settings.secret_key  # reuse or add dedicated admin_user setting
    if body.username != "admin" or body.password != "stylo-admin":
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(body.username)
    return TokenResponse(access_token=token)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
