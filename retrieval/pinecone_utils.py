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
        
        index_name = f"user{user_id}"
        
        # Verificar se o índice existe
        available_indexes = [index.name for index in self.pinecone_client.list_indexes()]
        if index_name not in available_indexes:
            raise ValueError(f"Índice {index_name} não encontrado")
        
        # Obter o índice
        index = self.pinecone_client.Index(index_name)
        
        # Criar o vector store para busca
        vector_store = PineconeVectorStore(
            index=index,
            namespace=thread_id if thread_id else "",
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
        
        
