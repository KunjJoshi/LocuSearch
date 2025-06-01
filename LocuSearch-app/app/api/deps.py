from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from typing import Generator

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.schemas.token import TokenPayload

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
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms = [settings.ALGORITHM])
        username :str = payload.get("sub")
        if username is None:
            print("username not provided")
        token_data = TokenPayload(sub = username)
    except JWTError as e:
        print(e)
        raise credentials_exception
    
    user = db.query(User).filter(User.username == token_data.sub).first()
    if user is None:
        print("User does not exist")
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(status_code = status.HTTP_400_BAD_REQUEST, detail = "Inactive User")
    return user
