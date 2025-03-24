from typing import Optional
from fastapi import Header, Cookie, HTTPException, status, Depends
from sqlalchemy.orm import Session
import requests

from api.database.session import get_db
from api.database.models import User
from api.config.settings import AUTH0_DOMAIN

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
    db: Session = Depends(get_db)
):
    """
    Verifica se o usuário está autenticado por token de autorização,
    user_id ou user_email nos cookies
    """
    if authorization:
        # Verificar bearer token (implementação simplificada)
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autorização inválido"
            )
        
        # Aqui você poderia validar o token JWT Auth0
        # por simplicidade, estamos assumindo que é um user_id
        try:
            user_id = int(token)
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return user
        except:
            pass
            
        # Se não for um user_id, talvez seja um email
        user = db.query(User).filter(User.email == token).first()
        if user:
            return user
            
    # Verificar cookies
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