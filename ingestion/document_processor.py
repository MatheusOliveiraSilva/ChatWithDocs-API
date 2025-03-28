import os
import tempfile
import boto3
from typing import List, Dict, Any, Optional, Tuple
import PyPDF2
from langchain_text_splitters import RecursiveCharacterTextSplitter
import docx
import io

from ingestion.config import CHUNK_SIZE, CHUNK_OVERLAP

class DocumentProcessor:
    """
    Classe para processamento de documentos: download do S3,
    extração de texto e chunking.
    """
    
    def __init__(self, s3_client=None):
        """
        Inicializar o processador de documentos com um cliente S3 opcional.
        """
        self.s3_client = s3_client or boto3.client(
            's3',
            aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
            region_name=os.getenv("S3_REGION_NAME"),
            endpoint_url=os.getenv("S3_ENDPOINT_URL")
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def download_from_s3(self, bucket: str, key: str) -> Tuple[str, str]:
        """
        Baixa um arquivo do S3 para um arquivo temporário.
        
        Args:
            bucket: Nome do bucket S3
            key: Path do arquivo no S3
            
        Returns:
            Caminho para o arquivo temporário e o tipo de arquivo
        """
        # Criar arquivo temporário com a extensão correta
        _, file_extension = os.path.splitext(key)
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Baixar o arquivo
        self.s3_client.download_file(bucket, key, temp_path)
        
        # Determinar o tipo MIME com base na extensão
        mime_type = self._get_mime_type(file_extension)
        
        return temp_path, mime_type
    
    def _get_mime_type(self, extension: str) -> str:
        """Retorna o tipo MIME com base na extensão do arquivo."""
        extension = extension.lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
        }
        return mime_types.get(extension, 'application/octet-stream')
    
    def extract_text(self, file_path: str, mime_type: str) -> str:
        """
        Extrai texto de diferentes formatos de arquivo.
        
        Args:
            file_path: Caminho para o arquivo
            mime_type: Tipo MIME do arquivo
            
        Returns:
            Texto extraído do documento
        """
        if mime_type == 'application/pdf':
            return self._extract_from_pdf(file_path)
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return self._extract_from_docx(file_path)
        elif mime_type in ['text/plain', 'text/markdown']:
            return self._extract_from_text(file_path)
        else:
            raise ValueError(f"Formato não suportado: {mime_type}")
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extrai texto de um arquivo PDF."""
        text = ""
        with open(file_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
        return text
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extrai texto de um arquivo DOCX."""
        doc = docx.Document(file_path)
        return "\n\n".join([para.text for para in doc.paragraphs])
    
    def _extract_from_text(self, file_path: str) -> str:
        """Extrai texto de um arquivo de texto."""
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    
    def create_chunks(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Divide o texto em chunks com metadados.
        
        Args:
            text: Texto completo do documento
            metadata: Metadados do documento
            
        Returns:
            Lista de dicionários com texto e metadados
        """
        chunks = self.text_splitter.create_documents([text])
        
        # Adicionar metadados e número do chunk
        result = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_index": i,
                "chunk_total": len(chunks)
            })
            
            result.append({
                "content": chunk.page_content,
                "metadata": chunk_metadata
            })
        
        return result
    
    def process_document(self, bucket: str, key: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Processa um documento completo: download, extração e chunking.
        
        Args:
            bucket: Nome do bucket S3
            key: Path do arquivo no S3
            metadata: Metadados do documento
            
        Returns:
            Lista de chunks com metadados
        """
        try:
            # Download do documento
            temp_path, mime_type = self.download_from_s3(bucket, key)
            
            # Extrair texto
            text = self.extract_text(temp_path, mime_type)
            
            # Criar chunks
            chunks = self.create_chunks(text, metadata)
            
            # Limpar arquivo temporário
            os.unlink(temp_path)
            
            return chunks
        except Exception as e:
            # Em caso de erro, limpar arquivo temporário se existir
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except:
                    pass
            raise e 