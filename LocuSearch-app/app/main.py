from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth
from app.core.config import settings
from app.db.database import Base, engine

Base.metadata.create_all(bind = engine)

app = FastAPI(
    title = settings.PROJECT_NAME,
    openapi_url = f"{settings.PROJECT_URL_V1}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

app.include_router(auth.router, prefix = f"{settings.PROJECT_URL_V1}/auth", tags = ["authentication"])

@app.get("/")
def root():
    return {"message": "Welcome to LocuSearch"}

