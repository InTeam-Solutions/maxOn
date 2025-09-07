import os
import httpx
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from dotenv import load_dotenv

load_dotenv()

# Default to a local PostgreSQL instance but allow override via DATABASE_URL
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost/postgres"
)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    clarifications = Column(JSON, default=list)
    steps = relationship("GoalStep", back_populates="goal", cascade="all, delete-orphan")


class GoalStep(Base):
    __tablename__ = "goal_steps"
    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False)
    description = Column(String, nullable=False)
    is_done = Column(Boolean, default=False)
    goal = relationship("Goal", back_populates="steps")


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


class Clarification(BaseModel):
    question: str
    answer: str


class GoalRequest(BaseModel):
    goal: str


class GoalResponse(BaseModel):
    goal_id: int
    clarifications: List[Clarification]
    steps: List[str]


class GoalStepResponse(BaseModel):
    id: int
    description: str
    is_done: bool

    class Config:
        orm_mode = True


class GoalStepUpdate(BaseModel):
    is_done: bool


@app.post("/goals", response_model=GoalResponse)
async def set_goal(req: GoalRequest, db: Session = Depends(get_db)) -> GoalResponse:
    """Generate clarifying questions and steps for a goal and store them."""
    clarify_prompt = (
        f"Пользователь поставил цель: '{req.goal}'. "
        "Сформулируй два уточняющих вопроса и ответь на них. "
        "Формат каждой строки: Вопрос: <вопрос> Ответ: <ответ>"
    )
    qa_text = await generate_response(clarify_prompt)
    clarifications: List[Clarification] = []
    for line in qa_text.splitlines():
        if "Вопрос:" in line and "Ответ:" in line:
            q_part, a_part = line.split("Ответ:", 1)
            question = q_part.split("Вопрос:", 1)[1].strip()
            answer = a_part.strip()
            clarifications.append(Clarification(question=question, answer=answer))

    steps_prompt = (
        f"Перечисли шаги для достижения цели: '{req.goal}'. "
        "Каждый шаг с новой строки без нумерации."
    )
    steps_text = await generate_response(steps_prompt)
    steps = [s.strip("- ").strip() for s in steps_text.splitlines() if s.strip()]

    goal = Goal(description=req.goal, clarifications=[c.dict() for c in clarifications])
    db.add(goal)
    db.flush()
    for step_desc in steps:
        db.add(GoalStep(goal_id=goal.id, description=step_desc))
    db.commit()
    return GoalResponse(goal_id=goal.id, clarifications=clarifications, steps=steps)


@app.get("/goals/{goal_id}/steps", response_model=List[GoalStepResponse])
def get_goal_steps(goal_id: int, db: Session = Depends(get_db)) -> List[GoalStepResponse]:
    steps = db.query(GoalStep).filter_by(goal_id=goal_id).all()
    return steps


@app.patch("/goals/{goal_id}/steps/{step_id}", response_model=GoalStepResponse)
def update_goal_step(
    goal_id: int,
    step_id: int,
    update: GoalStepUpdate,
    db: Session = Depends(get_db),
) -> GoalStepResponse:
    step = db.query(GoalStep).filter_by(goal_id=goal_id, id=step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    step.is_done = update.is_done
    db.commit()
    db.refresh(step)
    return step


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
