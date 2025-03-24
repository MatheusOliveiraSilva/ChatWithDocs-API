import os
import uuid
import datetime
import json
from typing import List, Tuple, Optional, Dict, Any, Literal
from pydantic import BaseModel, EmailStr
from fastapi import FastAPI, HTTPException, Depends, Response, Request, status, Header, Cookie, Form, File, UploadFile
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
from agent.graph import SimpleAssistantGraph
from agent.states import ModelConfiguration
from langchain_core.messages import HumanMessage, AIMessage

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

GRAPH = SimpleAssistantGraph()

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
    Verifies if the user is authenticated by an authorization token,
    user_id or user_email in cookies
    """
    if authorization:
        # Verify bearer token (simplified implementation)
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization token"
            )
        
        # Here you could validate the Auth0 JWT token
        # for simplicity, we're assuming it's a user_id
        try:
            user_id = int(token)
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return user
        except:
            pass
            
        # If it's not a user_id, maybe it's an email
        user = db.query(User).filter(User.email == token).first()
        if user:
            return user
            
    # Check cookies
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
        detail="Not authenticated"
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
    """Simplified login with username and optionally email"""
    
    username = login_data.username
    email = login_data.email or f"{username}@example.com"
    
    # Create a placeholder sub (normally provided by Auth0)
    sub = f"local|{username}"
    
    # Search for user by email
    user = db.query(User).filter(User.email == email).first()
    
    # Create user if it doesn't exist
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
        # Update last login
        user.last_login = datetime.datetime.utcnow()
        db.commit()
    
    # Set cookies for authentication
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
    
    # Return user information
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }

@app.get("/auth/login")
async def auth_login(redirect_uri: Optional[str] = None, prompt: Optional[str] = None, 
                    force_login: Optional[bool] = None, ui_locales: Optional[str] = None):
    """
    Endpoint that redirects to the Auth0 login page
    """
    # Store the redirect_uri in the query params to be used later in the callback
    callback_url = AUTH0_CALLBACK_URL
    if redirect_uri:
        callback_url = f"{AUTH0_CALLBACK_URL}?redirect_uri={redirect_uri}"
    
    # Construir URL com parâmetros adicionais se fornecidos
    auth_url = (
        f"https://{AUTH0_DOMAIN}/authorize"
        f"?response_type=code"
        f"&client_id={AUTH0_CLIENT_ID}"
        f"&redirect_uri={callback_url}"
        f"&scope=openid profile email"
    )
    
    # Adicionar parâmetros opcionais
    if prompt:
        auth_url += f"&prompt={prompt}"
    if force_login:
        auth_url += f"&force_login=true"
    if ui_locales:
        auth_url += f"&ui_locales={ui_locales}"
    
    return RedirectResponse(auth_url)

@app.get("/auth/callback")
async def auth_callback(
    request: Request, 
    code: str, 
    redirect_uri: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Callback handler to process the Auth0 authorization code and create session
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
            detail="Authentication failed with Auth0"
        )
    
    token_data = token_response.json()
    
    # Get user info from Auth0
    try:
        userinfo = get_auth0_user_info(token_data["access_token"])
    except requests.RequestException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to get user information"
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
    # Use the provided redirect_uri if available, otherwise fall back to environment variable
    frontend_url = redirect_uri or os.getenv("FRONTEND_URL", "")
    
    # Generate a JWT token
    token = str(user.id)  # Simplificado para este exemplo
    
    # For SPA applications, it's better to redirect to a callback URL and include the token as a query parameter
    response = RedirectResponse(url=f"{frontend_url}?token={token}")
    
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
    Endpoint to exchange the authorization code for tokens and create a session
    (Alternative implementation for SPAs that don't use redirection)
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
            detail="Authentication failed with Auth0"
        )
    
    token_data = token_response.json()
    
    # Get user info from Auth0
    try:
        userinfo = get_auth0_user_info(token_data["access_token"])
    except requests.RequestException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to get user information"
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
    """Endpoint to logout by clearing cookies"""
    response.delete_cookie("user_id")
    response.delete_cookie("user_email")
    
    return {"message": "Logout successful"}

@app.get("/auth/me")
async def get_user_info(user: User = Depends(get_current_user)):
    """Endpoint to get authenticated user information"""
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
    Creates a new conversation for the authenticated user.
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
    Updates the conversation of the authenticated user.
    """
    conversation = db.query(ConversationThread).filter(
        ConversationThread.user_id == user.id,
        ConversationThread.thread_id == data.thread_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

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
    Retrieves all conversations for the authenticated user.
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
    Retrieves a specific conversation for the authenticated user.
    """
    conversation = db.query(ConversationThread).filter(
        ConversationThread.user_id == user.id,
        ConversationThread.thread_id == thread_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    return {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "thread_id": conversation.thread_id,
        "thread_name": conversation.thread_name,
        "messages": conversation.messages,
        "created_at": conversation.created_at,
        "last_used": conversation.last_used
    }

@app.delete("/conversation/{thread_id}")
def delete_conversation(
    thread_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes a specific conversation for the authenticated user.
    """
    conversation = db.query(ConversationThread).filter(
        ConversationThread.user_id == user.id,
        ConversationThread.thread_id == thread_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Delete the conversation
    db.delete(conversation)
    db.commit()
    
    return {"message": "Conversation deleted successfully"}


# -------------------------------------------------------------------
# 4) Agent Endpoints
# -------------------------------------------------------------------
class ModelConfig(BaseModel):
    model_id: str
    provider: str
    reasoning_effort: Optional[Literal["low", "medium", "high"]] = "low"
    think_mode: Optional[bool] = False
    temperature: Optional[float] = 0.7

class AgentRequest(BaseModel):
    thread_id: str
    message: str
    llm_config: ModelConfig

@app.post("/agent/chat")
def invoke_agent(
    data: AgentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint para invocar o agente com configurações de modelo personalizadas
    """
    # Verificar se o usuário tem permissão para acessar este thread
    conversation = db.query(ConversationThread).filter(
        ConversationThread.user_id == user.id,
        ConversationThread.thread_id == data.thread_id
    ).first()
    
    # Se não encontrou conversa com esse thread_id
    if not conversation:
        # Criar uma nova conversa
        new_thread_name = f"Conversa {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
        conversation = ConversationThread(
            user_id=user.id,
            thread_id=data.thread_id,
            thread_name=new_thread_name,
            messages=[],
            created_at=datetime.datetime.utcnow(),
            last_used=datetime.datetime.utcnow()
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    # Inicializar o grafo
    agent = GRAPH.get_agent()
    
    # Preparar as mensagens para o agente
    messages = []
    for msg in conversation.messages:
        if msg[0] == "user":
            messages.append(HumanMessage(content=msg[1]))
        elif msg[0] == "assistant":
            messages.append(AIMessage(content=msg[1]))
    
    # Adicionar a mensagem atual
    messages.append(HumanMessage(content=data.message))
    
    try:
        # Invocar o agente com as configurações personalizadas
        # Convertendo para o formato esperado pelo ModelConfiguration
        model_config_data = {
            "model_id": data.llm_config.model_id,
            "provider": data.llm_config.provider,
            "reasoning_effort": data.llm_config.reasoning_effort,
            "think_mode": data.llm_config.think_mode,
            "temperature": data.llm_config.temperature
        }
        
        result = agent.invoke({
            "messages": messages,
            "llm_config": model_config_data
        }, 
        config={"configurable": {"thread_id": data.thread_id}}
        )
        
        # Atualizar a conversa no banco de dados
        updated_messages = conversation.messages.copy()
        # Adicionar a mensagem do usuário
        updated_messages.append(["user", data.message])
        # Adicionar a resposta do assistente
        if "messages" in result and result["messages"] and hasattr(result["messages"][-1], "content"):
            assistant_message = result["messages"][-1].content
            updated_messages.append(["assistant", assistant_message])
        
        # Atualizar no banco de dados
        conversation.messages = updated_messages
        conversation.last_used = datetime.datetime.utcnow()
        db.commit()
        
        return {
            "thread_id": data.thread_id,
            "response": result,
            "updated_conversation": {
                "id": conversation.id,
                "thread_id": conversation.thread_id,
                "messages": conversation.messages,
                "last_used": conversation.last_used
            }
        }
    
    except Exception as e:
        # Em caso de erro, ainda registramos a mensagem do usuário
        updated_messages = conversation.messages.copy()
        updated_messages.append(["user", data.message])
        conversation.messages = updated_messages
        db.commit()
        
        # Retornar o erro para debugging
        return {
            "thread_id": data.thread_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "conversation": {
                "id": conversation.id,
                "thread_id": conversation.thread_id,
                "messages": conversation.messages
            }
        }
