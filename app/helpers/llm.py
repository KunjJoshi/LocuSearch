from torch._C import NoneType
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
from dotenv import load_dotenv
from app.api.routes.document import weaviate_client
import os
from langchain_openai import ChatOpenAI
import json


load_dotenv()
#MODEL_CHECKPOINT = "google/flan-t5-base"

environment = os.getenv("ENVIRONMENT", "test")
if environment == "test":
    api_key = None
else:
    api_key = os.getenv("CHATGPT_KEY")
#model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_CHECKPOINT, torch_dtype = "auto", device_map = "auto")
#tokenizer = AutoTokenizer.from_pretrained(MODEL_CHECKPOINT, trust_remote_code = True)


class TitleCreator(object):
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer
        self.llm = ChatOpenAI(api_key = api_key, model = "gpt-3.5-turbo", temperature = 0)
        self.prompt = "Write an appropriate title for the following Query: "
    
    def generate_query(self, query):
        if environment == "test":
            self.messages = self.prompt + "\n" + query
        else:
            self.messages = [{"role":"system", "content":self.prompt}, {"role":"user", "content":query}]
    
    def title(self, query, api_key = None):
        if api_key is not None:
            self.llm = ChatOpenAI(api_key = api_key, model = "gpt-3.5-turbo", temperature = 0)
        if environment == "test":
            if self.model is None and self.tokenizer is None:
                raise ValueError("Model and tokenizer must be provided")
            try:
                self.generate_query(query)
                inputs = self.tokenizer(self.messages, return_tensors = "pt", padding = 'max_length', truncation = False)
                device = torch.device("mps")
                inputs = {k:v.to(device) for k,v in inputs.items()}
                output = self.model.generate(input_ids = inputs['input_ids']
                                , attention_mask = inputs['attention_mask'],
                                num_beams = 1,
                                top_p = 0.95,
                                max_new_tokens = 15,
                                do_sample = True)
                response = self.tokenizer.decode(output[0], skip_special_tokens=True)
                self.generate_query("")
                return {"error":False, "title":response}
            except Exception as e:
                return {"error":True, "message":str(e)}
        else:
            try:
                self.generate_query(query)
                response = self.llm.invoke(self.messages)
                content = response.json()
                answer = json.loads(content)['content']
                return {"error":False, "title":answer}
            except Exception as e:
                return {"error":True, "message":str(e)}


class AnswerFetcher(object):
    def __init__(self, model, tokenizer, vectordb):
        self.model = model
        self.tokenizer = tokenizer
        self.vectordb = vectordb
        self.llm = ChatOpenAI(api_key = api_key, model = "gpt-3.5-turbo", temperature = 0)
    
    def fetch(self, query):
        try:
            results = self.vectordb.retrieve(query)
            return results
        except Exception as e:
            print(e)
            return []
    
    def generate(self, query, api_key = None):
        if api_key is not None:
            self.llm = ChatOpenAI(api_key = api_key, model = "gpt-3.5-turbo", temperature = 0)
        try:
            results = self.fetch(query)
            if not results:
                return {"error":True, "message":"Error in fetching data from VectorDB"}
            if environment == "test":
                if self.model is None and self.tokenizer is None:
                    raise ValueError("Model and tokenizer must be provided")
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
                inputs = self.tokenizer(context, return_tensors = "pt", padding = 'max_length', truncation = False)
                device = torch.device("mps")
                inputs = {k:v.to(device) for k,v in inputs.items()}
                output = self.model.generate(input_ids = inputs['input_ids']
                    , attention_mask = inputs['attention_mask'],
                    num_beams = 1,
                    top_p = 0.95,
                    max_new_tokens = 200,
                    do_sample = True)
                response = self.tokenizer.decode(output[0], skip_special_tokens=True)
                return {"error":False, "message":response}
            else:
                prompt = "You are a Helpful Research Assisting Agent, tasked with generating a response to the query using data and context provided to you and create MLA Citations for your answers. I will provide you with the context and finally the query you need to answer."
                message = "Context: \n"
                cont_num = 0
                for ind, res in enumerate(results):
                    if res['_additional']['certainty'] >= 0.9:
                        message = message + f"{cont_num + 1}) " + res['text'] + '\n'
                        message = message + "Source: " + res['source'] + "\n"
                        message = message + "Title of Paper: " + res['title'] + "\n"
                        message = message + "Authors: " + ', '.join(auth for auth in res['authors']) + "\n"
                        cont_num += 1
                message = message + "\n" + "Query: \n" + query
                messages = [{"role":"system", "content":prompt}, {"role":"user", "content":message}]
                response = self.llm.invoke(messages)
                content = response.json()
                answer = json.loads(content)['content']
                return {"error":False, "message":answer}
        except Exception as e:
            return {"error":True, "message":str(e)}
    
    def continuous_response(self, query, message_history, threshold = 10, api_key = None):
        if api_key is not None:
            self.llm = ChatOpenAI(api_key = api_key, model = "gpt-3.5-turbo", temperature = 0)
        try:
            history = ""
            if len(message_history) > threshold:
                message_history = message_history[-threshold:]
            for message in  message_history:
                history = history + message['role'] + ": " + message['content'] + "\n"

            results = self.fetch(history)
            if not results:
                return {"error":True, "message":"Error in fetching data from VectorDB"}
            
            if environment == "test":
                if self.model is None and self.tokenizer is None:
                    raise ValueError("Model and tokenizer must be provided")
                context = "You must answer the asked Query based on Chat History and Provided Context to you. I will first provide with the Chat History, the the Context and finally the Query. Use the provided data to answer the finally asked Query"
                context = context + "\n" + "Chat History:\n" + history            
                cont_num = 0
                for ind, res in enumerate(results):
                    if res['_additional']['certainty'] >= 0.9:
                        context = context + f"{cont_num + 1}) " + res['text'] + '\n'
                        context = context + "Source: " + res['source'] + "\n"
                        context = context + "Title of Paper: " + res['title'] + "\n"
                        context = context + "Authors: " + ', '.join(auth for auth in res['authors']) + "\n"
                        cont_num += 1
                context = context + "\n" + "Query:\n" + query
                context = context + "\n" + "Provide citations from the context you generated your answer in MLA Format"
                inputs = self.tokenizer(context, return_tensors = "pt", padding = 'max_length', truncation = False)
                device = torch.device("mps")
                inputs = {k:v.to(device) for k,v in inputs.items()}
                output = self.model.generate(input_ids = inputs['input_ids'],
                attention_mask = inputs['attention_mask'], 
                num_beams = 1,
                top_p = 0.95,
                max_new_tokens = 200,
                do_sample = True
                )
                response = self.tokenizer.decode(output[0], skip_special_tokens=True)
                return {"error":False, "message":response}
            else:
                prompt = "You are a Helpful Research Assisting Agent, tasked with generating a response to the query using data and context provided to you, as well as our previous Chat Historyand create MLA Citations for your answers. I will provide you with the context, certain amount of chat history and finally the query you need to answer."
                message = "Context: \n"
                cont_num = 0
                for ind, res in enumerate(results):
                    if res['_additional']['certainty'] >= 0.9:
                        message = message + f"{cont_num + 1}) " + res['text'] + '\n'
                        message = message + "Source: " + res['source'] + "\n"
                        message = message + "Title of Paper: " + res['title'] + "\n"
                        message = message + "Authors: " + ', '.join(auth for auth in res['authors']) + "\n"
                        cont_num += 1
                message = message + "\n" + "Chat History:\n" + history
                message = message + "\n" + "Query:\n" + query
                messages = [{"role":"system", "content":prompt}, {"role":"user", "content":message}]
                response = self.llm.invoke(messages)
                content = response.json()
                answer = json.loads(content)['content']
                return {"error":False, "message":answer}
        except Exception as e:
            return {"error":True, "message":str(e)}

TITLE_GENERATOR = TitleCreator(None, None)
ANSWER_CREATOR = AnswerFetcher(None, None, weaviate_client)
    
    
