from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class DocumentBase(BaseModel):
    document_name: str
    subject: str
    document_link: str

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    document_name_original: str
    document_name: Optional[str]
    subject: Optional[str]

class DocumentInDB(DocumentBase):
    document_id: int
    document_link: str
    uploaded_by: str
    upload_date: datetime

    class Config:
        from_attributes = True

class DocumentDelete(BaseModel):
    document_id: int    
class Document(DocumentInDB):
    pass

class ConnectionBase(BaseModel):
    authorname : str
    authoremail: Optional[str]
    primary_author: Optional[bool]

class ConnectionCreate(ConnectionBase):
    pass

class ConnectionUpdate(BaseModel):
    conn_id: int
    authorname: Optional[str]
    authoremail: Optional[str]
    primary_author: Optional[bool]

class ConnectionInDB(ConnectionBase):
    conn_id: int
    authorname: str
    authoremail: str
    document_conn: int
    primary_author: bool

class AuthorConnection(ConnectionInDB):
    pass