from pydantic import BaseModel
from typing import Optional, List


class MessageParam(BaseModel):
    role: str
    content: str


class ChatStreamRequest(BaseModel):
    messages: List[MessageParam]
    thread_id: str

    model_config = {"extra": "ignore"}


class CreateThreadRequest(BaseModel):
    title: Optional[str] = None


class UpdateThreadRequest(BaseModel):
    title: str
