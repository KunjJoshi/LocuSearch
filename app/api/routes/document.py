from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path

from app.api.deps import get_current_user
from app.core.config import settings
import boto3
from app.db.database import get_db
from app.models.document import Document, AuthorConnection
from app.schemas.document import DocumentCreate, Document as DocSchema, DocumentUpdate, ConnectionCreate, AuthorConnection as ConnSchema, ConnectionUpdate, DocumentDelete
from app.schemas.user import User as UserSchema
from app.models.user import User
from botocore.exceptions import ClientError, NoCredentialsError
import uuid
import os
import tempfile
import json
from app.helpers.weaviate import WeaviateDB, PDFLoader

router = APIRouter()

weaviate_host = settings.WEAVIATE_URL
weaviate_client = WeaviateDB(weaviate_host)
loader = PDFLoader()

try:
   weaviate_client.ensure_schema()
except Exception as e:
   pass

s3 = boto3.client(
   "s3",
   region_name = settings.AWS_REGION,
   aws_access_key_id = settings.AWS_ACCESS_KEY,
   aws_secret_access_key = settings.AWS_SECRET_KEY
)

async def upload_file(file: UploadFile, location: str = 'pdfs'):
   try:
      file_extension = Path(file.filename).suffix
      unique_filename = f"{uuid.uuid4()}{file_extension}"
      s3_key = f"{location.strip('/')}/{unique_filename}"
      file_content = await file.read()
      await file.seek(0)
      s3.put_object(
         Bucket = settings.AWS_BUCKET_NAME,
         Key = s3_key,
         Body = file_content,
         ContentType = file.content_type
         #ACL = "public-read"
      )
      s3_url = f"https://{settings.AWS_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
      return s3_url
   except ClientError as e:
      raise Exception(f"Failed to upload to s3 : {e}")
   except Exception as e:
      raise Exception(f"Error in uploading: {e}")

async def chunk_and_upload(file: UploadFile, file_name: str, authors_list: List[str], file_link: str):
   temp_file_path = None
   try:
      allowed_type = set(["application/pdf"])
      if file.content_type not in allowed_type:
         raise Exception(f"Unsupoported File Type")
      file_content = await file.read()
      if len(file_content) > 5 * 1024 * 1024:
         raise Exception("Too large of a file. (Max Upload: 5MB)")
      #await file.seek(0)
      #s3_url = await upload_file(file)
      file_extension = Path(file.filename).suffix
      temp_filename = f"{uuid.uuid4()}{file_extension}"
      temp_file_path = os.path.join(tempfile.gettempdir(), temp_filename)
      with open(temp_file_path, "wb") as temp_file:
        temp_file.write(file_content)
      documents = loader.load(temp_file_path, file_name, authors_list, file_link)
      weaviate_client.upload_file(documents)
   except Exception as e:
      raise Exception(f"Error in Chunking and Uploading file: {e}")
   finally:
       if temp_file_path and os.path.exists(temp_file_path):
         try:
            os.remove(temp_file_path)
            print(f"Temporary file deleted: {temp_file_path}")
         except Exception as cleanup_error:
            print(f"Warning: Could not delete temporary file: {cleanup_error}")

@router.post('/upload', response_model = DocSchema)
async def upload_document(document_data: str =  Form(...), authors: str = Form(...), file: UploadFile = File(...),
                     db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    try:
       doc_data = DocumentCreate.parse_raw(document_data)
       #print(doc_data)
       autho_list = json.loads(authors)
       authors_data = [ConnectionCreate(**autho) for autho in autho_list]
    except Exception as e:
       raise HTTPException(status_code = status.HTTP_406_NOT_ACCEPTABLE, detail = "Not Acceptable JSON")
    
    doc_name = doc_data.document_name
    document = db.query(Document).filter(Document.document_name == doc_name).first()
    if document:
        raise HTTPException(status_code = status.HTTP_409_CONFLICT, detail="Document already exists in Database")
    
    else:
      try:
        uploader_id = current_user.user_id
        author_list = []
        for author in authors_data:
            author_list.append(author.authorname)
        await chunk_and_upload(file, doc_name, author_list, doc_data.document_link)
        doc = Document(
            document_name = doc_name,
            document_link = doc_data.document_link,
            uploaded_by = uploader_id,
            subject = doc_data.subject
        )
        db.add(doc)
        db.flush()

        for author in authors_data:
            connection = AuthorConnection(
                authorname = author.authorname,
                authoremail = "" if not author.authoremail else author.authoremail,
                document_conn = doc.document_id,
                primary_author = False if not author.primary_author else author.primary_author
            )
            db.add(connection)
        
        db.commit()
        db.refresh(doc)
        return doc
      except Exception as e:
         db.rollback()
         print(e)
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail = "Error occured in uploading document!")

@router.get('/all-papers')
def get_all_papers(db: Session = Depends(get_db)):
   try:
      all_papers = db.query(Document).all()
      papers = []
      for paper in all_papers:
         papers.append({
            "doc_id":paper.document_id,
            "doc_name":paper.document_name
         })
      return {"error":False, "papers":papers}
   except Exception as e:
      raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail = "Error in fetching papers!")

@router.delete('/delete')
def delete_document(document: DocumentDelete,db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
   try:
      doc = db.query(Document).filter(Document.document_id == document.document_id).first()
      if doc:
         doc_uploader = doc.uploaded_by
         if current_user.user_id == doc_uploader:
            title = doc.document_name
            message = weaviate_client.delete(title)
            db.delete(doc)
            db.commit()
            if message["success"]:
               return {"success":True, "message":f"{message['message']}"}
            else:
               return {"success":True, "message":"Failure in deleting from Vectorstore"}
         else:
            raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED, detail = "Ask the uploader to delete the Document!")
      else:
         raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Document not found")
   except Exception as e:
      raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR, detail = f"{e}, Error in deleting paper!")

@router.get('/doc-details')
def document_details(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
   try:
      user_id = current_user.user_id
      document = db.query(Document).filter(Document.document_id == doc_id).first()
      if not document:
         raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Document not found")
      
      authors = db.query(AuthorConnection).filter(AuthorConnection.document_conn == doc_id).all()
      author_list = []
      for author in authors:
         author_list.append({
            "author_name":author.authorname,
            "author_email":author.authoremail,
            "primary_author":author.primary_author
         })
      
      uploaded_by = db.query(User).filter(User.user_id == document.uploaded_by).first()
      uploader = uploaded_by.name
      response = {
         "error":False,
         "doc_id":document.document_id,
         "doc_name":document.document_name,
         "doc_link":document.document_link,
         "subject":document.subject,
         "uploaded_by": uploader,
         "authors":author_list,
         "doc_owner": user_id == document.uploaded_by
      }
      return response
   except Exception as e:
      print(e)
      raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR, detail = "Error in fetching document details!")
