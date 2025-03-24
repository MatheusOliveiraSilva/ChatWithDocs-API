import json
from typing import Dict, Any, Generator, Tuple, List, Optional, Union
from fastapi import HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

class LLMStreamer:
    """
    Classe para gerenciar streaming de diferentes provedores de LLMs.
    Suporta OpenAI e Anthropic com diferentes formatos de streaming.
    """
    
    @staticmethod
    def format_streaming_response(
        chunk: Union[AIMessage, str], 
        meta: Dict[str, Any] = None
    ) -> str:
        """
        Formata um chunk de resposta para streaming no formato SSE (Server-Sent Events).
        
        Args:
            chunk: Chunk de resposta do modelo (AIMessage ou string)
            meta: Metadados adicionais
            
        Returns:
            String formatada para SSE
        """
        # Se o chunk for uma AIMessage, extrair o conteúdo
        if isinstance(chunk, AIMessage):
            content = chunk.content
        else:
            content = chunk
            
        # Formatar resposta para SSE
        payload = {"content": content}
        if meta:
            payload["meta"] = meta
            
        return f"data: {json.dumps(payload)}\n\n"
    
    @staticmethod
    def stream_agent_response(
        agent, 
        messages: List[Union[HumanMessage, AIMessage]], 
        config: Dict[str, Any],
        stream_mode: str = "messages"
    ) -> Generator[str, None, None]:
        """
        Stream das respostas do agent.
        
        Args:
            agent: O agente LangChain
            messages: Lista de mensagens (histórico + input atual)
            config: Configuração do modelo
            stream_mode: Modo de streaming ("messages" ou "tokens")
            
        Returns:
            Generator que produz chunks de resposta formatados para SSE
        """
        try:
            # Converter config para o formato esperado pelo agent
            agent_config = {"configurable": config} if config else {}
            
            # Stream da resposta
            for chunk, meta in agent.stream(
                {"messages": messages}, 
                stream_mode=stream_mode,
                config=agent_config
            ):
                yield LLMStreamer.format_streaming_response(chunk, meta)
                
            # Marcar fim do streaming
            yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"
            
        except Exception as e:
            # Em caso de erro durante o streaming
            error_payload = {
                "error": str(e),
                "error_type": type(e).__name__
            }
            yield f"data: {json.dumps(error_payload)}\n\n"
            yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"
    
    @staticmethod
    def stream_provider_specific(
        agent,
        messages: List[Union[HumanMessage, AIMessage]],
        provider: str,
        model_id: str,
        config: Dict[str, Any] = None
    ) -> Generator[str, None, None]:
        """
        Stream específico para diferentes provedores, lidando com suas peculiaridades.
        
        Args:
            agent: O agente LangChain
            messages: Lista de mensagens
            provider: Provedor do modelo ("openai", "anthropic", etc)
            model_id: ID do modelo sendo usado
            config: Configuração do modelo
            
        Returns:
            Generator que produz chunks de resposta formatados para SSE
        """
        stream_mode = "messages"  # Padrão para a maioria dos casos
        
        # Ajustes específicos por provedor
        if provider.lower() == "openai":
            # Alguns modelos da OpenAI preferem streaming por tokens
            if any(m in model_id.lower() for m in ["gpt-4-vision", "gpt-4o-vision"]):
                stream_mode = "tokens"
                
        elif provider.lower() == "anthropic":
            # A Anthropic tem diferenças entre Claude 2 e Claude 3
            if "claude-3" in model_id.lower():
                stream_mode = "messages"  # Claude 3 funciona bem com messages
            else:
                stream_mode = "tokens"  # Claude 2 e anteriores preferem tokens
        
        # Fazer o streaming com as configurações específicas
        yield from LLMStreamer.stream_agent_response(
            agent=agent,
            messages=messages,
            config=config,
            stream_mode=stream_mode
        ) 