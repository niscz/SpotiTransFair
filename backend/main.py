from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import init_db
from routers import auth, dashboard, playlists, imports
from tenant import attach_tenant

app = FastAPI(title="SpotiTransFair")

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

@app.on_event("startup")
def on_startup():
    init_db()
