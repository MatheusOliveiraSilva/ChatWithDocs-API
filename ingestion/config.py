import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurações do Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
PINECONE_INDEX_DIMENSIONS = 3072

# Configurações do OpenAI para embeddings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
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