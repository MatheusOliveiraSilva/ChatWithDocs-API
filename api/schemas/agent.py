from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel

class ModelConfig(BaseModel):
    model_id: str
    provider: str
    reasoning_effort: Optional[Literal["low", "medium", "high"]] = "low"
    think_mode: Optional[bool] = False
    temperature: Optional[float] = 0.7

class AgentRequest(BaseModel):
    thread_id: str
    message: str
    llm_config: ModelConfig

class AgentResponse(BaseModel):
    thread_id: str
    response: Dict[str, Any]
    updated_conversation: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None 