from sqlmodel import SQLModel, create_engine, Session
import os
from pathlib import Path

# Resolve the absolute path to the backend directory
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_URL = f"sqlite:///{BASE_DIR}/spotitransfair.db"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

def get_session():
    with Session(engine) as session:
        yield session

def init_db():
    SQLModel.metadata.create_all(engine)
