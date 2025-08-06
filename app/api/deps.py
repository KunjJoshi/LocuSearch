from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from typing import Generator
import logging

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.schemas.token import TokenPayload

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl= f"{settings.PROJECT_URL_V1}/auth/login")

def get_current_user(
        db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
):
    credentials_exception = HTTPException(
        status_code= status.HTTP_401_UNAUTHORIZED,
        detail = "Could not Authorize: Invalid Credentials",
        headers = {"WWW-Authenticate":"Bearer"}
    )

    try:
        logger.info(f"Attempting to decode token: {token[:20]}...")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms = [settings.ALGORITHM])
        logger.info(f"Token decoded successfully. Payload keys: {list(payload.keys())}")
        
        username: str = payload.get("sub")
        if username is None:
            logger.error("Token payload missing 'sub' field")
            raise credentials_exception
            
        logger.info(f"Token subject (username): {username}")
        token_data = TokenPayload(sub = username)
        
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error in token validation: {e}")
        raise credentials_exception
    
    user = db.query(User).filter(User.username == token_data.sub).first()
    if user is None:
        logger.error(f"User not found in database: {token_data.sub}")
        raise credentials_exception
    
    if not user.is_active:
        logger.error(f"Inactive user attempted access: {user.username}")
        raise HTTPException(status_code = status.HTTP_400_BAD_REQUEST, detail = "Inactive User")
    
    logger.info(f"Authentication successful for user: {user.username}")
    return user
