"""
Worker Service for Initio
Handles scheduled notifications and reminders
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from shared.database import init_db, Base
from shared.utils.logger import setup_logger
from app.scheduler import setup_jobs


# Setup logger
logger = setup_logger("worker_service", level=os.getenv("LOG_LEVEL", "INFO"))

# Initialize scheduler
jobstores = {
    'default': RedisJobStore(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 4))
    )
}

executors = {
    'default': AsyncIOExecutor()
}

job_defaults = {
    'coalesce': True,  # Combine multiple pending executions into one
    'max_instances': 1,  # Only one instance of each job at a time
    'misfire_grace_time': 60  # Job can run up to 60s late
}

scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone='UTC'
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app"""
    # Startup
    logger.info("Starting Worker Service...")

    # Initialize database
    db = init_db()
    Base.metadata.create_all(bind=db.engine)
    logger.info("✅ Database initialized")

    # Setup scheduled jobs
    setup_jobs(scheduler)

    # Start scheduler
    scheduler.start()
    logger.info("✅ Scheduler started")
    logger.info(f"📋 Active jobs: {[job.id for job in scheduler.get_jobs()]}")

    yield

    # Shutdown
    logger.info("Shutting down Worker Service...")
    scheduler.shutdown(wait=True)
    logger.info("✅ Scheduler stopped")


# Create FastAPI app
app = FastAPI(
    title="Initio Worker Service",
    description="Background worker for notifications and scheduled tasks",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "worker"}


@app.get("/jobs")
async def list_jobs():
    """List all scheduled jobs"""
    jobs = scheduler.get_jobs()
    return {
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in jobs
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8005,
        log_level="info",
        reload=False
    )
