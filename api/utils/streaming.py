import json
from typing import Dict, Any, Generator, List, Optional, Union
from langchain_core.messages import AIMessage, HumanMessage

class LLMStreamer:
    """
    Classe para gerenciar streaming de respostas de modelos LLM.
    Suporta diferentes provedores e formatos de resposta.
    """
    
    @staticmethod
    def format_response(chunk: Any, meta: Dict[str, Any] = None) -> str:
        """
        Formata um chunk de resposta para streaming no formato SSE (Server-Sent Events).
        
        Args:
            chunk: Chunk de resposta do modelo
            meta: Metadados adicionais
            
        Returns:
            String formatada para SSE
        """
        # Determinar o conteúdo e tipo do chunk
        content = ""
        chunk_type = "text"
        
        # Se o chunk for uma AIMessage, extrair o conteúdo
        if isinstance(chunk, AIMessage):
            content = chunk.content
        elif isinstance(chunk, dict):
            # Para lidar com casos como Claude 3.7 Sonnet
            if "text" in chunk:
                content = chunk["text"]
                chunk_type = "text"
            elif "thinking" in chunk:
                content = chunk["thinking"]
                chunk_type = "thinking"
            else:
                # Caso genérico para outros formatos de dicionário
                content = chunk
        else:
            # String ou outro tipo
            content = str(chunk)
            
        # Formatar resposta para SSE com tipo explícito
        payload = {
            "content": content,
            "type": chunk_type
        }
        
        if meta:
            payload["meta"] = meta
            
        return f"data: {json.dumps(payload)}\n\n"
    
    @staticmethod
    def stream_response(
        agent,
        agent_input: Dict[str, Any] = None,
        agent_config: Dict[str, Any] = None,
        # Parâmetros legados para compatibilidade
        messages: List[Union[HumanMessage, AIMessage]] = None,
        llm_config: Dict[str, Any] = None,
        thread_id: str = None
    ) -> Generator[str, None, None]:
        """
        Função unificada para streaming de respostas de modelos de linguagem.
        Suporta tanto o formato antigo (messages, llm_config, thread_id) quanto
        o novo formato RAG (agent_input, agent_config).
        
        Args:
            agent: O agente LangChain/LangGraph
            agent_input: Input completo para o agente no formato RAG
            agent_config: Configuração do agente
            messages: (Legado) Lista de mensagens (histórico + input atual)
            llm_config: (Legado) Configuração do modelo (provider, model_id, etc)
            thread_id: (Legado) ID da thread para persistência
            
        Returns:
            Generator que produz chunks de resposta formatados para SSE
        """
        # Compatibilidade com formato antigo (formato legado)
        if agent_input is None and messages is not None:
            agent_input = {
                "messages": messages,
                "llm_config": llm_config or {}
            }
            
        if agent_config is None and thread_id is not None:
            agent_config = {"configurable": {"thread_id": thread_id}}
            
        # Garantir que temos um input válido
        if agent_input is None:
            agent_input = {"messages": []}
            
        # Extrair config do LLM para comportamentos específicos de modelo
        llm_config = agent_input.get("llm_config", {})
        
        # Configurações básicas
        provider = llm_config.get("provider", "openai")
        model_id = llm_config.get("model_id", "gpt-4o")
        think_mode = llm_config.get("think_mode", False)
        
        # Detectar se é Claude 3.7 com thinking mode
        is_claude_37_thinking = (
            provider.lower() == "anthropic" and
            "claude-3-7" in model_id.lower() and
            think_mode
        )
        
        try:
            # Stream da resposta
            for chunk, meta in agent.stream(
                agent_input, 
                stream_mode="messages", 
                config=agent_config
            ):
                # Caso especial para Claude 3.7 Sonnet com thinking
                if is_claude_37_thinking:
                    # Extrair e processar o conteúdo do chunk específico para Claude 3.7
                    if hasattr(chunk, "content") and isinstance(chunk.content, list):
                        for item in chunk.content:
                            # Se for pensamento, enviar como thinking
                            if isinstance(item, dict) and "thinking" in item:
                                thinking_content = item.get("thinking", "")
                                
                                payload = {
                                    "content": thinking_content,
                                    "type": "thinking",
                                    "meta": meta
                                }
                                yield f"data: {json.dumps(payload)}\n\n"
                                
                            # Se for texto da resposta
                            elif isinstance(item, dict) and "text" in item:
                                text_content = item.get("text", "")
                                
                                payload = {
                                    "content": text_content,
                                    "type": "text",
                                    "meta": meta
                                }
                                yield f"data: {json.dumps(payload)}\n\n"
                    
                    # Se for o final da resposta e vazio
                    elif hasattr(chunk, "content") and chunk.content == "":
                        # Já enviamos todos os chunks, ignorar
                        pass
                    else:
                        # Fallback para outros formatos
                        if hasattr(chunk, "content"):
                            content = chunk.content
                            payload = {"content": content, "type": "text", "meta": meta}
                            yield f"data: {json.dumps(payload)}\n\n"
                
                # Caso padrão para outros modelos
                else:
                    if hasattr(chunk, "content"):
                        content = chunk.content
                        
                        payload = {"content": content, "type": "text", "meta": meta}
                        yield f"data: {json.dumps(payload)}\n\n"
            
            # Marcar fim do streaming
            yield f"data: {json.dumps({'content': '[DONE]', 'type': 'end'})}\n\n"
            
        except Exception as e:
            # Em caso de erro durante o streaming
            error_payload = {
                "content": str(e),
                "type": "error",
                "error_type": type(e).__name__
            }
            yield f"data: {json.dumps(error_payload)}\n\n"
            yield f"data: {json.dumps({'content': '[DONE]', 'type': 'end'})}\n\n" 