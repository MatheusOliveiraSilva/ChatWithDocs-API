import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from api.utils.secrets_manager import get_secrets

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carrega as variáveis de ambiente
root = Path(__file__).parent.parent.parent  # Vai para o diretório raiz do projeto
load_dotenv(root / ".env")

# Obtém as credenciais AWS dos secrets do GitHub Actions
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Try to load secrets from AWS Secrets Manager in production
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
secrets = {}

if ENVIRONMENT == "production":
    # In production, use secrets manager
    logger.info(f"Ambiente de produção detectado, tentando carregar secrets de AWS Secrets Manager")
    try:
        secrets = get_secrets("prod/chat-with-docs", AWS_REGION)
        if not secrets:
            logger.warning("Não foi possível obter segredos do AWS Secrets Manager. Usando variáveis de ambiente como fallback.")
    except Exception as e:
        logger.error(f"Erro ao carregar segredos: {str(e)}")
        logger.warning("Usando variáveis de ambiente como fallback...")
else:
    logger.info(f"Ambiente de desenvolvimento detectado, usando variáveis de ambiente")

# Auth0 Configuration
AUTH0_DOMAIN = secrets.get("AUTH0_DOMAIN") or os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = secrets.get("AUTH0_CLIENT_ID") or os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = secrets.get("AUTH0_CLIENT_SECRET") or os.getenv("AUTH0_CLIENT_SECRET")
AUTH0_CALLBACK_URL = secrets.get("AUTH0_CALLBACK_URL") or os.getenv("AUTH0_CALLBACK_URL")

# Middleware Secret Key
MIDDLEWARE_SECRET_KEY = secrets.get("MIDDLEWARE_SECRET_KEY") or os.getenv("MIDDLEWARE_SECRET_KEY", "default-secret-key")

# CORS Settings
CORS_ORIGINS = ["http://localhost:5173"]  # Substitua por origens específicas em produção
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

# Frontend URL para redirecionamentos
FRONTEND_URL = secrets.get("FRONTEND_URL") or os.getenv("FRONTEND_URL", "")

# Configurações da aplicação
APP_NAME = "ChatWithDocs-API"
APP_VERSION = "1.0.0"

# Configurações do S3
S3_BUCKET_NAME = secrets.get("S3_BUCKET_NAME") or os.getenv("S3_BUCKET_NAME")
S3_ACCESS_KEY = secrets.get("S3_ACCESS_KEY") or os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = secrets.get("S3_SECRET_KEY") or os.getenv("S3_SECRET_KEY")
S3_REGION_NAME = secrets.get("S3_REGION") or os.getenv("S3_REGION")
S3_ENDPOINT_URL = secrets.get("S3_ENDPOINT_URL") or os.getenv("S3_ENDPOINT_URL", None)

# Provider API Keys
OPENAI_API_KEY = secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

# Pinecone settings
PINECONE_API_KEY = secrets.get("PINECONE_API_KEY") or os.getenv("PINECONE_API_KEY")

# Log configurações importantes
if not PINECONE_API_KEY:
    logger.warning("PINECONE_API_KEY não encontrada! Isso pode causar erros em funções que dependem do Pinecone.")
    
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY não encontrada! Isso pode causar erros em funções que dependem da OpenAI.") 