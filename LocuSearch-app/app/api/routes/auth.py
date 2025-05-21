from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import get_password_hash, verify_password, create_access_token
from app.db.database import get_db
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, User as UserSchema

router = APIRouter()

@router.post("/register", response_model = UserSchema)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_in.username).first()

    if user:
        raise HTTPException(status_code = status.HTTP_400_BAD_REQUEST, detail = "Username already registered, please use another username")
    
    user = db.query(User).filter(User.email == user_in.email).first()

    if user:
        raise HTTPException(status_code = status.HTTP_400_BAD_REQUEST, detail = "Email already registered")
    
    last_user = db.query(User).order_by(User.id.desc()).first()
    next_id = 1 if not last_user else last_user.id + 1
    formatted_id = settings.USER_ID_FORMAT.format(next_id)

    user = User(
        email = user_in.email,
        username = user_in.username,
        name = user_in.name,
        user_id = formatted_id,
        hashed_password = get_password_hash(user_in.password),
        google_scholar_link = user_in.google_scholar_link,
        organization = user_in.organization,
        affiliation = user_in.affiliation
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user

@router.post("/login", response_model = Token)
def login_for_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail = "Incorrect Username or password",
            headers = {"WWW-Authenticate":"Bearer"}
        )
    
    if not user.is_active:
        raise HTTPException(status_code = status.HTTP_400_BAD_REQUEST, detail = "Inactive User")
    
    access_token_expires = timedelta(settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(subject = form_data.username, expires_delta = access_token_expires)

    return {"access_token": access_token, "token_type":"bearer"}

@router.get("/me", response_model = UserSchema)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

