from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Initio Backend")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """Return a friendly echo response."""
    reply = f"Привет! Вы сказали: {req.message}"
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
