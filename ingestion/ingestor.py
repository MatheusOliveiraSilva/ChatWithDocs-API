import os
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from langchain_pinecone import PineconeVectorStore

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
            
            # Usar um único índice para toda a aplicação
            index_name = "chatwithdocs"
            
            # Namespace no formato <user_id>-<thread_id>
            namespace = f"{document.user_id}-{document.thread_id}"
            
            # Verificar se o namespace excede o limite de caracteres
            max_namespace_length = 64
            if len(namespace) > max_namespace_length:
                # Calcular quanto do thread_id podemos manter
                user_id_len = len(str(document.user_id))
                # Reservar 1 caracter para o hífen
                thread_id_max_len = max_namespace_length - user_id_len - 1
                namespace = f"{document.user_id}-{document.thread_id[:thread_id_max_len]}"
            
            # Verificar se o índice existe e criá-lo se necessário
            sanitized_index = self.indexer.ensure_index_exists(index_name)
            sanitized_namespace = self.indexer.sanitize_namespace(namespace)
            
            # Indexar chunks no Pinecone
            logger.info(f"Indexando {len(chunks)} chunks no Pinecone (index={sanitized_index}, namespace={sanitized_namespace})")
            
            # Processar chunks em lotes para salvar gradualmente no banco
            BATCH_SIZE = 10
            total_chunks = len(chunks)
            
            for i in range(0, total_chunks, BATCH_SIZE):
                # Pegar o próximo lote de chunks
                batch_chunks = chunks[i:i+BATCH_SIZE]
                
                # Extrair textos e metadados para o batch atual
                batch_texts = [chunk["content"] for chunk in batch_chunks]
                batch_metadatas = [chunk["metadata"] for chunk in batch_chunks]
                
                # Gerar IDs únicos para o batch
                batch_ids = [f"{sanitized_namespace}_{meta['document_id']}_{meta['chunk_index']}" for meta in batch_metadatas]
                
                # Indexar o batch atual no Pinecone
                logger.info(f"Indexando batch {i//BATCH_SIZE + 1}/{(total_chunks+BATCH_SIZE-1)//BATCH_SIZE}: {len(batch_chunks)} chunks")
                
                try:
                    # Obter ou criar o índice Pinecone
                    index = self.indexer.pc.Index(sanitized_index)
                    
                    # Criar vetores para este batch
                    vector_store = PineconeVectorStore(
                        index=index,
                        embedding=self.indexer.embeddings,
                        pinecone_api_key=self.indexer.api_key,
                        namespace=sanitized_namespace
                    )
                    
                    # Adicionar documentos do batch atual
                    vector_store.add_texts(
                        texts=batch_texts,
                        metadatas=batch_metadatas,
                        ids=batch_ids
                    )
                except Exception as e:
                    logger.error(f"Erro ao indexar batch no Pinecone: {str(e)}")
                    raise
                
                # Salvar os chunks processados no banco em tempo real
                for j, chunk in enumerate(batch_chunks):
                    db_chunk = DocumentChunk(
                        document_id=document.id,
                        chunk_index=int(chunk["metadata"]["chunk_index"]),
                        content=chunk["content"],
                        chunk_metadata=chunk["metadata"],
                        vector_id=batch_ids[j]
                    )
                    self.db.add(db_chunk)
                
                # Commit parcial para salvar os chunks deste batch
                self.db.commit()
                
                # Atualizar progresso no documento
                progress = min(100, int((i + len(batch_chunks)) / total_chunks * 100))
                document.doc_metadata.update({
                    "indexing_progress": progress,
                    "chunks_indexed": i + len(batch_chunks),
                    "total_chunks": total_chunks
                })
                self.db.commit()
            
            # Atualizar status do documento
            document.is_processed = True
            document.index_status = DOCUMENT_STATUS["COMPLETED"]
            
            # Armazenar informações do índice nos metadados
            document.doc_metadata.update({
                "pinecone_index": sanitized_index,
                "pinecone_namespace": sanitized_namespace,
                "indexing_progress": 100,
                "chunks_indexed": total_chunks,
                "total_chunks": total_chunks
            })
            
            self.db.commit()
            
            return {
                "status": "success",
                "document_id": document.id,
                "chunks_processed": total_chunks,
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
        Remove um documento do índice Pinecone, garantindo que todos os chunks sejam excluídos.
        
        Args:
            document_id: ID do documento a ser removido
            
        Returns:
            Informações sobre o resultado da operação
        """
        # Buscar documento
        document = self.db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            raise ValueError(f"Documento não encontrado: {document_id}")
        
        # Resultado padrão com informações de sucesso
        result = {
            "status": "success",
            "document_id": document.id,
            "chunks_removed": 0
        }
        
        try:
            # Verificar se temos informações de índice nos metadados
            pinecone_index = document.doc_metadata.get("pinecone_index")
            pinecone_namespace = document.doc_metadata.get("pinecone_namespace")
            
            # Se não temos informações armazenadas, usar a lógica padrão
            if not pinecone_index or not pinecone_namespace:
                # Usar um único índice para toda a aplicação
                pinecone_index = "chatwithdocs"
                
                # Namespace no formato <user_id>-<thread_id>
                namespace = f"{document.user_id}-{document.thread_id}"
                
                # Verificar se o namespace excede o limite de caracteres
                max_namespace_length = 64
                if len(namespace) > max_namespace_length:
                    # Calcular quanto do thread_id podemos manter
                    user_id_len = len(str(document.user_id))
                    # Reservar 1 caracter para o hífen
                    thread_id_max_len = max_namespace_length - user_id_len - 1
                    namespace = f"{document.user_id}-{document.thread_id[:thread_id_max_len]}"
                
                # Sanitizar nome do namespace
                pinecone_namespace = self.indexer.sanitize_namespace(namespace)
            
            # Verificar se o índice existe antes de tentar acessá-lo
            try:
                # Listar índices existentes
                existing_indexes = [index.name for index in self.indexer.pc.list_indexes()]
                
                if pinecone_index not in existing_indexes:
                    logger.warning(f"Índice {pinecone_index} não existe, nada para excluir")
                    return {
                        "status": "warning",
                        "document_id": document.id,
                        "message": f"Índice {pinecone_index} não encontrado"
                    }
            except Exception as e:
                logger.error(f"Erro ao verificar índices Pinecone: {str(e)}")
            
            # Obter os IDs dos chunks deste documento
            chunk_ids = []
            chunk_count = 0
            
            # Buscar chunks do documento para remoção específica
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document.id
            ).all()
            
            chunk_count = len(chunks)
            
            if chunk_count > 0:
                # Se tivermos chunks no banco, usamos seus IDs para exclusão mais precisa
                logger.info(f"Encontrados {chunk_count} chunks para o documento {document.id}")
                chunk_ids = [chunk.vector_id for chunk in chunks if chunk.vector_id]
                
                # Remover os vetores específicos pelo ID
                if chunk_ids:
                    try:
                        logger.info(f"Excluindo {len(chunk_ids)} vetores por ID do Pinecone")
                        index = self.indexer.pc.Index(pinecone_index)
                        index.delete(ids=chunk_ids, namespace=pinecone_namespace)
                        result["chunks_removed_by_id"] = len(chunk_ids)
                    except Exception as e:
                        logger.warning(f"Erro ao excluir vetores por ID, tentando por filtro: {str(e)}")
            
            # Também remover usando o filtro (abordagem de segurança para pegar qualquer vetor restante)
            try:
                logger.info(f"Excluindo vetores por filtro document_id={document.id} do Pinecone")
                self.indexer.delete_document(pinecone_index, pinecone_namespace, str(document.id))
                result["removed_by_filter"] = True
            except Exception as e:
                logger.error(f"Erro ao excluir por filtro: {str(e)}")
                result["removed_by_filter"] = False
            
            # Atualizar status no banco de dados
            document.is_processed = False
            document.index_status = DOCUMENT_STATUS["PENDING"]
            
            # Remover informações de índice dos metadados
            if "pinecone_index" in document.doc_metadata:
                del document.doc_metadata["pinecone_index"]
            if "pinecone_namespace" in document.doc_metadata:
                del document.doc_metadata["pinecone_namespace"]
            if "indexing_progress" in document.doc_metadata:
                del document.doc_metadata["indexing_progress"]
            if "chunks_indexed" in document.doc_metadata:
                del document.doc_metadata["chunks_indexed"]
            if "total_chunks" in document.doc_metadata:
                del document.doc_metadata["total_chunks"]
            
            self.db.commit()
            
            # Adicionar informações ao resultado
            result.update({
                "pinecone_index": pinecone_index,
                "pinecone_namespace": pinecone_namespace,
                "total_chunks": chunk_count
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao remover documento {document.id} do índice: {str(e)}")
            # Rolar de volta transações do banco de dados em caso de erro
            self.db.rollback()
            
            # Retornar erro, mas não relançar a exceção para permitir que a aplicação continue
            return {
                "status": "error",
                "document_id": document.id,
                "error": str(e)
            } 