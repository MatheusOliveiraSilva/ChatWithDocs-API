import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database.session import get_db
from api.database.models import User, ConversationThread
from api.utils.dependencies import get_current_user
from api.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationResponse

router = APIRouter(prefix="/conversation", tags=["Conversations"])

@router.post("", response_model=ConversationResponse)
def add_conversation(
    data: ConversationCreate, 
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cria uma nova conversa para o usuário autenticado.
    """
    initial_messages = [(data.first_message_role, data.first_message_content)]

    new_conv = ConversationThread(
        user_id=user.id,
        thread_id=data.thread_id,
        thread_name=data.thread_name,
        messages=initial_messages,
        created_at=datetime.datetime.utcnow(),
        last_used=datetime.datetime.utcnow()
    )
    db.add(new_conv)
    db.commit()
    db.refresh(new_conv)
    return {
        "id": new_conv.id,
        "user_id": new_conv.user_id,
        "thread_id": new_conv.thread_id,
        "thread_name": new_conv.thread_name,
        "messages": new_conv.messages,
        "created_at": new_conv.created_at,
        "last_used": new_conv.last_used
    }

@router.patch("", response_model=ConversationResponse)
def update_conversation(
    data: ConversationUpdate, 
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Atualiza a conversa do usuário autenticado.
    """
    conversation = db.query(ConversationThread).filter(
        ConversationThread.user_id == user.id,
        ConversationThread.thread_id == data.thread_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    conversation.messages = data.messages
    conversation.last_used = datetime.datetime.utcnow()

    db.commit()
    db.refresh(conversation)
    return {
        "id": conversation.id,
        "thread_id": conversation.thread_id,
        "thread_name": conversation.thread_name,
        "messages": conversation.messages,
        "user_id": conversation.user_id,
        "created_at": conversation.created_at,
        "last_used": conversation.last_used
    }

@router.get("")
def get_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Recupera todas as conversas para o usuário autenticado.
    """
    convs = db.query(ConversationThread).filter(
        ConversationThread.user_id == user.id
    ).order_by(ConversationThread.created_at.desc()).all()

    return {
        "conversations": [
            {
                "id": conv.id,
                "user_id": conv.user_id,
                "thread_id": conv.thread_id,
                "thread_name": conv.thread_name,
                "messages": conv.messages,
                "created_at": conv.created_at,
                "last_used": conv.last_used
            }
            for conv in convs
        ]
    }

@router.get("/{thread_id}", response_model=ConversationResponse)
def get_conversation(
    thread_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Recupera uma conversa específica para o usuário autenticado.
    """
    conversation = db.query(ConversationThread).filter(
        ConversationThread.user_id == user.id,
        ConversationThread.thread_id == thread_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
        
    return {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "thread_id": conversation.thread_id,
        "thread_name": conversation.thread_name,
        "messages": conversation.messages,
        "created_at": conversation.created_at,
        "last_used": conversation.last_used
    }

@router.delete("/{thread_id}")
def delete_conversation(
    thread_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deleta uma conversa específica para o usuário autenticado.
    """
    conversation = db.query(ConversationThread).filter(
        ConversationThread.user_id == user.id,
        ConversationThread.thread_id == thread_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    # Deletar a conversa
    db.delete(conversation)
    db.commit()
    
    return {"message": "Conversa deletada com sucesso"} 