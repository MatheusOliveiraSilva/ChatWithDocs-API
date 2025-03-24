from langgraph.graph import END, StateGraph, START
from langgraph.checkpoint.memory import MemorySaver
from .states import GraphState
from .nodes import SimpleAssistantNodes
from langchain_core.messages import HumanMessage

class SimpleAssistantGraph:
    def __init__(self):
        self.nodes = SimpleAssistantNodes()

        self.Graph = StateGraph(GraphState)

        self.Graph = self.setup_nodes(self.Graph)
        
        self.Graph = self.setup_edges(self.Graph)

        self.agent = self.Graph.compile(checkpointer=MemorySaver())

    def get_agent(self):
        return self.agent

    def setup_nodes(self, graph: StateGraph) -> StateGraph:

        graph.add_node("assistant", self.nodes.assistant)

        return graph
    
    def setup_edges(self, graph: StateGraph) -> StateGraph:

        graph.add_edge(START, "assistant")
        graph.add_edge("assistant", END)

        return graph

if __name__ == "__main__":
    graph = SimpleAssistantGraph()
    agent = graph.get_agent()
    
    result = agent.invoke({
        "messages": [HumanMessage(content="Hello, how are you?")],
        "model_config": {
            "model_id": "gpt-4o",
            "provider": "openai",
            "temperature": 0
        }
        }, 
        config={"configurable": {"thread_id": "123"}}
    )

    print(result)