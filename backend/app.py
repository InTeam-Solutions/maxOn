import os
from datetime import datetime, date

import httpx
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
from .models import Event, EventSkip

load_dotenv()

app = FastAPI(title="Initio Backend")

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


class EventCreate(BaseModel):
    time: datetime
    description: str
    cron: Optional[str] = None
    skipped_dates: List[date] = []


class EventOut(BaseModel):
    id: int
    time: datetime
    description: str
    cron: Optional[str] = None
    skipped_dates: List[date] = []


class SkipDateRequest(BaseModel):
    date: date


@app.post("/events", response_model=EventOut)
def create_event(req: EventCreate, db: Session = Depends(get_db)) -> EventOut:
    """Create a calendar event with optional repetition and skipped dates."""
    event = Event(time=req.time, description=req.description, cron=req.cron)
    db.add(event)
    db.commit()
    db.refresh(event)
    for d in req.skipped_dates:
        db.add(EventSkip(event_id=event.id, date=d))
    db.commit()
    db.refresh(event)
    return EventOut(
        id=event.id,
        time=event.time,
        description=event.description,
        cron=event.cron,
        skipped_dates=[s.date for s in event.skips],
    )


@app.post("/events/{event_id}/skip", response_model=EventOut)
def skip_event(event_id: int, req: SkipDateRequest, db: Session = Depends(get_db)) -> EventOut:
    """Skip a single occurrence of an event on a specific date."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.add(EventSkip(event_id=event_id, date=req.date))
    db.commit()
    db.refresh(event)
    return EventOut(
        id=event.id,
        time=event.time,
        description=event.description,
        cron=event.cron,
        skipped_dates=[s.date for s in event.skips],
    )


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
