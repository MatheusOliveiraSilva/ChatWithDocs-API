import datetime
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

from api.config.settings import MIDDLEWARE_SECRET_KEY, CORS_ORIGINS, CORS_METHODS, CORS_HEADERS, APP_NAME, APP_VERSION
from api.database.models import init_db
from api.routers import auth, conversation, agent

# Inicializar aplicação FastAPI
app = FastAPI(
    title=APP_NAME,
    description="API for the ChatWithDocs system, enabling authentication, conversation management, and interaction with AI agents.",
    version=APP_VERSION
)

# Adicionar middleware de sessão
app.add_middleware(
    SessionMiddleware, 
    secret_key=MIDDLEWARE_SECRET_KEY
)

# Adicionar middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
)

# Inicializar banco de dados
init_db()

# Registrar routers
app.include_router(auth.router)
app.include_router(conversation.router)
app.include_router(agent.router)

@app.get("/status")
def check_status():
    """
    Endpoint simples para verificar se a API está funcionando.
    Retorna informações básicas de status sobre a API.
    """
    return {
        "status": "online",
        "service": APP_NAME,
        "version": APP_VERSION,
        "timestamp": datetime.datetime.utcnow().isoformat()
    } 