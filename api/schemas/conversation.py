from typing import List, Optional
from pydantic import BaseModel
import datetime

class ConversationCreate(BaseModel):
    thread_id: str
    thread_name: str
    first_message_role: str = "user"
    first_message_content: str

class ConversationUpdate(BaseModel):
    thread_id: str
    # Definimos que "messages" é uma lista de listas [role, content]
    messages: List[List[str]]

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    thread_id: str
    thread_name: str
    messages: List[List[str]]
    created_at: datetime.datetime
    last_used: datetime.datetime 