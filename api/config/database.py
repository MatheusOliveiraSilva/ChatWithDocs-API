import os
import boto3
from dotenv import load_dotenv
from pathlib import Path

# Carrega as variáveis de ambiente
root = Path(__file__).parent.parent.parent  # Vai para o diretório raiz do projeto
load_dotenv(root / ".env")

# Configurações AWS
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Configurações do banco de dados
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")

# Variável para ser importada por outros módulos
# Usa diretamente a variável de ambiente DATABASE_URL ao invés de tentar descobrir o endpoint
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://matheus:password@localhost/users_chat_history") 