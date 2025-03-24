import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage

from api.database.session import get_db
from api.database.models import User, ConversationThread
from api.utils.dependencies import get_current_user
from api.schemas.agent import AgentRequest, AgentResponse
from agent.graph import SimpleAssistantGraph

# Inicializar o grafo do agente
GRAPH = SimpleAssistantGraph()

router = APIRouter(prefix="/agent", tags=["Agent"])

@router.post("/chat", response_model=AgentResponse)
def invoke_agent(
    data: AgentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint para invocar o agente com configurações de modelo personalizadas
    """
    # Verificar se o usuário tem permissão para acessar este thread
    conversation = db.query(ConversationThread).filter(
        ConversationThread.user_id == user.id,
        ConversationThread.thread_id == data.thread_id
    ).first()
    
    # Se não encontrou conversa com esse thread_id
    if not conversation:
        # Criar uma nova conversa
        new_thread_name = f"Conversa {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
        conversation = ConversationThread(
            user_id=user.id,
            thread_id=data.thread_id,
            thread_name=new_thread_name,
            messages=[],
            created_at=datetime.datetime.utcnow(),
            last_used=datetime.datetime.utcnow()
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    # Inicializar o grafo
    agent = GRAPH.get_agent()
    
    # Preparar as mensagens para o agente
    messages = []
    for msg in conversation.messages:
        if msg[0] == "user":
            messages.append(HumanMessage(content=msg[1]))
        elif msg[0] == "assistant":
            messages.append(AIMessage(content=msg[1]))
    
    # Adicionar a mensagem atual
    messages.append(HumanMessage(content=data.message))
    
    try:
        # Invocar o agente com as configurações personalizadas
        # Convertendo para o formato esperado pelo ModelConfiguration
        model_config_data = {
            "model_id": data.llm_config.model_id,
            "provider": data.llm_config.provider,
            "reasoning_effort": data.llm_config.reasoning_effort,
            "think_mode": data.llm_config.think_mode,
            "temperature": data.llm_config.temperature
        }
        
        result = agent.invoke({
            "messages": messages,
            "llm_config": model_config_data
        }, 
        config={"configurable": {"thread_id": data.thread_id}}
        )
        
        # Atualizar a conversa no banco de dados
        updated_messages = conversation.messages.copy()
        # Adicionar a mensagem do usuário
        updated_messages.append(["user", data.message])
        # Adicionar a resposta do assistente
        if "messages" in result and result["messages"] and hasattr(result["messages"][-1], "content"):
            assistant_message = result["messages"][-1].content
            updated_messages.append(["assistant", assistant_message])
        
        # Atualizar no banco de dados
        conversation.messages = updated_messages
        conversation.last_used = datetime.datetime.utcnow()
        db.commit()
        
        return {
            "thread_id": data.thread_id,
            "response": result,
            "updated_conversation": {
                "id": conversation.id,
                "thread_id": conversation.thread_id,
                "messages": conversation.messages,
                "last_used": conversation.last_used
            }
        }
    
    except Exception as e:
        # Em caso de erro, ainda registramos a mensagem do usuário
        updated_messages = conversation.messages.copy()
        updated_messages.append(["user", data.message])
        conversation.messages = updated_messages
        db.commit()
        
        # Retornar o erro para debugging
        return {
            "thread_id": data.thread_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "response": {},
            "conversation": {
                "id": conversation.id,
                "thread_id": conversation.thread_id,
                "messages": conversation.messages
            }
        } 