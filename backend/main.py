from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from database import init_db, engine
from models import User
from routers import auth, dashboard, playlists, imports

app = FastAPI(title="SpotiTransFair")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include Routers (Blueprints)
app.include_router(dashboard.router)
app.include_router(auth.router)
app.include_router(playlists.router)
app.include_router(imports.router)

@app.on_event("startup")
def on_startup():
    init_db()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == "admin")).first()
        if not user:
            user = User(username="admin")
            session.add(user)
            session.commit()
