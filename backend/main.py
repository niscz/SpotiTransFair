from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from database import init_db
from routers import auth_routes as auth, dashboard, playlists, imports
from tenant import attach_tenant

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="SpotiTransFair", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include Routers (Blueprints)
app.include_router(dashboard.router)
app.include_router(auth.router)
app.include_router(playlists.router)
app.include_router(imports.router)

@app.middleware("http")
async def tenant_middleware(request, call_next):
    return await attach_tenant(request, call_next)
