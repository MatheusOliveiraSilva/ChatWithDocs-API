import datetime
import os
import uuid
import logging
import boto3
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.database.session import get_db
from api.database.models import User, Document, ConversationThread
from api.utils.dependencies import get_current_user
from api.schemas.document import DocumentResponse, DocumentListResponse, DocumentDownloadResponse
from api.config.settings import (
    S3_BUCKET_NAME,
    S3_REGION_NAME,
    S3_ACCESS_KEY,
    S3_SECRET_KEY,
    S3_ENDPOINT_URL
)
from ingestion.ingestor import DocumentIngestor

router = APIRouter(prefix="/document", tags=["Documents"])

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurar cliente S3
s3_client = boto3.client(
    's3',
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION_NAME,
)

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    thread_id: str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Faz upload de um documento para o S3 e registra no banco de dados,
    associando-o a uma conversa específica.
    """
    # Buscar a conversa pelo thread_id
    conversation = db.query(ConversationThread).filter(
        ConversationThread.thread_id == thread_id,
        ConversationThread.user_id == user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    # Verificar tamanho do arquivo (limite de 50MB)
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(status_code=400, detail="Arquivo muito grande. Limite de 50MB.")
    
    # Reposicionar o cursor do arquivo
    await file.seek(0)
    
    # Gerar nome único para o arquivo no S3
    original_filename = file.filename
    filename = f"{uuid.uuid4()}{os.path.splitext(original_filename)[1]}"
    s3_path = f"documents/{user.id}/{thread_id}/{filename}"
    
    # Upload para o S3
    try:
        s3_client.upload_fileobj(
            file.file,
            S3_BUCKET_NAME,
            s3_path,
            ExtraArgs={
                "ContentType": file.content_type
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao fazer upload para S3: {str(e)}")
    
    # Criar registro no banco de dados
    new_document = Document(
        user_id=user.id,
        thread_id=thread_id,
        conversation_id=conversation.id,
        filename=filename,
        original_filename=original_filename,
        s3_path=s3_path,
        mime_type=file.content_type,
        file_size=file_size,
        index_status="pending",
        doc_metadata={
            "extension": os.path.splitext(original_filename)[1].lower()
        }
    )
    
    db.add(new_document)
    db.commit()
    db.refresh(new_document)
    
    return new_document

@router.get("", response_model=DocumentListResponse)
def list_documents(
    thread_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista os documentos do usuário, opcionalmente filtrados por thread_id.
    """
    query = db.query(Document).filter(Document.user_id == user.id)
    
    # Se thread_id for fornecido, filtrar apenas documentos dessa conversa
    if thread_id:
        query = query.filter(Document.thread_id == thread_id)
        
    documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    total = query.count()
    
    return {
        "documents": documents,
        "total": total
    }

@router.get("/conversation/{thread_id}", response_model=DocumentListResponse)
def list_conversation_documents(
    thread_id: str,
    skip: int = 0,
    limit: int = 10,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista todos os documentos associados a uma conversa específica.
    """
    # Verificar se a conversa existe e pertence ao usuário
    conversation = db.query(ConversationThread).filter(
        ConversationThread.thread_id == thread_id,
        ConversationThread.user_id == user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    # Buscar documentos associados à conversa
    documents = db.query(Document).filter(
        Document.thread_id == thread_id,
        Document.user_id == user.id
    ).order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    
    total = db.query(Document).filter(
        Document.thread_id == thread_id,
        Document.user_id == user.id
    ).count()
    
    return {
        "documents": documents,
        "total": total
    }

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtém os detalhes de um documento específico.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    
    return document

@router.get("/{document_id}/download", response_model=DocumentDownloadResponse)
def download_document(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Gera uma URL pré-assinada para download do documento.
    """
    # Buscar documento
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    
    # Gerar URL pré-assinada para download (expira em 10 minutos)
    expiration = 600  # segundos
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET_NAME,
                'Key': document.s3_path
            },
            ExpiresIn=expiration
        )
        
        return {
            "download_url": url,
            "expires_in": expiration,
            "filename": document.original_filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar URL de download: {str(e)}")

@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove um documento do S3, do Pinecone e do banco de dados.
    Garante que todos os chunks associados sejam excluídos.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    
    try:
        # 1. Limpar vetores do Pinecone (se o documento foi indexado)
        if document.is_processed:
            logger.info(f"Removendo vetores do documento {document_id} do Pinecone")
            ingestor = DocumentIngestor(db_session=db)
            try:
                ingestor.delete_document_from_index(document_id)
            except Exception as e:
                logger.error(f"Erro ao excluir vetores do Pinecone: {str(e)}")
                # Continuar mesmo se houver erro na limpeza do Pinecone
        
        # 2. Excluir do S3
        logger.info(f"Excluindo documento {document_id} do S3: {document.s3_path}")
        try:
            s3_client.delete_object(
                Bucket=S3_BUCKET_NAME,
                Key=document.s3_path
            )
        except Exception as e:
            logger.error(f"Erro ao excluir do S3: {str(e)}")
            # Mesmo se a exclusão do S3 falhar, continuamos a excluir do banco de dados
        
        # 3. Excluir do banco de dados (isso vai excluir automaticamente os chunks via CASCADE)
        logger.info(f"Excluindo documento {document_id} do banco de dados")
        db.delete(document)
        db.commit()
        
        return None
    
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao excluir documento {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao excluir documento: {str(e)}") 