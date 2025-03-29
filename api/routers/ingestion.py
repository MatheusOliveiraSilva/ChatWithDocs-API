from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from api.database.session import get_db
from api.database.models import User, Document
from api.utils.dependencies import get_current_user
from ingestion.ingestor import DocumentIngestor

router = APIRouter(prefix="/ingestion", tags=["Document Ingestion"])

def process_document_task(document_id: int, db: Session):
    """
    Função de fundo para processar um documento.
    """
    # Criar uma nova sessão para o background task
    db_session = Session(bind=db.get_bind())
    try:
        # Verificar se o documento existe
        document = db_session.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Documento não encontrado: {document_id}")
            
        # Criar ingestor com a sessão
        ingestor = DocumentIngestor(db_session=db_session)
        
        # Processar documento
        ingestor.ingest_document(document_id)
    except Exception as e:
        import logging
        logging.error(f"Erro ao processar documento {document_id}: {str(e)}")
        # Atualizar status do documento para falha
        try:
            document = db_session.query(Document).filter(Document.id == document_id).first()
            if document:
                document.index_status = "failed"
                document.doc_metadata = document.doc_metadata or {}
                document.doc_metadata.update({"error": str(e)})
                db_session.commit()
        except Exception as inner_e:
            logging.error(f"Erro ao atualizar status do documento: {str(inner_e)}")
    finally:
        db_session.close()

@router.post("/{document_id}/process", response_model=Dict[str, Any])
def process_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Inicia o processamento assíncrono de um documento.
    """
    # Verificar se o documento existe e pertence ao usuário
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    
    # Verificar se o documento já está em processamento
    if document.index_status == "processing":
        raise HTTPException(status_code=400, detail="Documento já está em processamento")
    
    # Iniciar processamento em background
    background_tasks.add_task(process_document_task, document_id, db)
    
    return {
        "status": "processing_started",
        "document_id": document_id,
        "message": "Processamento iniciado em segundo plano"
    }

@router.post("/thread/{thread_id}/process", response_model=Dict[str, Any])
def process_thread_documents(
    thread_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Inicia o processamento de todos os documentos de uma thread.
    """
    # Buscar todos os documentos não processados da thread
    documents = db.query(Document).filter(
        Document.thread_id == thread_id,
        Document.user_id == user.id,
        Document.is_processed == False
    ).all()
    
    if not documents:
        raise HTTPException(status_code=404, detail="Nenhum documento pendente de processamento")
    
    # Iniciar processamento em background para cada documento
    document_ids = []
    for document in documents:
        background_tasks.add_task(process_document_task, document.id, db)
        document_ids.append(document.id)
    
    return {
        "status": "processing_started",
        "thread_id": thread_id,
        "document_count": len(document_ids),
        "document_ids": document_ids,
        "message": "Processamento iniciado para todos os documentos"
    }

@router.delete("/{document_id}", response_model=Dict[str, Any])
def delete_document_index(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove um documento do índice Pinecone.
    """
    # Verificar se o documento existe e pertence ao usuário
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    
    # Verificar se o documento está indexado
    if not document.is_processed:
        raise HTTPException(status_code=400, detail="Documento não está indexado")
    
    # Remover do índice
    ingestor = DocumentIngestor(db_session=db)
    result = ingestor.delete_document_from_index(document_id)
    
    return {
        "status": "success",
        "document_id": document_id,
        "message": "Documento removido do índice"
    } 