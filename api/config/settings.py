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

FRONTEND_URL = os.getenv("FRONTEND_URL")

# CORS Settings
CORS_ORIGINS = [FRONTEND_URL]  # Substitua por origens específicas em produção
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

APP_NAME = "ChatWithDocs-API"
APP_VERSION = "1.0.0"

# AWS S3
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_REGION_NAME = os.getenv("S3_REGION_NAME")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", None)