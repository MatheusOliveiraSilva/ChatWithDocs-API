from langchain_core.messages import SystemMessage, HumanMessage, AIMessageChunk
from .states import GraphState
from .llm_config import ModelConfig
from .prompts import SIMPLE_ASSISTANT_PROMPT
from langgraph.config import get_stream_writer

class SimpleAssistantNodes:
    def __init__(self) -> None:
        pass
    
    def assistant(self, state: GraphState) -> GraphState:
        """
        Generate an answer to the user question, using the documents and the question.
        
        Args:
            state: GraphState with current state (documents and question).

        Returns:
            GraphState with answer
        """
        print(f"--- Generating answer ---")

        model_configuration = state["model_config"]
        
        llm = ModelConfig.get_llm(**model_configuration)

        sys_msg = SystemMessage(
            content=SIMPLE_ASSISTANT_PROMPT
        )

        return {"messages": [llm.invoke([sys_msg] + state["messages"])]}
        
if __name__ == "__main__":
    # optional testing in future.
    pass
