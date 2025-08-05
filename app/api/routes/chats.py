from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.models.chats import QuerySearch, Chat, ChatMessage
from app.schemas.chats import QueryBase, QueryInDB, QueryDelete, MessageBase, MessageInDB, SendMessage, OpenChat    
from app.helpers.llm import TITLE_GENERATOR, ANSWER_CREATOR

import base64
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
load_dotenv()

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

router = APIRouter()

@router.get('/all-searches')
def get_all_searches(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.user_id
        all_searches = db.query(QuerySearch).filter(QuerySearch.user_id == user_id).order_by(QuerySearch.created_at.desc())
        search_titles = []
        for search in all_searches:
            search_titles.append(
                {
                    "title":search.title,
                    "query_id":search.query_id
                }
            )
        message = {"error":False, "titles":search_titles}
        return message
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error in fetching your data: {e}")
    
@router.post('/search')
def search(query: QueryBase, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.user_id
        eapi = current_user.api_key
        
        print(eapi)
        # Validate API key
        if not eapi:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key is required")
        
        # Decrypt the API key
        try:
            if not ENCRYPTION_KEY:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Encryption key not configured")
            
            cipher = Fernet(ENCRYPTION_KEY.encode())
            
            encrypted_key = base64.urlsafe_b64decode(eapi)
            decrypted = cipher.decrypt(encrypted_key).decode('utf-8')
            api_key = decrypted
            print("API Key Decrypted successfully")
                
        except Exception as e:
            print(f"Error decrypting API key: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to decrypt API key")
        
        query = query.query
        title = TITLE_GENERATOR.title(query, api_key=api_key)
        response = ANSWER_CREATOR.generate(query, api_key=api_key)

        if title['error']:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=title['message'])

        if response['error']:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=response['message'])
        else:
           search = QuerySearch(
            query = query,
            title = title['title'],
            user_id = user_id,
           )

           db.add(search)
           db.flush()

           chat =  Chat(
            parent_query_id = search.query_id
           )   
           db.add(chat)
           db.flush()
           search.chat_id = chat.chat_id

           human_message = ChatMessage(
            parent_chat_id = chat.chat_id,
            role = "HUMAN",
            content = query
           )

           machine_response = ChatMessage(
            parent_chat_id = chat.chat_id,
            role = "MACHINE",
            content = response['message']
           )
           db.add(human_message)
           db.add(machine_response)
           db.commit()
           db.refresh(search)
           db.refresh(chat)
           db.refresh(human_message)
           db.refresh(machine_response)

           message = {
            "error":False,
            "query_id":search.query_id,
            "response": response['message']
           }
           return message
    except Exception as e:
        print(e)
        raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR, detail = f"Error in searching: {e}")

@router.get("/open_chat")
def open_chat(query_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.user_id
        query_item = db.query(QuerySearch).filter(QuerySearch.query_id == query_id).first()
        
        if not query_item:
            raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Chat not found")
        
        if query_item.user_id != user_id:
            raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED, detail = "You are not authorized to open this chat")
        else:
            chat_item = db.query(Chat).filter(Chat.parent_query_id == query_id).first()
            message_history = []
            messages = db.query(ChatMessage).filter(ChatMessage.parent_chat_id == chat_item.chat_id).order_by(ChatMessage.sent.asc())
            for message in messages:
                message_history.append(
                    {
                        "role":message.role,
                        "content": message.content
                    }
                )
            response = {"error":False, "message_history":message_history, "chat_id":query_id}
            return response
    except Exception as e:
        raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR, detail = f"Error in opening chat: {e}")

@router.post("/ask")
def ask(message: SendMessage, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        chat_id = message.chat_id
        query = message.query
        user_id = current_user.user_id
        eapi = current_user.api_key
        
        print(eapi)
        # Validate API key
        if not eapi:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key is required")
        
        # Decrypt the API key
        try:
            if not ENCRYPTION_KEY:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Encryption key not configured")
            
            cipher = Fernet(ENCRYPTION_KEY.encode())
            
            encrypted_key = base64.urlsafe_b64decode(eapi)
            decrypted = cipher.decrypt(encrypted_key).decode('utf-8')
            api_key = decrypted
            print("API Key Decrypted successfully")
                
        except Exception as e:
            print(f"Error decrypting API key: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to decrypt API key")
        
        chat_item = db.query(Chat).filter(Chat.chat_id == chat_id).first()
        parent_query_id = chat_item.parent_query_id
        user_id = current_user.user_id
        query_item = db.query(QuerySearch).filter(QuerySearch.query_id == parent_query_id).first()
        print("User ID:" + str(user_id))
        print("Query Owner: " + str(query_item.user_id))
        if query_item.user_id != user_id:
            raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED, detail = "You are not authorized to ask this query")
        
        if not chat_item:
            raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Chat not found")
        else:
            message_history = []
            messages = db.query(ChatMessage).filter(ChatMessage.parent_chat_id == chat_item.chat_id).order_by(ChatMessage.sent.asc())
            for chat_message in messages:
                message_history.append(
                    {
                        "role":chat_message.role,
                        "content":chat_message.content
                    }
                )
            answer = ANSWER_CREATOR.continuous_response(query, message_history, api_key=api_key)
            if answer['error']:
                raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR, detail = answer['message'])
            else:
                response = answer['message']
                human_message = ChatMessage(
                    parent_chat_id = chat_item.chat_id,
                    role = "HUMAN",
                    content = query
                )
                ai_response = ChatMessage(
                    parent_chat_id = chat_item.chat_id,
                    role = "MACHINE",
                    content = response
                )
                db.add(human_message)
                db.add(ai_response)
                db.commit()
                db.refresh(human_message)
                db.refresh(ai_response)
                message = {
                    "error":False,
                    "message":response,
                    "chat_id":chat_id
                }
                return message
    except Exception as e:
        raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR, detail = f"Error in asking: {e}")

@router.delete("/delete_chat")
def delete_chat(query: QueryBase, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.user_id
        query = query.query
        query_item = db.query(QuerySearch).filter(QuerySearch.title == query, QuerySearch.user_id == user_id).first()
        if not query_item:
            raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Chat not found")
        else:
            chat_id = query_item.chat_id
            chat_item = db.query(Chat).filter(Chat.chat_id == chat_id).first()
            all_messages = db.query(ChatMessage).filter(ChatMessage.parent_chat_id == chat_id).all()
            for message in all_messages:
                db.delete(message)
            db.delete(chat_item)
            db.delete(query_item)

            db.commit()
            message = {"error":False, "message":"Chat deleted successfully"}
            return message
    except Exception as e:
        message = {"error":True, "message":str(e)}
        return message
