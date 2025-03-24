from typing import List, Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class ModelConfiguration:
    model_id: str
    provider: str
    reasoning_effort: Literal["low", "medium", "high"]
    think_mode: bool
    temperature: float

class GraphState(TypedDict):
    """
    Represents the state of the graph.

    Attributes:
        messages: list of user messages
    """

    messages: Annotated[List, add_messages]
    llm_config: ModelConfiguration