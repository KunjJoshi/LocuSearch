from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import validates, relationship
import re
from datetime import datetime

from app.db.database import Base
from app.core.config import settings

class Document(Base):
    __tablename__ = "documents"
    document_id = Column(Integer, primary_key = True, index = True)
    document_name = Column(String, nullable = False)
    document_link = Column(String, unique = True)
    uploaded_by = Column(String, ForeignKey('users.user_id'), index = True)
    upload_date = Column(DateTime, default = datetime.utcnow)
    subject = Column(String, index = True, nullable =True)

    authors = relationship("AuthorConnection", back_populates="document", cascade="all, delete-orphan")

class AuthorConnection(Base):
    __tablename__ = "authors"

    conn_id = Column(Integer, unique = True, primary_key=True, index=True)
    authorname = Column(String, nullable = False)
    authoremail = Column(String, nullable=True)
    document_conn = Column(Integer, ForeignKey('documents.document_id'))
    primary_author = Column(Boolean, default = False)

    document = relationship("Document", back_populates="authors")