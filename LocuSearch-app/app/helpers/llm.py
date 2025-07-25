from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch

from app.api.routes.document import weaviate_client

MODEL_CHECKPOINT = "google/flan-t5-base"

model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_CHECKPOINT, torch_dtype = "auto", device_map = "auto")
tokenizer = AutoTokenizer.from_pretrained(MODEL_CHECKPOINT, trust_remote_code = True)


class TitleCreator(object):
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer

        self.prompt = "Write an appropriate title for the following Query: "
    
    def generate_query(self, query):
        self.prompt = self.prompt + "\n" + query
    
    def title(self, query):
        try:
            self.generate_query(query)
            inputs = tokenizer(self.prompt, return_tensors = "pt", padding = 'max_length', truncation = False)
            device = torch.device("mps")
            inputs = {k:v.to(device) for k,v in inputs.items()}
            output = model.generate(input_ids = inputs['input_ids']
                                , attention_mask = inputs['attention_mask'],
                                num_beams = 1,
                                top_p = 0.95,
                                max_new_tokens = 15,
                                do_sample = True)
            response = tokenizer.decode(output[0], skip_special_tokens=True)
            self.generate_query("")
            return {"error":False, "title":response}
        except Exception as e:
            return {"error":True, "message":str(e)}


class AnswerFetcher(object):
    def __init__(self, model, tokenizer, vectordb):
        self.model = model
        self.tokenizer = tokenizer
        self.vectordb = vectordb
    
    def fetch(self, query):
        try:
            results = self.vectordb.retrieve(query)
            return results
        except Exception as e:
            print(e)
            return []
    
    def generate(self, query):
        try:
            results = self.fetch(query)
            if not results:
                return {"error":True, "message":"Error in fetching data from VectorDB"}
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
            return {"error":False, "response":response}
        except Exception as e:
            return {"error":True, "message":str(e)}



TITLE_GENERATOR = TitleCreator(model, tokenizer)
ANSWER_CREATOR = AnswerFetcher(model, tokenizer, weaviate_client)
    
    
