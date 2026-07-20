from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.chat import chat_router, chats_router
from app.logging import setup_logging

# Setup structlog structured logging
setup_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title="Document Copilot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chats_router, prefix="/chats", tags=["chats"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
# Forced reload after environment config update

