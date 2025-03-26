import os
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from api.database.models import Document, DocumentChunk, User, ConversationThread
from api.config.settings import S3_BUCKET_NAME
from ingestion.document_processor import DocumentProcessor
from ingestion.pinecone_indexer import PineconeIndexer
from ingestion.config import DOCUMENT_STATUS

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentIngestor:
    """
    Classe principal para ingestão de documentos: orquestra o processo completo de
    processamento e indexação.
    """
    
    def __init__(
        self, 
        db_session: Session,
        processor: Optional[DocumentProcessor] = None,
        indexer: Optional[PineconeIndexer] = None
    ):
        """
        Inicializar o ingestor com dependências.
        
        Args:
            db_session: Sessão do SQLAlchemy para operações no banco de dados
            processor: Processador de documentos (opcional)
            indexer: Indexador do Pinecone (opcional)
        """
        self.db = db_session
        self.processor = processor or DocumentProcessor()
        self.indexer = indexer or PineconeIndexer()
        self.bucket_name = S3_BUCKET_NAME
    
    def ingest_document(self, document_id: int) -> Dict[str, Any]:
        """
        Processa um documento completo e o indexa no Pinecone.
        
        Args:
            document_id: ID do documento no banco de dados
            
        Returns:
            Informações sobre o resultado do processamento
        """
        # Buscar documento no banco de dados
        document = self.db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            raise ValueError(f"Documento não encontrado: {document_id}")
        
        # Atualizar status para "processing"
        document.index_status = DOCUMENT_STATUS["PROCESSING"]
        self.db.commit()
        
        try:
            # Buscar informações da conversa
            conversation = self.db.query(ConversationThread).filter(
                ConversationThread.id == document.conversation_id
            ).first()
            
            if not conversation:
                raise ValueError(f"Conversa não encontrada: {document.conversation_id}")
                
            # Preparar metadados para os chunks
            metadata = {
                "document_id": str(document.id),
                "thread_id": document.thread_id,
                "user_id": str(document.user_id),
                "filename": document.original_filename,
                "mime_type": document.mime_type,
                **document.doc_metadata  # Inclui metadados personalizados
            }
            
            # Processar documento (download, extração, chunking)
            logger.info(f"Processando documento {document.id}: {document.original_filename}")
            chunks = self.processor.process_document(
                self.bucket_name,
                document.s3_path,
                metadata
            )
            
            # Criar nome do índice baseado no usuário
            index_name = f"user{document.user_id}"
            
            # Namespace é o thread_id (será sanitizado pelo indexador)
            namespace = document.thread_id
            
            # Indexar chunks no Pinecone
            logger.info(f"Indexando {len(chunks)} chunks no Pinecone (index={index_name}, namespace={namespace})")
            
            # O método index_chunks sanitiza internamente os nomes
            vector_ids = self.indexer.index_chunks(chunks, index_name, namespace)
            
            # Obter nomes sanitizados para referência
            sanitized_index = self.indexer.sanitize_index_name(index_name)
            sanitized_namespace = self.indexer.sanitize_namespace(namespace)
            
            # Salvar chunks no banco de dados
            for i, chunk in enumerate(chunks):
                db_chunk = DocumentChunk(
                    document_id=document.id,
                    chunk_index=i,
                    content=chunk["content"],
                    chunk_metadata=chunk["metadata"],
                    vector_id=vector_ids[i] if i < len(vector_ids) else None
                )
                self.db.add(db_chunk)
            
            # Atualizar status do documento
            document.is_processed = True
            document.index_status = DOCUMENT_STATUS["COMPLETED"]
            
            # Armazenar informações do índice nos metadados
            document.doc_metadata.update({
                "pinecone_index": sanitized_index,
                "pinecone_namespace": sanitized_namespace
            })
            
            self.db.commit()
            
            return {
                "status": "success",
                "document_id": document.id,
                "chunks_processed": len(chunks),
                "index_name": sanitized_index,
                "namespace": sanitized_namespace
            }
            
        except Exception as e:
            # Em caso de erro, atualizar status e registrar a exceção
            logger.error(f"Erro ao processar documento {document.id}: {str(e)}")
            document.index_status = DOCUMENT_STATUS["FAILED"]
            document.doc_metadata.update({"error": str(e)})
            self.db.commit()
            
            # Re-lançar a exceção para tratamento externo
            raise
    
    def delete_document_from_index(self, document_id: int) -> Dict[str, Any]:
        """
        Remove um documento do índice Pinecone.
        
        Args:
            document_id: ID do documento a ser removido
            
        Returns:
            Informações sobre o resultado da operação
        """
        # Buscar documento
        document = self.db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            raise ValueError(f"Documento não encontrado: {document_id}")
        
        try:
            # Verificar se temos informações de índice nos metadados
            pinecone_index = document.doc_metadata.get("pinecone_index")
            pinecone_namespace = document.doc_metadata.get("pinecone_namespace")
            
            # Se não temos informações armazenadas, usar a lógica padrão
            if not pinecone_index or not pinecone_namespace:
                # Criar nome do índice baseado no usuário
                index_name = f"user{document.user_id}"
                
                # Namespace é o thread_id
                namespace = document.thread_id
                
                # Sanitizar nomes (mesmo processo usado na ingestão)
                pinecone_index = self.indexer.sanitize_index_name(index_name)
                pinecone_namespace = self.indexer.sanitize_namespace(namespace)
            
            # Remover do Pinecone
            self.indexer.delete_document(pinecone_index, pinecone_namespace, str(document.id))
            
            # Atualizar status
            document.is_processed = False
            document.index_status = DOCUMENT_STATUS["PENDING"]
            
            # Remover informações de índice dos metadados
            if "pinecone_index" in document.doc_metadata:
                del document.doc_metadata["pinecone_index"]
            if "pinecone_namespace" in document.doc_metadata:
                del document.doc_metadata["pinecone_namespace"]
                
            self.db.commit()
            
            return {
                "status": "success",
                "document_id": document.id,
                "index_name": pinecone_index,
                "namespace": pinecone_namespace
            }
            
        except Exception as e:
            logger.error(f"Erro ao remover documento {document.id} do índice: {str(e)}")
            raise 