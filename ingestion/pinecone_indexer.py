import os
import re
import logging
from typing import List, Dict, Any, Optional
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec
from pinecone.exceptions import PineconeConfigurationError, PineconeException

from ingestion.config import (
    PINECONE_API_KEY,
    PINECONE_ENVIRONMENT,
    PINECONE_INDEX_DIMENSIONS,
    OPENAI_API_KEY,
    EMBEDDING_MODEL
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PineconeIndexer:
    """
    Classe para indexar documentos no Pinecone.
    """
    
    def __init__(self, api_key: Optional[str] = None, environment: Optional[str] = None):
        """
        Inicializa o indexador Pinecone.
        
        Args:
            api_key: Chave API do Pinecone (opcional, usa variável de ambiente por padrão)
            environment: Ambiente do Pinecone (opcional, usa variável de ambiente por padrão)
        """
        self.api_key = api_key or PINECONE_API_KEY
        self.environment = environment or PINECONE_ENVIRONMENT
        self.pc = None
        self.embeddings = None
        
        # Verificar se temos a API key do Pinecone
        if not self.api_key:
            logger.error("API Key do Pinecone não encontrada. Funcionalidades de indexação não estarão disponíveis.")
            return
            
        # Inicializar cliente Pinecone com tratamento de erros
        try:
            self.pc = Pinecone(api_key=self.api_key)
            logger.info("Cliente Pinecone inicializado com sucesso")
        except PineconeConfigurationError as e:
            logger.error(f"Erro na configuração do Pinecone: {str(e)}")
            logger.error("Verifique se a chave API do Pinecone está correta")
            return
        except Exception as e:
            logger.error(f"Erro ao inicializar Pinecone: {str(e)}")
            return
            
        # Verificar se temos a API key da OpenAI
        if not OPENAI_API_KEY:
            logger.error("API Key da OpenAI não encontrada. Geração de embeddings não estará disponível.")
            return
            
        # Inicializar modelo de embeddings com tratamento de erros
        try:
            self.embeddings = OpenAIEmbeddings(
                api_key=OPENAI_API_KEY,
                model=EMBEDDING_MODEL
            )
            logger.info("Modelo de embeddings inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar modelo de embeddings: {str(e)}")
    
    @staticmethod
    def sanitize_index_name(name: str) -> str:
        """
        Sanitiza o nome do índice para atender às restrições do Pinecone.
        O nome deve conter apenas letras minúsculas, números e hífens.
        
        Args:
            name: Nome original
            
        Returns:
            Nome sanitizado
        """
        # Converter para minúsculas
        name = name.lower()
        
        # Substituir caracteres não permitidos por hífens
        sanitized = re.sub(r'[^a-z0-9-]', '', name)
        
        # Remover hífens duplicados
        sanitized = re.sub(r'-+', '-', sanitized)
        
        # Garantir que comece com letra ou número
        if sanitized and not sanitized[0].isalnum():
            sanitized = 'p' + sanitized[1:]
            
        # Garantir tamanho mínimo
        if len(sanitized) < 3:
            sanitized = 'idx-' + sanitized
            
        # Limitar tamanho (máximo 45 caracteres para índices Pinecone)
        if len(sanitized) > 45:
            sanitized = sanitized[:45]
            
        return sanitized
    
    @staticmethod
    def sanitize_namespace(namespace: str) -> str:
        """
        Sanitiza o namespace para atender às restrições do Pinecone.
        
        Args:
            namespace: Namespace original
            
        Returns:
            Namespace sanitizado
        """
        # Substituir caracteres não alfanuméricos por underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', namespace)
        
        # Limitar tamanho (para evitar problemas)
        if len(sanitized) > 64:
            sanitized = sanitized[:64]
            
        return sanitized
    
    def ensure_index_exists(self, index_name: str) -> str:
        """
        Verifica se o índice existe e cria se não existir.
        
        Args:
            index_name: Nome do índice Pinecone
            
        Returns:
            Nome sanitizado do índice
        """
        # Verificar se o cliente Pinecone está inicializado
        if not self.pc:
            logger.error("Cliente Pinecone não inicializado. Não é possível manipular índices.")
            raise RuntimeError("Cliente Pinecone não inicializado")
            
        # Sanitizar nome do índice
        sanitized_name = self.sanitize_index_name(index_name)
        
        try:
            # Listar índices existentes
            existing_indexes = [index.name for index in self.pc.list_indexes()]
            
            # Criar índice se não existir
            if sanitized_name not in existing_indexes:
                logger.info(f"Criando índice Pinecone: {sanitized_name}")
                self.pc.create_index(
                    name=sanitized_name,
                    dimension=PINECONE_INDEX_DIMENSIONS,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                logger.info(f"Índice {sanitized_name} criado com sucesso")
        except PineconeException as e:
            logger.error(f"Erro ao gerenciar índice Pinecone: {str(e)}")
            raise
            
        return sanitized_name
    
    def index_chunks(
        self, 
        chunks: List[Dict[str, Any]], 
        index_name: str, 
        namespace: str
    ) -> List[str]:
        """
        Indexa chunks no Pinecone.
        
        Args:
            chunks: Lista de dicionários com "content" e "metadata"
            index_name: Nome do índice Pinecone
            namespace: Namespace dentro do índice (geralmente thread_id)
            
        Returns:
            Lista de IDs dos vetores criados
        """
        # Sanitizar nomes
        sanitized_index = self.ensure_index_exists(index_name)
        sanitized_namespace = self.sanitize_namespace(namespace)
        
        # Obter o índice
        index = self.pc.Index(sanitized_index)
        
        # Criar vetores com IDs únicos
        texts = [chunk["content"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        # Gerar IDs únicos
        ids = [f"{sanitized_namespace}_{meta['document_id']}_{meta['chunk_index']}" for meta in metadatas]
        
        # Criar embeddings e upsert no Pinecone
        vector_store = PineconeVectorStore(
            index=index,
            embedding=self.embeddings,
            pinecone_api_key=self.api_key,
            namespace=sanitized_namespace
        )
        
        # Adicionar documentos
        vector_store.add_texts(
            texts=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        return ids
    
    def delete_document(self, index_name: str, namespace: str, document_id: str) -> None:
        """
        Deleta todos os chunks de um documento do Pinecone.
        
        Args:
            index_name: Nome do índice Pinecone
            namespace: Namespace dentro do índice (geralmente thread_id)
            document_id: ID do documento a ser excluído
        """
        # Sanitizar nomes
        sanitized_index = self.sanitize_index_name(index_name)
        sanitized_namespace = self.sanitize_namespace(namespace)
        
        # Obter índice
        index = self.pc.Index(sanitized_index)
        
        # Excluir vetores pelo filtro de metadados
        index.delete(
            filter={"document_id": document_id},
            namespace=sanitized_namespace
        )
    
    def delete_namespace(self, index_name: str, namespace: str) -> None:
        """
        Deleta todo um namespace (todos os documentos de uma thread).
        
        Args:
            index_name: Nome do índice Pinecone
            namespace: Namespace a ser excluído
        """
        # Sanitizar nomes
        sanitized_index = self.sanitize_index_name(index_name)
        sanitized_namespace = self.sanitize_namespace(namespace)
        
        # Obter índice
        index = self.pc.Index(sanitized_index)
        
        # Excluir namespace inteiro
        index.delete(delete_all=True, namespace=sanitized_namespace) 