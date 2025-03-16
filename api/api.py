import os
import uuid
import datetime
from typing import List, Tuple
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends, Response, Request
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from api.models import (
    User, UserSession, ConversationThread, SessionLocal, init_db
)


load_dotenv(dotenv_path=".env")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("MIDDLEWARE_SECRET_KEY", "default-secret-key"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------------------------------------------------
# 1) Login and Session Management Endpoints (Simplified)
# -------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str

@app.post("/auth/login-simple")
def login_simple(login_data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Simple login endpoint that creates a session for a username without password verification"""
    
    username = login_data.username
    # Create a placeholder sub (normally provided by Auth0)
    sub = f"local|{username}"
    
    # Check if user exists
    user = db.query(User).filter(User.name == username).first()
    
    # Create user if not exists
    if not user:
        user = User(
            email=f"{username}@example.com",  # Placeholder email
            sub=sub,
            name=username,
            picture=None  # No picture for simple login
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Create session
    session_token = str(uuid.uuid4())
    new_session = UserSession(session_id=session_token, user_id=user.id)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    # Return session token
    return {
        "session_token": session_token,
        "user": {
            "id": user.id,
            "name": user.name
        }
    }

@app.get("/status")
def check_status():
    """
    Simple endpoint to check if the API is running.
    Returns basic status information about the API.
    """
    return {
        "status": "online",
        "service": "adaptative-rag-api",
        "version": "1.0.0",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }


# Keep Auth0 endpoints for backward compatibility
@app.get("/auth/login")
async def auth_login(request: Request):
    # This endpoint is kept for backward compatibility
    return {"message": "Auth0 login is deprecated. Use /auth/login-simple instead"}

@app.get("/auth/callback")
async def auth_callback(request: Request):
    # This endpoint is kept for backward compatibility
    return {"message": "Auth0 login is deprecated. Use /auth/login-simple instead"}

@app.get("/test/set-cookie")
def set_cookie_test(response: Response):
    test_value = "local|teste123"
    response.set_cookie(
        key="sub",
        value=test_value,
        max_age=30 * 24 * 3600,
        httponly=False,
        samesite="lax",
        secure=False,
        domain="localhost",
        path="/"
    )
    return {"message": f"Cookie 'sub' set to {test_value}"}

# -------------------------------------------------------------------
# 2) BaseModels to chat history creation
# -------------------------------------------------------------------
class ConversationCreate(BaseModel):
    session_id: str
    thread_id: str
    thread_name: str
    first_message_role: str = "user"
    first_message_content: str

class ConversationUpdate(BaseModel):
    thread_id: str
    # We defined that "messages" is a list of lists [role, content],
    messages: List[List[str]]

# -------------------------------------------------------------------
# 3) Session Creating/Updating Endpoints
# -------------------------------------------------------------------
@app.post("/session")
def create_session(response: Response, db: Session = Depends(get_db)):
    session_token = str(uuid.uuid4())
    new_session = UserSession(session_id=session_token)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    response.set_cookie(key="session_token", value=session_token)
    return {"session_id": session_token, "created_at": new_session.created_at}

@app.get("/session")
def get_session(session_token: str, db: Session = Depends(get_db)):
    session_obj = db.query(UserSession).filter(UserSession.session_id == session_token).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_obj.session_id,
        "user_id": session_obj.user_id,
        "created_at": session_obj.created_at
    }

# -------------------------------------------------------------------
# 4) Chat Creating/Updating Endpoints
# -------------------------------------------------------------------
def validate_session(session_id: str, db: Session):
    """Helper function to validate if a session exists"""
    session = db.query(UserSession).filter(UserSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Invalid session. Please login again.")
    return session

@app.post("/conversation")
def add_conversation(data: ConversationCreate, db: Session = Depends(get_db)):
    """
    Create a new conversation thread in the database and save the first message.
    """
    # Validate the session
    validate_session(data.session_id, db)
    
    initial_messages = [(data.first_message_role, data.first_message_content)]

    new_conv = ConversationThread(
        session_id=data.session_id,
        thread_id=data.thread_id,
        thread_name=data.thread_name,
        messages=initial_messages,
        created_at=datetime.datetime.utcnow(),
        last_used=datetime.datetime.utcnow()
    )
    db.add(new_conv)
    db.commit()
    db.refresh(new_conv)
    return {
        "id": new_conv.id,
        "session_id": new_conv.session_id,
        "thread_id": new_conv.thread_id,
        "thread_name": new_conv.thread_name,
        "messages": new_conv.messages,
        "created_at": new_conv.created_at,
        "last_used": new_conv.last_used
    }

@app.patch("/conversation")
def update_conversation(data: ConversationUpdate, db: Session = Depends(get_db)):
    """
    Update chat history in database with the new messages.
    """
    conversation = db.query(ConversationThread).filter(
        ConversationThread.thread_id == data.thread_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    # Validar a existência da sessão associada à conversa
    validate_session(conversation.session_id, db)

    conversation.messages = data.messages
    conversation.last_used = datetime.datetime.utcnow()

    db.commit()
    db.refresh(conversation)
    return {
        "id": conversation.id,
        "thread_id": conversation.thread_id,
        "thread_name": conversation.thread_name,
        "messages": conversation.messages,
        "session_id": conversation.session_id,
        "created_at": conversation.created_at,
        "last_used": conversation.last_used
    }

@app.get("/conversation")
def get_conversations(session_token: str, db: Session = Depends(get_db)):
    convs = db.query(ConversationThread).filter(
        ConversationThread.session_id == session_token
    ).order_by(ConversationThread.created_at.desc()).all()

    return {
        "conversations": [
            {
                "id": conv.id,
                "session_id": conv.session_id,
                "thread_id": conv.thread_id,
                "thread_name": conv.thread_name,
                "messages": conv.messages,
                "created_at": conv.created_at,
                "last_used": conv.last_used
            }
            for conv in convs
        ]
    }


