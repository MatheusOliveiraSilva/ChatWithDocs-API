from typing import Optional, Dict, List, Any
from pydantic import BaseModel
from datetime import datetime

class DocumentCreate(BaseModel):
    original_filename: str
    mime_type: str
    file_size: int
    thread_id: str
    
class DocumentResponse(BaseModel):
    id: int
    user_id: int
    thread_id: str
    conversation_id: int
    filename: str
    original_filename: str
    s3_path: str
    mime_type: str
    file_size: int
    is_processed: bool
    index_status: str
    doc_metadata: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    
class DocumentChunkResponse(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    chunk_metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True

class DocumentDownloadResponse(BaseModel):
    download_url: str
    expires_in: int  # segundos até a expiração da URL
    filename: str 