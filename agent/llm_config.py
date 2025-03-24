from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
from pathlib import Path
from typing import Literal

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DEFAULT_TEMPERATURE = 0.7
DEFAULT_THINK_MODE = False
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
            return ChatOpenAI(model="o3-mini-2025-01-31", temperature=1, reasoning_effort=reasoning_effort)
        elif model_id == "o1":
            return ChatOpenAI(model="o1-2024-12-17", temperature=1, reasoning_effort=reasoning_effort)
        elif model_id == "gpt-4o":
            return ChatOpenAI(model="gpt-4o-2024-08-06", temperature=temperature)
        elif model_id == "gpt-4o-mini":
            return ChatOpenAI(model="gpt-4o-mini-2024-07-18", temperature=temperature)
        else:
            raise ValueError(f"Model {model_id} not supported")

    @staticmethod
    def get_anthropic_llm(model_id: str, think_mode: bool = DEFAULT_THINK_MODE, temperature: float = DEFAULT_TEMPERATURE):
        if model_id == "claude-3-7-sonnet":
            return ChatAnthropic(model="claude-3-7-sonnet-latest", temperature=1, think_mode=think_mode)  
        elif model_id == "claude-3-5-haiku":
            return ChatAnthropic(model="claude-3-5-haiku-20241022", temperature=temperature)
        elif model_id == "claude-3-5-sonnet":
            return ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=temperature)
        else:#
            raise ValueError(f"Model {model_id} not supported")
