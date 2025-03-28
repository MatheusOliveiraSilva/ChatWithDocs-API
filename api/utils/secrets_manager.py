import boto3
import json
import os
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError


def get_secrets(secret_name: str, region_name: Optional[str] = "us-east-1") -> Dict[str, Any]:
    """
    Retrieve secrets from AWS Secrets Manager.
    
    Args:
        secret_name: Name of the secret in AWS Secrets Manager
        region_name: AWS region where the secret is stored
        
    Returns:
        Dictionary containing the secret key-value pairs
    """
    try:
        # Verificar se estamos rodando no ECS com task role
        if os.environ.get("ECS_CONTAINER_METADATA_URI"):
            print("Detectado ambiente ECS, usando task role")
    
        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        
        # Get the secret value
        response = client.get_secret_value(SecretId=secret_name)
        
        # Parse the secret JSON string
        if 'SecretString' in response:
            return json.loads(response['SecretString'])
        else:
            # Binary secrets are not supported in this implementation
            print("Aviso: Segredo binário encontrado, não suportado")
            return {}
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        print(f"Erro ao acessar AWS Secrets Manager: {error_code}")
        if error_code == 'AccessDeniedException':
            print("Permissão negada ao acessar segredo. Verifique se a task role tem permissão secretsmanager:GetSecretValue")
        elif error_code == 'ResourceNotFoundException':
            print(f"Segredo '{secret_name}' não encontrado na região {region_name}")
        return {}
    except Exception as e:
        print(f"Error retrieving secret '{secret_name}': {str(e)}")
        return {} 