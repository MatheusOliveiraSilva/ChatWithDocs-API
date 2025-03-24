import os
import uuid
import datetime
import json
from typing import List, Tuple, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from fastapi import FastAPI, HTTPException, Depends, Response, Request, status, Header, Cookie
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
import requests
from jose import jwt
from api.models import (
    User, ConversationThread, SessionLocal, init_db
)

load_dotenv(dotenv_path=".env")

# Auth0 Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUTH0_CALLBACK_URL = os.getenv("AUTH0_CALLBACK_URL")

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
# Auth0 Helper Functions
# -------------------------------------------------------------------
def get_auth0_user_info(access_token: str) -> Dict[str, Any]:
    """Get user info from Auth0 using the access token"""
    userinfo_url = f"https://{AUTH0_DOMAIN}/userinfo"
    response = requests.get(
        userinfo_url,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    response.raise_for_status()
    return response.json()

# -------------------------------------------------------------------
# Auth & User Functions
# -------------------------------------------------------------------
def get_current_user(
    authorization: Optional[str] = Header(None),
    user_id: Optional[int] = Cookie(None),
    user_email: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Verifica se o usuário está autenticado por um token de autorização,
    user_id ou user_email em cookies
    """
    if authorization:
        # Verifica bearer token (implementação simplificada)
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autorização inválido"
            )
        
        # Aqui você poderia validar o token JWT do Auth0
        # por simplicidade, estamos assumindo que é um user_id
        try:
            user_id = int(token)
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return user
        except:
            pass
            
        # Se não é um user_id, talvez seja um email
        user = db.query(User).filter(User.email == token).first()
        if user:
            return user
            
    # Verifica cookies
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user
            
    if user_email:
        user = db.query(User).filter(User.email == user_email).first()
        if user:
            return user
            
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado"
    )

# -------------------------------------------------------------------
# 1) Login and Authentication Endpoints
# -------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    email: Optional[EmailStr] = None

class Auth0TokenRequest(BaseModel):
    code: str
    redirect_uri: str

class Auth0TokenResponse(BaseModel):
    access_token: str
    id_token: str
    token_type: str
    expires_in: int

@app.post("/auth/login-simple")
def login_simple(login_data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Login simplificado com nome de usuário e opcionalmente email"""
    
    username = login_data.username
    email = login_data.email or f"{username}@example.com"
    
    # Create a placeholder sub (normally provided by Auth0)
    sub = f"local|{username}"
    
    # Procurar usuário pelo email
    user = db.query(User).filter(User.email == email).first()
    
    # Criar usuário se não existir
    if not user:
        user = User(
            sub=sub,
            email=email,
            name=username,
            picture=None,
            created_at=datetime.datetime.utcnow(),
            last_login=datetime.datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Atualizar último login
        user.last_login = datetime.datetime.utcnow()
        db.commit()
    
    # Definir cookies para autenticação
    response.set_cookie(
        key="user_id",
        value=str(user.id),
        httponly=True,
        secure=True,
        samesite="lax"
    )
    
    response.set_cookie(
        key="user_email",
        value=user.email,
        httponly=True,
        secure=True,
        samesite="lax"
    )
    
    # Retornar informações do usuário
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }

@app.get("/auth/login")
async def auth_login():
    """
    Endpoint que redireciona para a página de login do Auth0
    """
    return RedirectResponse(
        f"https://{AUTH0_DOMAIN}/authorize"
        f"?response_type=code"
        f"&client_id={AUTH0_CLIENT_ID}"
        f"&redirect_uri={AUTH0_CALLBACK_URL}"
        f"&scope=openid profile email"
    )

@app.get("/auth/callback")
async def auth_callback(request: Request, code: str, db: Session = Depends(get_db)):
    """
    Callback handler para processar o código de autorização do Auth0 e criar sessão
    """
    # Exchange authorization code for tokens
    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
    token_payload = {
        "grant_type": "authorization_code",
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "code": code,
        "redirect_uri": AUTH0_CALLBACK_URL
    }

    token_response = requests.post(token_url, json=token_payload)
    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falha na autenticação com Auth0"
        )
    
    token_data = token_response.json()
    
    # Get user info from Auth0
    try:
        userinfo = get_auth0_user_info(token_data["access_token"])
    except requests.RequestException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falha ao obter informações do usuário"
        )
    
    # Extract user data
    sub = userinfo.get("sub")
    email = userinfo.get("email")
    name = userinfo.get("name")
    picture = userinfo.get("picture")
    
    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            sub=sub,
            email=email,
            name=name,
            picture=picture,
            created_at=datetime.datetime.utcnow(),
            last_login=datetime.datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update user info and last login
        user.sub = sub
        user.name = name
        user.picture = picture
        user.last_login = datetime.datetime.utcnow()
        db.commit()
    
    # Set cookies for authentication
    frontend_url = os.getenv("FRONTEND_URL", "/")
    response = RedirectResponse(url=f"{frontend_url}?user_id={user.id}")
    
    response.set_cookie(
        key="user_id",
        value=str(user.id),
        httponly=True,
        secure=True,
        samesite="lax"
    )
    
    response.set_cookie(
        key="user_email",
        value=user.email,
        httponly=True,
        secure=True,
        samesite="lax"
    )
    
    return response

@app.post("/auth/token")
async def auth_token(
    token_request: Auth0TokenRequest, 
    db: Session = Depends(get_db)
):
    """
    Endpoint para trocar o código de autorização por tokens e criar uma sessão
    (Implementação alternativa para SPAs que não usam redirecionamento)
    """
    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
    token_payload = {
        "grant_type": "authorization_code",
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "code": token_request.code,
        "redirect_uri": token_request.redirect_uri
    }

    token_response = requests.post(token_url, json=token_payload)
    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falha na autenticação com Auth0"
        )
    
    token_data = token_response.json()
    
    # Get user info from Auth0
    try:
        userinfo = get_auth0_user_info(token_data["access_token"])
    except requests.RequestException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falha ao obter informações do usuário"
        )
    
    # Extract user data
    sub = userinfo.get("sub")
    email = userinfo.get("email")
    name = userinfo.get("name")
    picture = userinfo.get("picture")
    
    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            sub=sub,
            email=email,
            name=name,
            picture=picture,
            created_at=datetime.datetime.utcnow(),
            last_login=datetime.datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update user info and last login
        user.sub = sub
        user.name = name
        user.picture = picture
        user.last_login = datetime.datetime.utcnow()
        db.commit()
    
    # Return user data and tokens
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "picture": user.picture
        },
        "auth0_tokens": token_data
    }

@app.get("/auth/logout")
async def logout(response: Response):
    """Endpoint para fazer logout limpando os cookies"""
    response.delete_cookie("user_id")
    response.delete_cookie("user_email")
    
    return {"message": "Logout bem sucedido"}

@app.get("/auth/me")
async def get_user_info(user: User = Depends(get_current_user)):
    """Endpoint para obter informações do usuário autenticado"""
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "picture": user.picture,
        "created_at": user.created_at,
        "last_login": user.last_login
    }

@app.get("/status")
def check_status():
    """
    Simple endpoint to check if the API is running.
    Returns basic status information about the API.
    """

    return {
        "status": "online",
        "service": "chatbot-api",
        "version": "1.0.0",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

# -------------------------------------------------------------------
# 2) BaseModels to chat history creation
# -------------------------------------------------------------------
class ConversationCreate(BaseModel):
    thread_id: str
    thread_name: str
    first_message_role: str = "user"
    first_message_content: str

class ConversationUpdate(BaseModel):
    thread_id: str
    # We defined that "messages" is a list of lists [role, content],
    messages: List[List[str]]

# -------------------------------------------------------------------
# 3) Conversation Endpoints
# -------------------------------------------------------------------
@app.post("/conversation")
def add_conversation(
    data: ConversationCreate, 
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cria uma nova conversa para o usuário autenticado.
    """
    initial_messages = [(data.first_message_role, data.first_message_content)]

    new_conv = ConversationThread(
        user_id=user.id,
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
        "user_id": new_conv.user_id,
        "thread_id": new_conv.thread_id,
        "thread_name": new_conv.thread_name,
        "messages": new_conv.messages,
        "created_at": new_conv.created_at,
        "last_used": new_conv.last_used
    }

@app.patch("/conversation")
def update_conversation(
    data: ConversationUpdate, 
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Atualiza a conversa do usuário autenticado.
    """
    conversation = db.query(ConversationThread).filter(
        ConversationThread.user_id == user.id,
        ConversationThread.thread_id == data.thread_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    conversation.messages = data.messages
    conversation.last_used = datetime.datetime.utcnow()

    db.commit()
    db.refresh(conversation)
    return {
        "id": conversation.id,
        "thread_id": conversation.thread_id,
        "thread_name": conversation.thread_name,
        "messages": conversation.messages,
        "user_id": conversation.user_id,
        "created_at": conversation.created_at,
        "last_used": conversation.last_used
    }

@app.get("/conversation")
def get_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Recupera todas as conversas do usuário autenticado.
    """
    convs = db.query(ConversationThread).filter(
        ConversationThread.user_id == user.id
    ).order_by(ConversationThread.created_at.desc()).all()

    return {
        "conversations": [
            {
                "id": conv.id,
                "user_id": conv.user_id,
                "thread_id": conv.thread_id,
                "thread_name": conv.thread_name,
                "messages": conv.messages,
                "created_at": conv.created_at,
                "last_used": conv.last_used
            }
            for conv in convs
        ]
    }

@app.get("/conversation/{thread_id}")
def get_conversation(
    thread_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Recupera uma conversa específica do usuário autenticado.
    """
    conversation = db.query(ConversationThread).filter(
        ConversationThread.user_id == user.id,
        ConversationThread.thread_id == thread_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
        
    return {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "thread_id": conversation.thread_id,
        "thread_name": conversation.thread_name,
        "messages": conversation.messages,
        "created_at": conversation.created_at,
        "last_used": conversation.last_used
    }
