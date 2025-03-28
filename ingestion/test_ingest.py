import sys
import os
import argparse
from dotenv import load_dotenv

# Garantir que o diretório raiz está no path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database.session import get_db
from ingestion.ingestor import DocumentIngestor

def main():
    """
    Script para testar a ingestão de um documento.
    
    Uso:
        python -m ingestion.test_ingest <document_id>
    """
    # Configurar parser de argumentos
    parser = argparse.ArgumentParser(description="Teste de ingestão de documentos")
    parser.add_argument("document_id", type=int, help="ID do documento a ser processado")
    args = parser.parse_args()
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Obter sessão do banco de dados
    db = next(get_db())
    
    try:
        # Inicializar ingestor
        ingestor = DocumentIngestor(db_session=db)
        
        # Processar documento
        print(f"Iniciando processamento do documento ID: {args.document_id}")
        result = ingestor.ingest_document(args.document_id)
        
        # Exibir resultado
        print(f"Processamento concluído com sucesso:")
        print(f"- Documento ID: {result['document_id']}")
        print(f"- Chunks processados: {result['chunks_processed']}")
        print(f"- Índice Pinecone: {result['index_name']}")
        print(f"- Namespace: {result['namespace']}")
        
    except Exception as e:
        print(f"Erro ao processar documento: {str(e)}")
        raise

if __name__ == "__main__":
    main() 