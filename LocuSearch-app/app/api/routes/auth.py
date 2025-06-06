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
from app.schemas.user import UserCreate, User as UserSchema, UserUpdate, PasswordUpdate

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

    print(user_in.password)
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
    print("In login module")
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

    return {"access_token": str(access_token), "token_type":"bearer"}

@router.get("/me", response_model = UserSchema)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/update-user", response_model = UserSchema)
def update_user(update_deets: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):

    if update_deets.username and update_deets.username != current_user.username:
        user = db.query(User).filter(User.username == update_deets.username).first()
        if user:
            raise HTTPException(status_code = status.HTTP_400_BAD_REQUEST, detail = "Username already registered")
    
    if update_deets.email and update_deets.email != current_user.email:
        user = db.query(User).filter(User.email == update_deets.email).first()
        if user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail = "Email already taken")
    
    update_data = update_deets.dict(exclude_unset = True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.put("/update-password")
def update_password(pass_deets: PasswordUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):

    if not verify_password(pass_deets.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail = "Wrong Password Input")
    
    try:
        new_hash = get_password_hash(pass_deets.password)
        current_user.hashed_password = new_hash
        db.commit()
        db.refresh(current_user)
        return {"error":"False", "message":"Password updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail = "Error occurred in updating password")

