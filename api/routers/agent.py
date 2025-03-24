import datetime
import json
from typing import List, Dict, Any, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel

from api.database.session import get_db
from api.database.models import User, ConversationThread
from api.utils.dependencies import get_current_user
from agent.graph import SimpleAssistantGraph

# Inicializar o grafo do agente
GRAPH = SimpleAssistantGraph()

router = APIRouter(prefix="/agent", tags=["Agent"])

# Classes para as requisições
class ModelConfig(BaseModel):
    model_id: str = "gpt-4o"
    provider: str = "openai"
    reasoning_effort: Optional[Literal["low", "medium", "high"]] = "low"
    think_mode: Optional[bool] = False
    temperature: Optional[float] = 0.7

class MessageRequest(BaseModel):
    input: str
    thread_id: Optional[str] = None
    previous_messages: Optional[List[List[str]]] = None
    llm_config: Optional[ModelConfig] = None

@router.post("/chat/query_stream")
def query_stream(
    request: MessageRequest,
    user: User = Depends(get_current_user)
):
    """
    Endpoint simplificado para streaming de mensagens.
    Recebe a mensagem do usuário e o histórico da conversa, e envia a resposta em chunks.
    O frontend é responsável por salvar o histórico completo.
    """
    # Inicializar o agente
    agent = GRAPH.get_agent()
    
    # Preparar as mensagens para o LLM
    messages = []
    
    # Adicionar histórico se fornecido
    if request.previous_messages:
        for msg in request.previous_messages:
            if msg[0] == "user":
                messages.append(HumanMessage(content=msg[1]))
            elif msg[0] == "assistant":
                messages.append(AIMessage(content=msg[1]))
    
    # Adicionar a mensagem atual
    messages.append(HumanMessage(content=request.input))
    
    # Configurar o LLM
    llm_config = {}
    if request.llm_config:
        llm_config = {
            "model_id": request.llm_config.model_id,
            "provider": request.llm_config.provider,
            "reasoning_effort": request.llm_config.reasoning_effort,
            "think_mode": request.llm_config.think_mode,
            "temperature": request.llm_config.temperature
        }
    
    # Configuração para o streaming
    config = {
        "thread_id": request.thread_id or f"temp_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
    }
    
    # Função geradora para streaming
    def event_generator():
        try:
            # Stream direto do LangGraph
            for chunk, meta in agent.stream(
                {"messages": messages, "llm_config": llm_config}, 
                stream_mode="messages", 
                config={"configurable": config}
            ):
                # Extrair conteúdo e enviar como SSE
                if hasattr(chunk, "content"):
                    content = chunk.content
                    
                    # Formato de Server-Sent Events
                    payload = {"content": content, "meta": meta}
                    yield f"data: {json.dumps(payload)}\n\n"
                    
        except Exception as e:
            # Em caso de erro durante o streaming
            error_payload = {"error": str(e), "error_type": type(e).__name__}
            yield f"data: {json.dumps(error_payload)}\n\n"
    
    # Retornar StreamingResponse
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )