from typing import List, Annotated, Literal, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.documents import Document

class ModelConfiguration:
    model_id: str
    provider: str
    reasoning_effort: Literal["low", "medium", "high"]
    think_mode: bool
    temperature: float

class RetrieverConfiguration:
    user_id: int
    thread_id: str
    top_k: int
    include_sources: bool

class GraphState(TypedDict):
    """
    Represents the state of the graph.

    Attributes:
        messages: list of user messages
    """

    messages: Annotated[List, add_messages]
    llm_config: ModelConfiguration
    retriever_config: RetrieverConfiguration
    retrieved_documents: List[Document]