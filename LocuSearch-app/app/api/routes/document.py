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
import weaviate
from sentence_transformers import SentenceTransformer
from langchain_community.document_loaders.pdf import BasePDFLoader
import fitz
import re
import tempfile
import json

router = APIRouter()
embedder = SentenceTransformer("intfloat/e5-base")

class WeaviateDB:
    def __init__(self, url_link):
        self.client = weaviate.Client(url = url_link)
    
    def ensure_schema(self):
        if not self.client.schema.contains({"class":"Document"}):
            self.client.schema.create_class(
                {
                    "class":"Document",
                    "properties": [
                        {"name": "text", "dataType":["text"]},
                        {"name":"source", "dataType":["text"]},
                        {"name":"page", "dataType":["text"]},
                        {"name":"title", "dataType":["text"]},
                        {"name":"authors", "dataType":["text[]"]}
                    ],
                    "vectorizer": "none"
                }
            )
    
    def upload_file(self, chunks):
        for chunk in chunks:
            embedding = embedder.encode(chunk["text"])
            self.client.data_object.create(
                {
                    "text" : chunk["text"],
                    "source": chunk["metadata"]["source"],
                    "page": chunk["metadata"]["page"],
                    "title": chunk["paper-name"],
                    "authors": chunk["authors"]
                },
                class_name = "Document",
                vector = embedding
            )
    
    def upload_folder(self, doc_directory, loader, metadata):
        all_files = os.listdir(doc_directory)
        for index, filename in all_files:
            try:
              file_path = os.path.join(doc_directory, filename)
              chunks = loader.load(file_path, metadata[index]['title'], metadata[index]['authors'])
              self.upload_file(chunks)

            except Exception as e:
                print(e)        

    def retrieve(self, query, embedder = embedder):
        query_vector = embedder.encode(query)
        results = self.client.query.get("Document", ["text", "source", "page", "title", "authors"]).with_near_vector({"vector":query_vector}).with_additional(["certainty"]).with_limit(20).do()
        return results['data']['Get']['Document']
    
    def delete(self, title:str):
       try:
          results = self.client.batch.delete_objects(
             class_name = "Document",
             where = {
                "path": ['title'],
                "operator":"Equal",
                "valueText":title
             }
          )

          print(results)
          if results and "results" in results:
             if results['results']['failed'] == 0 and results['results']['successful'] != 0:
               return {
                  "success":True,
                  "message":f"Deleted {results['results']['successful']} items from the Vector Store",
               }
          else:
             return {
                "success":False,
                "message":"Could not find any items in Vector Store"
             }
       except Exception as e:
          return {
             "success":False,
             "message":f"{e}: Error encountered in deleting from Vector Store"
          }


class PDFLoader(BasePDFLoader):
    def __init__(self, embedder: SentenceTransformer = embedder) -> None:
        self.embedder = embedder
    
    def load(self, file_name, document_name, authors_list, file_link):
        doc = fitz.open(file_name)
        documents = []
        for pageNum, page in enumerate(doc):
            blocks = page.get_text("blocks")
            full_text = ""
            for block in blocks:
                block_text = block[4]
                block_type = block[6] if len(block)>6 else 0
                if block_type == 0:
                    full_text = full_text + block_text + "\n"
                else:
                    continue
            
            full_text = full_text.replace("\n", " ")
            full_text = full_text.replace("- ", "")
            sentences = re.split(r'(?<=[.?!])\s+', full_text)

            
            for start in range(len(sentences) - 2):
                chunk = ' '.join(sent for sent in sentences[start:start+3])
                documents.append({
                    "text" : chunk,
                    "paper-name": document_name,
                    "authors": authors_list,
                    "metadata" : {
                        "page": str(pageNum + 1),
                        "source": file_link,
                    }
                })
        return documents

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

async def chunk_and_upload(file: UploadFile, file_name: str, authors_list: List[str]):
   temp_file_path = None
   try:
      allowed_type = set(["application/pdf"])
      if file.content_type not in allowed_type:
         raise Exception(f"Unsupoported File Type")
      file_content = await file.read()
      if len(file_content) > 5 * 1024 * 1024:
         raise Exception("Too large of a file. (Max Upload: 5MB)")
      await file.seek(0)
      s3_url = await upload_file(file)
      file_extension = Path(file.filename).suffix
      temp_filename = f"{uuid.uuid4()}{file_extension}"
      temp_file_path = os.path.join(tempfile.gettempdir(), temp_filename)
      with open(temp_file_path, "wb") as temp_file:
        temp_file.write(file_content)
      documents = loader.load(temp_file_path, file_name, authors_list, s3_url)
      weaviate_client.upload_file(documents)
      return s3_url
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
        doc_link = await chunk_and_upload(file, doc_name, author_list)
        doc = Document(
            document_name = doc_name,
            document_link = doc_link,
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
      return all_papers
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
