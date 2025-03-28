import os
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add API directory to path for importing settings
api_path = Path(__file__).parent.parent / "api"
sys.path.append(str(api_path.parent))

# Import the secrets management
from api.utils.secrets_manager import get_secrets
from api.config.settings import ENVIRONMENT, AWS_REGION

# Carregar variáveis de ambiente
load_dotenv()

# Load secrets in production
secrets = {}
if ENVIRONMENT == "production":
    secrets = get_secrets("prod/chat-with-docs", AWS_REGION)

# Configurações do Pinecone
PINECONE_API_KEY = secrets.get("PINECONE_API_KEY") or os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = secrets.get("PINECONE_ENVIRONMENT") or os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
PINECONE_INDEX_DIMENSIONS = 3072

# Configurações do OpenAI para embeddings
OPENAI_API_KEY = secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-large"

# Configurações de chunking
CHUNK_SIZE = 512
CHUNK_OVERLAP = 128
MAX_DOCUMENT_PAGES = 50
MAX_DOCUMENTS_PER_THREAD = 3
MAX_DOCUMENTS_PER_USER = 10

# Status de processamento
DOCUMENT_STATUS = {
    "PENDING": "pending",
    "PROCESSING": "processing", 
    "COMPLETED": "completed",
    "FAILED": "failed"
} 