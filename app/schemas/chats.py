from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class QueryBase(BaseModel):
    query: str 

class QueryCreate(QueryBase):
    pass

class QueryInDB(BaseModel):
    query_id: int
    query: str
    user_id: str
    chat_id: int
    title: str

class MessageBase(BaseModel):
    content: str
    chat_id: int

class QueryDelete(BaseModel):
    query_id: int

class MessageInDB(BaseModel):
    message_id: int
    content: str
    role: str
    sent: datetime

class OpenChat(BaseModel):
    query_id: int
class SendMessage(BaseModel):
    query: str
    chat_id: int
