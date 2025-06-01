from langchain.llms import HuggingFacePipeline
from langchain.vectorstores import Weaviate
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_community.document_loaders.pdf import BasePDFLoader
from langchain.text_splitter import CharacterTextSplitter

import weaviate
import fitz
import os
import torch
import re
from sentence_transformers import SentenceTransformer
from langchain.docstore.document import Document
from transformers import pipeline, AutoModelForSeq2SeqLM, AutoTokenizer
from huggingface_hub import hf_hub_download

DOC_DIRECTORY = "data/pdf"
MODEL_CHECKPOINT = "google/flan-t5-base"

tokenizer = AutoTokenizer.from_pretrained(MODEL_CHECKPOINT, trust_remote_code = True)

model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_CHECKPOINT, torch_dtype = "auto", device_map = "auto")

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

class PDFLoader(BasePDFLoader):
    def __init__(self, embedder: SentenceTransformer = embedder) -> None:
        self.embedder = embedder
    
    def load(self, file_name, document_name, authors_list):
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
                        "source": file_name,
                    }
                })
        return documents

file_path = os.path.join(DOC_DIRECTORY, "AlinaOprea1.pdf")
file_path

loader = PDFLoader()
database = WeaviateDB("http://localhost:8080")
documents = loader.load(file_path, "User Inference Attacks on Large Language Models", ["Alina Oprea", "Nikhil Kandpal", "Zheng Xu"])

database.ensure_schema()
database.upload_file(documents)

if __name__ == "__main__":
    query = "query: Which family of Large Language Models (LLMs) were used by Alina Oprea and her team for User Inference Attacks experiments?"
    results = database.retrieve(query)
    context = "Answer the following question based on the data provided to you: \n"
    context = context + "Question: \n"
    context = context + query.replace("query: ", "")
    context = context + "\nProvided Data for answering Query: \n"
    cont_num = 0
    for ind, res in enumerate(results):
        if res['_additional']['certainty'] >= 0.9:
            context = context + f"{cont_num + 1}) " + res['text'] + '\n'
            context = context + "Source: " + res['source'] + "\n"
            context = context + "Title of Paper: " + res['title'] + "\n"
            context = context + "Authors: " + ', '.join(auth for auth in res['authors']) + "\n"
            cont_num += 1
    
    context = context + "\nProvide citations from the context you generated your answer in MLA Format"
    inputs = tokenizer(context, return_tensors = "pt", padding = 'max_length', truncation = False)
    device = torch.device("mps")
    inputs = {k:v.to(device) for k,v in inputs.items()}
    output = model.generate(input_ids = inputs['input_ids']
                        , attention_mask = inputs['attention_mask'],
                        num_beams = 1,
                        top_p = 0.95,
                        max_new_tokens = 200,
                         do_sample = True)
    response = tokenizer.decode(output[0], skip_special_tokens=True)
    print(response)

