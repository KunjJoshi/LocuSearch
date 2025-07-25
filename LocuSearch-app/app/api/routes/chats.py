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
    
    