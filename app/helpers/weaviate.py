import weaviate
from sentence_transformers import SentenceTransformer
from langchain_community.document_loaders.pdf import BasePDFLoader
import pymupdf as fitz
import re
import os

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