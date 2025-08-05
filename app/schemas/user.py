from typing import Optional
from pydantic import BaseModel, EmailStr, validator
import re

small_letters = set("abcdefghijklmnopqrstuvwxyz")
capital_letters = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
special_characters = set("~`!@#$%^&*()_-+=<>")
numbers = set("0123456789")
class UserBase(BaseModel):
    name: str
    username: str
    email: EmailStr
    google_scholar_link: Optional[str] = None
    organization: Optional[str] = None
    affiliation: Optional[str] = None
    api_key: str

class UserCreate(UserBase):
    password: str

    @validator('password')
    def password_strength(cls, v):
        def small_letters_in_password(v):
            for word in v:
                if word in small_letters:
                    return True
            return False
        
        def capital_letters_in_password(v):
            for word in v:
                if word in capital_letters:
                    return True
            return False
        
        def spec_chars_in_password(v):
            for word in v:
                if word in special_characters:
                    return True
            return False
        
        def num_in_password(v):
            for word in v:
                if word in numbers:
                    return True
            return False
        
        if len(v) < 8:
            raise ValueError("User Password must be Atleast 8 Characters long")
        
        if not small_letters_in_password(v):
            raise ValueError("User Password must contain atleast one Small Letter")
        
        if not capital_letters_in_password(v):
            raise ValueError("User Password must contain atleast one Capital Letter")
        
        if not spec_chars_in_password(v):
            raise ValueError("User Password must contain atleast One Special Character (~`!@#$%^&*()_-+=<>)")
        
        if not num_in_password(v):
            raise ValueError("User Password must contain a Number")
        return v
    

class UserUpdate(BaseModel):
    name : Optional[str] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    google_scholar_link: Optional[str] = None
    affiliation: Optional[str] = None
    organization: Optional[str] = None
    api_key: Optional[str] = None

class PasswordUpdate(BaseModel):
    current_password : str
    password: str
    @validator('password')
    def password_strength(cls, v):
        def small_letters_in_password(v):
            for word in v:
                if word in small_letters:
                    return True
            return False
        
        def capital_letters_in_password(v):
            for word in v:
                if word in capital_letters:
                    return True
            return False
        
        def spec_chars_in_password(v):
            for word in v:
                if word in special_characters:
                    return True
            return False
        
        def num_in_password(v):
            for word in v:
                if word in numbers:
                    return True
            return False
        
        if len(v) < 8:
            raise ValueError("User Password must be Atleast 8 Characters long")
        
        if not small_letters_in_password(v):
            raise ValueError("User Password must contain atleast one Small Letter")
        
        if not capital_letters_in_password(v):
            raise ValueError("User Password must contain atleast one Capital Letter")
        
        if not spec_chars_in_password(v):
            raise ValueError("User Password must contain atleast One Special Character (~`!@#$%^&*()_-+=<>)")
        
        if not num_in_password(v):
            raise ValueError("User Password must contain a Number")
        return v

class UserInDB(UserBase):
    user_id: str
    is_active: bool = True

    class Config:
        orm_mode = True

class User(UserInDB):
    pass

