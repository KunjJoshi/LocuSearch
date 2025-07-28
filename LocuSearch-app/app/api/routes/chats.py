from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.models.chats import QuerySearch, Chat, ChatMessage
from app.schemas.chats import QueryBase, QueryInDB, QueryDelete, MessageBase, MessageInDB
from app.helpers.llm import TITLE_GENERATOR, ANSWER_CREATOR

router = APIRouter()

@router.get('/all-searches')
def get_all_searches(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.user_id
        all_searches = db.query(QuerySearch).filter(QuerySearch.user_id == user_id).order_by(QuerySearch.created_at.desc())
        search_titles = []
        for search in all_searches:
            search_titles.append(search.title)
        message = {"error":False, "titles":search_titles}
        return message
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error in fetching your data: {e}")
    
@router.post('/search')
def search(query: QueryBase, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.user_id
        query = query.query
        title = TITLE_GENERATOR.title(query)
        response = ANSWER_CREATOR.generate(query)
        if response['error']:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=response['message'])
        else:
           search = QuerySearch(
            query = query,
            title = title,
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
           }
           return message
    except Exception as e:
        raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR, detail = f"Error in searching: {e}")

@router.get("/open_chat")
def open_chat(chat_title: QueryBase, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.user_id
        title = chat_title.query
        query_item = db.query(QuerySearch).filter(QuerySearch.title == title, QuerySearch.user_id == user_id).first()
        if not query_item:
            raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Chat not found")
        else:
            chat_id = query_item.chat_id
            chat_item = db.query(Chat).filter(Chat.chat_id == chat_id).first()
            message_history = []
            messages = db.query(ChatMessage).filter(ChatMessage.parent_chat_id == chat_item.chat_id).order_by(ChatMessage.sent.asc())
            for message in messages:
                message_history.append(
                    {
                        "role":message.role,
                        "content": message.content
                    }
                )
            response = {"error":False, "message_history":message_history}
            return response
    except Exception as e:
        raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR, detail = f"Error in opening chat: {e}")

