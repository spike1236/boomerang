import os
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import dotenv
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
import hashlib
import secrets

dotenv.load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

engine = sa.create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AccountModel(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    email = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    tasks = relationship("TaskCreateModel", back_populates="account")


class TaskCreateModel(Base):
    __tablename__ = "task_creates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    input_text = Column(Text, nullable=False)
    task_type = Column(String)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    account = relationship("AccountModel", back_populates="tasks")
    response = relationship("TaskResponseModel", back_populates="task", uselist=False)


class TaskResponseModel(Base):
    __tablename__ = "task_responses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("task_creates.id"), unique=True)
    status = Column(String, default="pending")
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    task = relationship("TaskCreateModel", back_populates="response")


def hash_password(password: str) -> str:
    """Hash a password for storing."""
    salt = secrets.token_hex(8)
    pwdhash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
    )
    return f"{salt}${pwdhash.hex()}"


def init_db():
    """Create all tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


# Run init_db when this module is imported
init_db()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
