from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from sqlalchemy import UniqueConstraint

class Provider(str, Enum):
    SPOTIFY = "spotify"
    TIDAL = "tidal"
    YTM = "ytm"

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_REVIEW = "waiting_review"
    IMPORTING = "importing"
    DONE = "done"
    FAILED = "failed"

class ItemStatus(str, Enum):
    MATCHED = "matched"
    UNCERTAIN = "uncertain"
    NOT_FOUND = "not_found"
    SKIPPED = "skipped"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)

    connections: List["Connection"] = Relationship(back_populates="user")
    jobs: List["ImportJob"] = Relationship(back_populates="user")

class Connection(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "provider", name="unique_user_provider"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    provider: Provider
    credentials: Dict[str, Any] = Field(sa_column=Column(JSON))

    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="connections")

class ImportJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_playlist_id: str
    source_playlist_name: Optional[str] = None
    target_provider: Provider
    status: JobStatus = Field(default=JobStatus.QUEUED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    target_playlist_id: Optional[str] = None

    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="jobs")
    items: List["ImportItem"] = Relationship(back_populates="job")

class ImportItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    original_track_data: Dict[str, Any] = Field(sa_column=Column(JSON))
    match_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    status: ItemStatus = Field(default=ItemStatus.NOT_FOUND)
    selected_match_id: Optional[str] = None

    job_id: int = Field(foreign_key="importjob.id")
    job: ImportJob = Relationship(back_populates="items")
