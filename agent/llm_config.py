from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
from pathlib import Path
import os
import sys
from typing import Literal

# Add paths for importing
current_dir = Path(__file__).parent
root_dir = current_dir.parent
sys.path.append(str(root_dir))

# Import secrets management
from api.utils.secrets_manager import get_secrets
from api.config.settings import ENVIRONMENT, AWS_REGION

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Load secrets in production
secrets = {}
if ENVIRONMENT == "production":
    secrets = get_secrets("prod/chat-with-docs", AWS_REGION)

# Get API keys with secrets fallback
OPENAI_API_KEY = secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

DEFAULT_TEMPERATURE = 0.7
DEFAULT_THINK_MODE = True
DEFAULT_REASONING_EFFORT = "low"

class ModelConfig:
    def __init__(self):
        pass
 
    @staticmethod
    def get_llm(model_id: str, provider: str, reasoning_effort: Literal["low", "medium", "high"] = DEFAULT_REASONING_EFFORT, think_mode: bool = DEFAULT_THINK_MODE, temperature: float = DEFAULT_TEMPERATURE):
        if provider == "openai":
            return ModelConfig.get_openai_llm(model_id, reasoning_effort, temperature)
        elif provider == "anthropic":
            return ModelConfig.get_anthropic_llm(model_id, think_mode, temperature)
        else:
            raise ValueError(f"Provider {provider} not supported")

    @staticmethod
    def get_openai_llm(model_id: str, reasoning_effort: Literal["low", "medium", "high"] = DEFAULT_REASONING_EFFORT, temperature: float = DEFAULT_TEMPERATURE):
        if model_id == "o3-mini":
            return ChatOpenAI(model="o3-mini-2025-01-31", temperature=1, reasoning_effort=reasoning_effort, api_key=OPENAI_API_KEY)
        elif model_id == "o1":
            return ChatOpenAI(model="o1-2024-12-17", temperature=1, reasoning_effort=reasoning_effort, api_key=OPENAI_API_KEY)
        elif model_id == "gpt-4o":
            return ChatOpenAI(model="gpt-4o-2024-08-06", temperature=temperature, api_key=OPENAI_API_KEY)
        elif model_id == "gpt-4o-mini":
            return ChatOpenAI(model="gpt-4o-mini-2024-07-18", temperature=temperature, api_key=OPENAI_API_KEY)
        else:
            raise ValueError(f"Model {model_id} not supported")

    @staticmethod
    def get_anthropic_llm(model_id: str, think_mode: bool = DEFAULT_THINK_MODE, temperature: float = DEFAULT_TEMPERATURE):
        think_param = "enable" if think_mode else "disable"
        if model_id == "claude-3-opus":
            return ChatAnthropic(model="claude-3-opus-20240229", temperature=temperature, anthropic_api_key=ANTHROPIC_API_KEY, thinking=think_param)
        elif model_id == "claude-3-sonnet":
            return ChatAnthropic(model="claude-3-sonnet-20240229", temperature=temperature, anthropic_api_key=ANTHROPIC_API_KEY, thinking=think_param)
        elif model_id == "claude-3-haiku":
            return ChatAnthropic(model="claude-3-haiku-20240307", temperature=temperature, anthropic_api_key=ANTHROPIC_API_KEY, thinking=think_param)
        else:
            raise ValueError(f"Model {model_id} not supported")
