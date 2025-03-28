from langchain_core.messages import SystemMessage, HumanMessage, AIMessageChunk
from .states import GraphState
from .llm_config import ModelConfig
from .prompts import RAG_SYSTEM_PROMPT
from langgraph.config import get_stream_writer
from retrieval.pinecone_utils import PineconeUtils

class RAGNodes:
    def __init__(self) -> None:
        self.retriever = PineconeUtils()
    
    def retrieve_documents(self, state: GraphState) -> GraphState:
        """
        Retrieve documents from the database.
        """
        print(f"--- Retrieving documents ---")
        
        retriever_config = state["retriever_config"]

        documents = self.retriever.retrieve_documents(
            query=state["messages"][-1].content,
            top_k=retriever_config["top_k"],
            thread_id=retriever_config["thread_id"],
            user_id=retriever_config["user_id"]
        )
        
        state["retrieved_documents"] = documents
        return state

    def assistant(self, state: GraphState) -> GraphState:
        """
        Generate an answer to the user question, using the documents and the question.
        
        Args:
            state: GraphState with current state (documents and question).

        Returns:
            GraphState with answer
        """
        print(f"--- Generating answer ---")

        model_configuration = state["llm_config"]
        llm = ModelConfig.get_llm(**model_configuration)

        retrieved_documents = state["retrieved_documents"]
        
        # Extrair e organizar o conteúdo dos documentos recuperados
        context = ""
        
        if retrieved_documents:
            context = "Retrieved documents:\n\n"
            for i, doc in enumerate(retrieved_documents, 1):
                # Extrair metadados e conteúdo
                source = doc.metadata.get("source", "Unknown source")
                page = doc.metadata.get("page", "")
                page_info = f" (page {page})" if page else ""
                
                # Adicionar informações do documento ao contexto
                context += f"Document {i}: {source}{page_info}\n"
                context += f"Content: {doc.page_content}\n\n"
        else:
            context = "No relevant documents found for this query."
        
        sys_msg = SystemMessage(
            content=RAG_SYSTEM_PROMPT.format(context=context)
        )

        print(f"System message: {sys_msg}")

        return {"messages": [llm.invoke([sys_msg] + state["messages"])], "retrieved_documents": retrieved_documents}
        
if __name__ == "__main__":
    # optional testing in future.
    pass
