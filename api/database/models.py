from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
import datetime

from api.config.database import DATABASE_URL

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
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")

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
    documents = relationship("Document", back_populates="conversation", cascade="all, delete-orphan")
    
class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id = Column(String(255), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversation_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    s3_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)  # tamanho em bytes
    is_processed = Column(Boolean, default=False)
    index_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    doc_metadata = Column(JsonType, default={})
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="documents")
    conversation = relationship("ConversationThread", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    chunk_metadata = Column(JsonType, default={})  # página, posição, etc.
    vector_id = Column(String(255), nullable=True)  # ID no Pinecone
    
    document = relationship("Document", back_populates="chunks")

def init_db():
    Base.metadata.create_all(bind=engine) 