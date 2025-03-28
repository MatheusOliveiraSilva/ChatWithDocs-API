import datetime
import logging
import boto3
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database.session import get_db
from api.database.models import User, ConversationThread, Document
from api.utils.dependencies import get_current_user
from api.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationResponse
from api.config.settings import S3_BUCKET_NAME, S3_ACCESS_KEY, S3_SECRET_KEY, S3_REGION_NAME, S3_ENDPOINT_URL
from ingestion.pinecone_indexer import PineconeIndexer
from ingestion.ingestor import DocumentIngestor

router = APIRouter(prefix="/conversation", tags=["Conversations"])

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar cliente S3
s3_client = boto3.client(
    's3',
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION_NAME,
    endpoint_url=S3_ENDPOINT_URL
)

# Inicializar indexador Pinecone
pinecone_indexer = PineconeIndexer()

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

@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exclui uma conversa e todos os seus recursos associados (documentos no S3 e vetores no Pinecone).
    """
    # Buscar a conversa
    conversation = db.query(ConversationThread).filter(
        ConversationThread.id == conversation_id,
        ConversationThread.user_id == user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    return _delete_conversation_internal(conversation, user, db)

@router.delete("/thread/{thread_id}")
def delete_conversation_by_thread_id(
    thread_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exclui uma conversa pelo thread_id e todos os seus recursos associados (documentos no S3 e vetores no Pinecone).
    """
    # Buscar a conversa pelo thread_id
    conversation = db.query(ConversationThread).filter(
        ConversationThread.thread_id == thread_id,
        ConversationThread.user_id == user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    return _delete_conversation_internal(conversation, user, db)

def _delete_conversation_internal(
    conversation: ConversationThread,
    user: User,
    db: Session
):
    """
    Função interna para excluir uma conversa e todos os seus recursos associados.
    Reutilizada por ambas as rotas de exclusão.
    """
    thread_id = conversation.thread_id
    conversation_id = conversation.id
    
    # Buscar documentos associados para limpar S3 e Pinecone
    documents = db.query(Document).filter(
        Document.conversation_id == conversation_id
    ).all()
    
    # Inicializar o DocumentIngestor para uso correto da remoção de documentos
    ingestor = DocumentIngestor(db_session=db)
    
    for document in documents:
        try:
            # 1. Limpar documentos do S3
            logger.info(f"Excluindo documento {document.id} do S3: {document.s3_path}")
            s3_client.delete_object(
                Bucket=S3_BUCKET_NAME,
                Key=document.s3_path
            )
            
            # 2. Limpar vetores do Pinecone usando o ingestor
            # Isso garante que usamos a mesma lógica da rota de exclusão de documentos
            if document.is_processed:
                logger.info(f"Excluindo vetores do documento {document.id} do Pinecone usando o ingestor")
                try:
                    ingestor.delete_document_from_index(document.id)
                except Exception as e:
                    logger.error(f"Erro ao excluir vetores do Pinecone usando ingestor: {str(e)}")
        
        except Exception as e:
            logger.error(f"Erro ao limpar recursos do documento {document.id}: {str(e)}")
            # Continuar mesmo se houver erro em um documento
    
    # 3. Apagar namespace inteiro do Pinecone para garantir limpeza completa
    if any(doc.is_processed for doc in documents):
        try:
            index_name = f"user{user.id}"
            pinecone_indexer = PineconeIndexer()
            sanitized_index = pinecone_indexer.sanitize_index_name(index_name)
            sanitized_namespace = pinecone_indexer.sanitize_namespace(thread_id)
            
            logger.info(f"Excluindo namespace inteiro do Pinecone: {sanitized_index}/{sanitized_namespace}")
            pinecone_indexer.delete_namespace(sanitized_index, sanitized_namespace)
        except Exception as e:
            logger.error(f"Erro ao excluir namespace do Pinecone: {str(e)}")
    
    # 4. Excluir a conversa (isso vai excluir automaticamente documentos e chunks via CASCADE)
    db.delete(conversation)
    db.commit()
    
    return {"status": "success", "message": "Conversa e recursos associados excluídos com sucesso"} 