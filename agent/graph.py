from langgraph.graph import END, StateGraph, START
from langgraph.checkpoint.memory import MemorySaver
from .states import GraphState
from .nodes import RAGNodes
from langchain_core.messages import HumanMessage, AIMessageChunk, AIMessage

class RAGGraph:
    def __init__(self):
        self.nodes = RAGNodes()

        self.Graph = StateGraph(GraphState)

        self.Graph = self.setup_nodes(self.Graph)

        self.Graph = self.setup_edges(self.Graph)

        self.agent = self.Graph.compile(checkpointer=MemorySaver())

    def get_agent(self):
        return self.agent

    def setup_nodes(self, graph: StateGraph) -> StateGraph:

        graph.add_node("retriever", self.nodes.retrieve_documents)
        graph.add_node("assistant", self.nodes.assistant)

        return graph
    
    def setup_edges(self, graph: StateGraph) -> StateGraph:

        graph.add_edge(START, "retriever")
        graph.add_edge("retriever", "assistant")
        graph.add_edge("assistant", END)

        return graph

if __name__ == "__main__":
    graph = RAGGraph()
    agent = graph.get_agent()
    
    result = agent.invoke({
            "messages": [HumanMessage(content="me fale como ministrar os medicamentos para o cachorro, dado as instrucoes do documento.")],
            "llm_config": {
                "model_id": "gpt-4o",
                "provider": "openai",
                "temperature": 0
            },
            "retriever_config": {
                "user_id": 1,
                "thread_id": "session-1742852515006-nznl2ol-4f60801d-e30c-494d-b0e8-7675dd0c9c",
                "top_k": 5,
                "include_sources": True
            }
        }, 
        config={"configurable": {"thread_id": "12345"}}
    )

    for message in result["messages"]:
        if isinstance(message, HumanMessage):
            print("Mensagem do Humano:", message.content)
        elif isinstance(message, AIMessageChunk) or isinstance(message, AIMessage):
            print("Mensagem do Assistente:", message.content)
        else:
            print(f"Outro tipo de mensagem ({type(message).__name__}):", message.content)