from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import validates
import re

from app.db.database import Base
from app.core.config import settings

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key= True, index = True)

    user_id = Column(String, index = True)
    username = Column(String, unique = True, index = True)
    email = Column(String, index = True, unique = True)
    hashed_password = Column(String)
    google_scholar_link = Column(String, nullable = True)
    organization = Column(String, nullable = True)
    affiliation = Column(String, nullable = True)
    name = Column(String)

    is_active = Column(Boolean, default = True)

    @validates('email')
    def validate_email(self, key, email):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Invalid Email Format")
        return email
    