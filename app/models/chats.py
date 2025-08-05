from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import re
from datetime import datetime

from app.db.database import Base
from app.core.config import settings

class QuerySearch(Base):
    __tablename__ = "query"
    query_id = Column(Integer, primary_key=True, index = True)
    query = Column(String, nullable = False)
    title = Column(String, nullable = False)
    user_id = Column(String, ForeignKey('users.user_id'), index = True)
    chat_id = Column(Integer, ForeignKey('chats.chat_id'), index = True, nullable = True)
    created_at = Column(DateTime, default = datetime.utcnow, index = True)

class Chat(Base):
    __tablename__ = "chats"
    chat_id = Column(Integer, primary_key=True, index = True)
    parent_query_id = Column(Integer, ForeignKey('query.query_id'), index = True)

class ChatMessage(Base):
    __tablename__ = "messages"
    message_id = Column(Integer, primary_key = True, index = True)
    parent_chat_id = Column(Integer, ForeignKey('chats.chat_id'), nullable = False, index = True)
    role = Column(String, nullable = False)
    content = Column(String, nullable = False)
    sent = Column(DateTime, default = datetime.utcnow)
