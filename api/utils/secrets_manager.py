import boto3
import json
from typing import Dict, Any, Optional


def get_secrets(secret_name: str, region_name: Optional[str] = "us-east-1") -> Dict[str, Any]:
    """
    Retrieve secrets from AWS Secrets Manager.
    
    Args:
        secret_name: Name of the secret in AWS Secrets Manager
        region_name: AWS region where the secret is stored
        
    Returns:
        Dictionary containing the secret key-value pairs
    """
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        # Get the secret value
        response = client.get_secret_value(SecretId=secret_name)
        
        # Parse the secret JSON string
        if 'SecretString' in response:
            return json.loads(response['SecretString'])
        else:
            # Binary secrets are not supported in this implementation
            raise ValueError("Binary secrets are not supported")
            
    except Exception as e:
        print(f"Error retrieving secret '{secret_name}': {str(e)}")
        return {} 