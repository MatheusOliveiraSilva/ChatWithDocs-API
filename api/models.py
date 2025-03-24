from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
import datetime
import os
from dotenv import load_dotenv
from pathlib import Path

from api.db_config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Determinar qual tipo de JSON usar com base no DATABASE_URL
if DATABASE_URL and DATABASE_URL.startswith('postgresql'):
    JsonType = JSONB
else:
    JsonType = JSON

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    sub = Column(String(255), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    name = Column(String(255), nullable=True)
    picture = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime, default=datetime.datetime.utcnow)
    
    conversations = relationship("ConversationThread", back_populates="user", cascade="all, delete-orphan")

class ConversationThread(Base):
    __tablename__ = "conversation_threads"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id = Column(String(255), nullable=False)
    thread_name = Column(String(255), nullable=False)
    messages = Column(JsonType, default=[])
    # model_id = Column(String(50), default="gpt-4o")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_used = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="conversations")

def init_db():
    Base.metadata.create_all(bind=engine)
