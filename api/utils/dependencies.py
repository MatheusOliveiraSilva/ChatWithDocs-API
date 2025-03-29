from typing import Optional
from fastapi import Header, Cookie, HTTPException, status, Depends
from sqlalchemy.orm import Session
import requests
from jose import jwt, JWTError
import datetime

from api.database.session import get_db
from api.database.models import User
from api.config.settings import AUTH0_DOMAIN, MIDDLEWARE_SECRET_KEY

def get_auth0_user_info(access_token: str):
    """Get user info from Auth0 using the access token"""
    userinfo_url = f"https://{AUTH0_DOMAIN}/userinfo"
    response = requests.get(
        userinfo_url,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    response.raise_for_status()
    return response.json()

def get_current_user(
    authorization: Optional[str] = Header(None),
    user_id: Optional[int] = Cookie(None),
    user_email: Optional[str] = Cookie(None),
    auth_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Verifica se o usuário está autenticado por token de autorização,
    user_id ou user_email nos cookies
    """
    # Primeiro, tentar verificar o token JWT no header de autorização
    if authorization:
        try:
            # Verificar bearer token
            scheme, token = authorization.split()
            if scheme.lower() != 'bearer':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token de autorização inválido"
                )
            
            # Decodificar e validar o token JWT
            try:
                payload = jwt.decode(token, MIDDLEWARE_SECRET_KEY, algorithms=["HS256"])
                user_id_from_token = int(payload.get("sub"))
                
                # Verificar se o token não expirou
                exp = payload.get("exp")
                if exp and datetime.datetime.fromtimestamp(exp) < datetime.datetime.utcnow():
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token expirado"
                    )
                
                # Buscar o usuário pelo ID do token
                user = db.query(User).filter(User.id == user_id_from_token).first()
                if user:
                    return user
            except JWTError:
                # Se falhar na decodificação JWT, tentar outras abordagens
                pass
                
            # Tentativa de fallback para compatibilidade: pode ser o ID direto
            try:
                user_id_legacy = int(token)
                user = db.query(User).filter(User.id == user_id_legacy).first()
                if user:
                    return user
            except (ValueError, TypeError):
                pass
                
            # Ou pode ser um email
            user = db.query(User).filter(User.email == token).first()
            if user:
                return user
        except Exception:
            # Se ocorrer qualquer erro na análise, continuar para outras verificações
            pass
    
    # Verificar o token JWT no cookie
    if auth_token:
        try:
            payload = jwt.decode(auth_token, MIDDLEWARE_SECRET_KEY, algorithms=["HS256"])
            user_id_from_cookie = int(payload.get("sub"))
            
            # Verificar se o token não expirou
            exp = payload.get("exp")
            if exp and datetime.datetime.fromtimestamp(exp) < datetime.datetime.utcnow():
                pass  # Token expirado, continuar para outras verificações
            else:
                # Buscar o usuário pelo ID do token
                user = db.query(User).filter(User.id == user_id_from_cookie).first()
                if user:
                    return user
        except JWTError:
            # Se falhar na decodificação JWT, continuar para outras verificações
            pass
    
    # Verificar cookies tradicionais como fallback
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