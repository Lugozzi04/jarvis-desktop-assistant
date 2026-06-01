"""SQLAlchemy database models for JARVIS.

Tables: settings, skills, apps, workflows, automations, logs, memory, etc.
Uses SQLite for MVP; designed to be swappable to PostgreSQL later.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)


class Base(DeclarativeBase):
    __allow_unmapped__ = True


# ── Settings ──

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(255), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Setting {self.key}={self.value}>"


# ── Skills ──

class SkillRecord(Base):
    __tablename__ = "skills"

    name = Column(String(100), primary_key=True)
    display_name = Column(String(200))
    version = Column(String(20), default="0.1.0")
    enabled = Column(Boolean, default=True)
    config_json = Column(Text, default="{}")
    installed_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Skill {self.name} enabled={self.enabled}>"

    @property
    def config(self) -> dict:
        return json.loads(self.config_json or "{}")

    @config.setter
    def config(self, value: dict) -> None:
        self.config_json = json.dumps(value)


# ── Apps (configured desktop applications) ──

class AppConfig(Base):
    __tablename__ = "apps"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    aliases_json: Mapped[str] = mapped_column(Text, default="[]")
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    app_type: Mapped[str] = mapped_column(String(50), default="desktop_app")
    icon: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    aliases_rel: Mapped[list["AppAlias"]] = relationship("AppAlias", back_populates="app", cascade="all, delete-orphan")

    @property
    def aliases(self) -> list[str]:
        return json.loads(self.aliases_json or "[]")

    @aliases.setter
    def aliases(self, value: list[str]) -> None:
        self.aliases_json = json.dumps(value)


class AppAlias(Base):
    __tablename__ = "app_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    app_name = Column(String(200), ForeignKey("apps.name"), nullable=False)
    alias = Column(String(200), unique=True, nullable=False)

    app = relationship("AppConfig", back_populates="aliases_rel")


# ── Workflows ──

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), unique=True, nullable=False)
    description = Column(Text, default="")
    mode = Column(String(50), default="normal")
    steps_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def steps(self) -> list[dict]:
        return json.loads(self.steps_json or "[]")

    @steps.setter
    def steps(self, value: list[dict]) -> None:
        self.steps_json = json.dumps(value)


# ── Automations ──

class AutomationRecord(Base):
    __tablename__ = "automations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), unique=True, nullable=False)
    description = Column(Text, default="")
    enabled = Column(Boolean, default=True)
    trigger_type = Column(String(100), nullable=False)
    trigger_config_json = Column(Text, default="{}")
    condition_type = Column(String(100), default="always")
    condition_config_json = Column(Text, default="{}")
    actions_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def trigger_config(self) -> dict:
        return json.loads(self.trigger_config_json)

    @property
    def condition_config(self) -> dict:
        return json.loads(self.condition_config_json)

    @property
    def actions(self) -> list[dict]:
        return json.loads(self.actions_json)


# ── Audit Log ──

class AuditLog(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    input_raw = Column(Text, default="")
    intent_kind = Column(String(50))
    skill = Column(String(100), nullable=True)
    action = Column(String(100), nullable=True)
    parameters_json = Column(Text, default="{}")
    risk = Column(String(20), default="safe")
    confirmation_required = Column(Boolean, default=False)
    confirmation_granted = Column(Boolean, nullable=True)
    result_success = Column(Boolean, nullable=True)
    result_summary = Column(Text, default="")
    error = Column(Text, nullable=True)
    duration_ms = Column(Float, default=0.0)


# ── Memory / Habit Learning ──

class HabitEvent(Base):
    __tablename__ = "habit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String(100), nullable=False)
    data_json = Column(Text, default="{}")
    session_id = Column(String(100), default="default")

    @property
    def data(self) -> dict:
        return json.loads(self.data_json)


class HabitSuggestion(Base):
    __tablename__ = "habit_suggestions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    title = Column(String(300))
    description = Column(Text)
    pattern_type = Column(String(100))
    confidence = Column(Float, default=0.5)
    status = Column(String(50), default="pending")  # pending, approved, rejected
    suggested_automation_json = Column(Text, nullable=True)


# ── Engine & Session Factory ──

_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine(database_url: str | None = None):
    """Create or return the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        url = database_url or "sqlite:///data/jarvis.db"
        connect_args = {"check_same_thread": False} if "sqlite" in url else {}
        _engine = create_engine(url, connect_args=connect_args, echo=False)
    return _engine


def get_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    """Create or return the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine(database_url)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def init_db(database_url: str | None = None) -> None:
    """Create all tables."""
    engine = get_engine(database_url)
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """Dependency injection — get a DB session."""
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
