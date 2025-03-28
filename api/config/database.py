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

# Função para obter o endpoint do RDS
def get_rds_endpoint():
    """
    Conecta ao AWS RDS para obter o endpoint do banco de dados.
    Se você já conhece o endpoint fixo, pode substituir esta função 
    por uma variável constante.
    """
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