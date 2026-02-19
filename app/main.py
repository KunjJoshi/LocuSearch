from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, document, chats

print(f"Length of Document APIs: {len(document.router.routes)}")
from app.core.config import settings
from app.db.database import Base, engine

# Add this to your main.py, right after importing your settings
import os
print(f"Database URL: {settings.DATABASE_URL}")
if settings.DATABASE_URL.startswith('sqlite:///'):
    db_path = settings.DATABASE_URL.replace('sqlite:///', '')
    abs_path = os.path.abspath(db_path)
    print(f"Absolute database path: {abs_path}")
    print(f"File exists: {os.path.exists(abs_path)}")

#Base.metadata.create_all(bind = engine)

app = FastAPI(
    title = settings.PROJECT_NAME,
    openapi_url = f"{settings.PROJECT_URL_V1}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://locusearch.vercel.app",
        "https://locusearch-*.vercel.app"
    ],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

app.include_router(auth.router, prefix = f"{settings.PROJECT_URL_V1}/auth", tags = ["authentication"])
app.include_router(document.router, prefix = f"{settings.PROJECT_URL_V1}/document", tags = ["document"])
app.include_router(chats.router, prefix = f"{settings.PROJECT_URL_V1}/chats", tags = ["chats"])

@app.get("/")
def root():
    return {"message": "Welcome to LocuSearch"}

