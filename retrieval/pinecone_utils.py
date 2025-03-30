import os
from pinecone import Pinecone
from langchain_core.documents import Document
from typing import List
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
class PineconeUtils:
    def __init__(self):
        self.pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

    def retrieve_documents(self, 
                           query: str, 
                           top_k: int = 5,
                           thread_id: str = None,
                           user_id: str = None) -> List[Document]:
        """
        Recupera documentos similares a uma query de um índice Pinecone.
        
        Args:
            query: O texto para buscar documentos similares
            top_k: Número de documentos a retornar
            thread_id: ID do thread para usar como namespace
            user_id: ID do usuário para construir o nome do índice
            
        Returns:
            Lista de documentos recuperados
        """
        if user_id is None:
            raise ValueError("user_id é obrigatório para recuperar documentos")
        
        if thread_id is None:
            raise ValueError("thread_id é obrigatório para recuperar documentos")
        
        # Usar o único índice para toda a aplicação
        index_name = "chatwithdocs"
        
        # Construir o namespace seguindo o novo padrão <user_id>-<thread_id>
        namespace = f"{user_id}-{thread_id}"
        
        # Verificar se o namespace excede o limite de caracteres
        max_namespace_length = 64
        if len(namespace) > max_namespace_length:
            # Calcular quanto do thread_id podemos manter
            user_id_len = len(str(user_id))
            # Reservar 1 caracter para o hífen
            thread_id_max_len = max_namespace_length - user_id_len - 1
            namespace = f"{user_id}-{thread_id[:thread_id_max_len]}"
        
        # Verificar se o índice existe
        available_indexes = [index.name for index in self.pinecone_client.list_indexes()]
        if index_name not in available_indexes:
            raise ValueError(f"Índice {index_name} não encontrado")
        
        # Obter o índice
        index = self.pinecone_client.Index(index_name)
        
        # Criar o vector store para busca
        vector_store = PineconeVectorStore(
            index=index,
            namespace=namespace,
            embedding=OpenAIEmbeddings(
                model="text-embedding-3-large"
            )
        )
        
        # Realizar a busca por similaridade
        results = vector_store.similarity_search(
            query=query,
            k=top_k
        )
        
        return results
        
        
