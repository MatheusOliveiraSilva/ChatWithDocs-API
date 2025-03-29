import os
import datetime
import requests
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status, Cookie
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from jose import jwt
 
from api.database.session import get_db
from api.database.models import User
from api.schemas.auth import LoginRequest, Auth0TokenRequest, UserResponse
from api.utils.dependencies import get_current_user, get_auth0_user_info
from api.config.settings import (
    AUTH0_DOMAIN, 
    AUTH0_CLIENT_ID, 
    AUTH0_CLIENT_SECRET,
    AUTH0_CALLBACK_URL,
    FRONTEND_URL,
    API_URL
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login-simple")
def login_simple(login_data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Login simplificado com username e opcionalmente email"""
    
    username = login_data.username
    email = login_data.email or f"{username}@example.com"
    
    # Criar um placeholder sub (normalmente fornecido pelo Auth0)
    sub = f"local|{username}"
    
    # Buscar usuário pelo email
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

@router.get("/login")
async def auth_login(redirect_uri: str = None, prompt: str = None, 
                    force_login: bool = None, ui_locales: str = None):
    """
    Endpoint que redireciona para a página de login do Auth0
    """
    # Use a API URL como callback básico se AUTH0_CALLBACK_URL não estiver definido
    base_callback_url = AUTH0_CALLBACK_URL or f"{API_URL}/auth/callback"
    
    # Armazenar o redirect_uri como um state parameter em vez de alterar o callback_url
    auth_url = (
        f"https://{AUTH0_DOMAIN}/authorize"
        f"?response_type=code"
        f"&client_id={AUTH0_CLIENT_ID}"
        f"&redirect_uri={base_callback_url}"
        f"&scope=openid profile email"
    )
    
    # Se redirect_uri estiver presente, adicione como um parâmetro state
    # Importante: Não substituir o state, mas usar ele para redirecionar depois
    if redirect_uri:
        # Use redirect_uri como state para redirecionar depois da autenticação
        auth_url += f"&state={redirect_uri}"
    else:
        # Se não fornecido, use o FRONTEND_URL default como state
        auth_url += f"&state={FRONTEND_URL}"
    
    # Adicionar parâmetros opcionais
    if prompt:
        auth_url += f"&prompt={prompt}"
    if force_login:
        auth_url += f"&force_login=true"
    if ui_locales:
        auth_url += f"&ui_locales={ui_locales}"
    
    return RedirectResponse(auth_url)

@router.get("/callback")
async def auth_callback(
    request: Request, 
    code: str,
    state: str = None,
    db: Session = Depends(get_db)
):
    """
    Callback handler para processar o código de autorização Auth0 e criar sessão
    """
    # Não redefinir variáveis importadas
    callback_url = AUTH0_CALLBACK_URL or f"{API_URL}/auth/callback"
    
    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
    token_payload = {
        "grant_type": "authorization_code",
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "code": code,
        "redirect_uri": callback_url
    }

    token_response = requests.post(token_url, json=token_payload)
    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação falhou com Auth0"
        )
    
    token_data = token_response.json()
    
    # Obter informações do usuário do Auth0
    try:
        userinfo = get_auth0_user_info(token_data["access_token"])
    except requests.RequestException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falha ao obter informações do usuário"
        )
    
    # Extrair dados do usuário
    sub = userinfo.get("sub")
    email = userinfo.get("email")
    name = userinfo.get("name")
    picture = userinfo.get("picture")
    
    # Encontrar ou criar usuário
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
        # Atualizar informações do usuário e último login
        user.sub = sub
        user.name = name
        user.picture = picture
        user.last_login = datetime.datetime.utcnow()
        db.commit()
    
    # Usar o state como redirect_uri, se disponível, caso contrário, usar a variável de ambiente
    frontend_url = state or FRONTEND_URL
    
    # Criar um token JWT mais seguro para autenticação cruzada de domínios
    from datetime import timedelta
    from jose import jwt
    
    # Criar um token JWT com informações do usuário que expira em 7 dias
    jwt_payload = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "exp": datetime.datetime.utcnow() + timedelta(days=7)
    }
    
    # Usar o secret key do middleware para assinar o token
    from api.config.settings import MIDDLEWARE_SECRET_KEY
    jwt_token = jwt.encode(jwt_payload, MIDDLEWARE_SECRET_KEY, algorithm="HS256")
    
    # Para aplicações SPA, redirecionar para a página principal com o token JWT
    # Incluir todos os dados necessários nos parâmetros de consulta para acessibilidade cross-domain
    response = RedirectResponse(
        url=f"{frontend_url}?token={jwt_token}&user_id={user.id}&user_email={email}&user_name={name}"
    )
    
    # Definir cookies também, mas ciente que em produção com domínios diferentes, 
    # eles podem não funcionar devido a restrições de segurança do navegador
    response.set_cookie(
        key="user_id",
        value=str(user.id),
        httponly=True,
        secure=True,  # Requer HTTPS
        samesite="lax"
    )
    
    response.set_cookie(
        key="user_email",
        value=user.email,
        httponly=True,
        secure=True,  # Requer HTTPS
        samesite="lax"
    )
    
    # Adicionar o token JWT também como cookie
    response.set_cookie(
        key="auth_token",
        value=jwt_token,
        httponly=True,
        secure=True,  # Requer HTTPS
        samesite="lax"
    )
    
    return response

@router.post("/token")
async def auth_token(
    token_request: Auth0TokenRequest, 
    db: Session = Depends(get_db)
):
    """
    Endpoint para trocar o código de autorização por tokens e criar uma sessão
    (Implementação alternativa para SPAs que não usam redirecionamento)
    """
    callback_url = AUTH0_CALLBACK_URL or f"{API_URL}/auth/callback"
    
    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
    token_payload = {
        "grant_type": "authorization_code",
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "code": token_request.code,
        "redirect_uri": callback_url
    }

    token_response = requests.post(token_url, json=token_payload)
    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação falhou com Auth0"
        )
    
    token_data = token_response.json()
    
    # Obter informações do usuário do Auth0
    try:
        userinfo = get_auth0_user_info(token_data["access_token"])
    except requests.RequestException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falha ao obter informações do usuário"
        )
    
    # Extrair dados do usuário
    sub = userinfo.get("sub")
    email = userinfo.get("email")
    name = userinfo.get("name")
    picture = userinfo.get("picture")
    
    # Encontrar ou criar usuário
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
        # Atualizar informações do usuário e último login
        user.sub = sub
        user.name = name
        user.picture = picture
        user.last_login = datetime.datetime.utcnow()
        db.commit()
    
    # Criar um token JWT com informações do usuário que expira em 7 dias
    from datetime import timedelta
    from jose import jwt
    
    jwt_payload = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "exp": datetime.datetime.utcnow() + timedelta(days=7)
    }
    
    # Usar o secret key do middleware para assinar o token
    from api.config.settings import MIDDLEWARE_SECRET_KEY
    jwt_token = jwt.encode(jwt_payload, MIDDLEWARE_SECRET_KEY, algorithm="HS256")
    
    # Retornar dados do usuário, tokens do Auth0 e o JWT personalizado
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "picture": user.picture
        },
        "auth0_tokens": token_data,
        "jwt_token": jwt_token
    }

@router.get("/logout")
async def logout(response: Response):
    """Endpoint para logout limpando cookies"""
    response.delete_cookie("user_id")
    response.delete_cookie("user_email")
    
    return {"message": "Logout realizado com sucesso"}

@router.get("/me", response_model=UserResponse)
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