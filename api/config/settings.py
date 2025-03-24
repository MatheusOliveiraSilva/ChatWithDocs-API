import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
root = Path(__file__).parent.parent.parent  # Vai para o diretório raiz do projeto
load_dotenv(root / ".env")

# Auth0 Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUTH0_CALLBACK_URL = os.getenv("AUTH0_CALLBACK_URL")

# Middleware Secret Key
MIDDLEWARE_SECRET_KEY = os.getenv("MIDDLEWARE_SECRET_KEY", "default-secret-key")

# CORS Settings
CORS_ORIGINS = ["*"]  # Substitua por origens específicas em produção
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

# Frontend URL para redirecionamentos
FRONTEND_URL = os.getenv("FRONTEND_URL", "")

# Configurações da aplicação
APP_NAME = "ChatWithDocs-API"
APP_VERSION = "1.0.0" 