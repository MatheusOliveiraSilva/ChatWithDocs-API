import os
import boto3
from dotenv import load_dotenv
from pathlib import Path
from api.utils.secrets_manager import get_secrets
from api.config.settings import ENVIRONMENT, AWS_REGION

# Carrega as variáveis de ambiente
root = Path(__file__).parent.parent.parent  # Vai para o diretório raiz do projeto
load_dotenv(root / ".env")

# Load secrets in production
secrets = {}
if ENVIRONMENT == "production":
    secrets = get_secrets("prod/chat-with-docs", AWS_REGION)

# Configurações AWS
AWS_ACCESS_KEY_ID = secrets.get("AWS_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = secrets.get("AWS_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = secrets.get("AWS_REGION") or os.getenv("AWS_REGION", "us-east-1")

# Configurações do banco de dados
DB_USER = secrets.get("POSTGRES_USER") or os.getenv("POSTGRES_USER")
DB_PASSWORD = secrets.get("POSTGRES_PASSWORD") or os.getenv("POSTGRES_PASSWORD")
DB_NAME = secrets.get("POSTGRES_DB") or os.getenv("POSTGRES_DB")
DB_HOST = secrets.get("DB_HOST")  # Podem ser definidos diretamente no Secret Manager

# Função para obter o endpoint do RDS
def get_rds_endpoint():
    """
    Conecta ao AWS RDS para obter o endpoint do banco de dados.
    Se você já conhece o endpoint fixo, pode substituir esta função 
    por uma variável constante.
    """
    # Se o host está definido nos secrets, use-o
    if DB_HOST:
        return DB_HOST
        
    try:
        # Cria um cliente RDS usando boto3
        rds_client = boto3.client(
            'rds',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        
        # Lista todas as instâncias RDS
        # Você pode filtrar pela instância específica se tiver várias
        response = rds_client.describe_db_instances()
        
        # Pega o primeiro endpoint disponível
        # Idealmente, você identificaria sua instância específica pelo nome
        for instance in response['DBInstances']:
            if instance['DBName'] == DB_NAME:
                return instance['Endpoint']['Address']
        
        # Se não encontrar pela correspondência exata de nome, pega o primeiro
        if response['DBInstances']:
            return response['DBInstances'][0]['Endpoint']['Address']
        
        raise Exception("Nenhuma instância RDS encontrada")
    
    except Exception as e:
        print(f"Erro ao obter endpoint RDS: {str(e)}")
        # Fallback para banco local em caso de erro
        return "localhost"

# Função para construir a DATABASE_URL
def get_database_url():
    """
    Constrói a URL de conexão com o banco de dados.
    Tenta primeiro conectar ao RDS, e se falhar, usa o banco local.
    """
    # Se a DATABASE_URL completa está definida nos secrets, use-a
    if secrets.get("DATABASE_URL"):
        return secrets.get("DATABASE_URL")
        
    # Obter o endpoint RDS
    try:
        host = get_rds_endpoint()
        # Construir a URL completa para o PostgreSQL
        return f"postgresql://{DB_USER}:{DB_PASSWORD}@{host}:5432/{DB_NAME}"
    except:
        # Em caso de erro, usa a URL local
        return os.getenv("DATABASE_URL", "postgresql://matheus:password@localhost/users_chat_history")

# Variável para ser importada por outros módulos
DATABASE_URL = get_database_url() 