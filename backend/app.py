import os

import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Initio Backend")


async def generate_response(message: str) -> str:
    """Call an external LLM service and return the assistant's reply."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": message}],
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Return a model-generated response for the given message."""
    reply = await generate_response(req.message)
    return ChatResponse(reply=reply)


class EventRequest(BaseModel):
    description: str


class EventResponse(BaseModel):
    description: str


@app.post("/calendar/events", response_model=EventResponse)
def add_event(req: EventRequest) -> EventResponse:
    """Stub for event creation."""
    return EventResponse(description=req.description)


class GoalRequest(BaseModel):
    goal: str


class GoalResponse(BaseModel):
    steps: List[str]


@app.post("/goals", response_model=GoalResponse)
def set_goal(req: GoalRequest) -> GoalResponse:
    """Return a single stub step for a goal."""
    step = f"Шаг 1 для цели '{req.goal}'"
    return GoalResponse(steps=[step])


class ProductRequest(BaseModel):
    query: str


class ProductResponse(BaseModel):
    title: str
    price: Optional[float] = None
    url: Optional[str] = None


@app.post("/shop", response_model=ProductResponse)
def add_product(req: ProductRequest) -> ProductResponse:
    """Stub product lookup."""
    return ProductResponse(title=req.query)


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
