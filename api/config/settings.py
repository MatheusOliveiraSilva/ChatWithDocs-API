import os
from pathlib import Path
from dotenv import load_dotenv

root = Path(__file__).parent.parent.parent
load_dotenv(root / ".env")

# Auth0 Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")

# Middleware Secret Key
MIDDLEWARE_SECRET_KEY = os.getenv("MIDDLEWARE_SECRET_KEY", "default-secret-key")

<<<<<<< HEAD
FRONTEND_URL = os.getenv("FRONTEND_URL")
=======
FRONTEND_URL = os.getenv("FRONTEND_URL", "")
>>>>>>> development

# CORS Settings
CORS_ORIGINS = [FRONTEND_URL]  # Substitua por origens específicas em produção
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

<<<<<<< HEAD
=======
# Configurações da aplicação
>>>>>>> development
APP_NAME = "ChatWithDocs-API"
APP_VERSION = "1.0.0"

# AWS S3
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_REGION_NAME = os.getenv("S3_REGION_NAME")
<<<<<<< HEAD
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", None)

# URL da API para callbacks externos
API_URL = os.getenv("API_URL", "http://chatmemoryapi-alb-258270582.us-east-1.elb.amazonaws.com")
# Garantir que a URL da API não termine com barra
if API_URL and API_URL.endswith("/"):
    API_URL = API_URL[:-1]

# Configurações de provedores de AI
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configurações Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
=======
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", None)  # Para MinIO ou outro serviço compatível 

DATABASE_URL = os.getenv("DATABASE_URL")
API_URL = os.getenv("API_URL")
>>>>>>> development
