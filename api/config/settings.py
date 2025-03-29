import os
from pathlib import Path
from dotenv import load_dotenv

root = Path(__file__).parent.parent.parent
load_dotenv(root / ".env")

# Auth0 Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUTH0_CALLBACK_URL = os.getenv("AUTH0_CALLBACK_URL")

# Middleware Secret Key
MIDDLEWARE_SECRET_KEY = os.getenv("MIDDLEWARE_SECRET_KEY", "default-secret-key")

# Frontend URL para redirecionamentos
FRONTEND_URL = os.getenv("FRONTEND_URL", "")
API_URL = os.getenv("API_URL", "")

# CORS Settings
CORS_ORIGINS = [
    "http://localhost:5173",  # Local development
    "https://chatwithdocs-front.vercel.app",  # Production frontend
    os.getenv("FRONTEND_URL", ""),  # Dynamic frontend URL from env
]
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

# Configurações da aplicação
APP_NAME = "ChatWithDocs-API"
APP_VERSION = "1.0.0"

# AWS S3
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_REGION_NAME = os.getenv("S3_REGION_NAME")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", None)  # Para MinIO ou outro serviço compatível 

DATABASE_URL = os.getenv("DATABASE_URL")
