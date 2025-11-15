"""
Job scheduler configuration
Defines all scheduled tasks and their triggers
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.tasks import event_reminders
from app.tasks import goal_deadlines
from app.tasks import step_reminders
from app.tasks import motivational

logger = logging.getLogger(__name__)


def setup_jobs(scheduler: AsyncIOScheduler):
    """
    Register all scheduled jobs with the scheduler
    """

    # Job 1: Event Reminders - Check every minute
    scheduler.add_job(
        func=event_reminders.check_and_send_reminders,
        trigger='interval',
        minutes=1,
        id='event_reminders',
        name='Event Reminders',
        replace_existing=True
    )
    logger.info("✅ Registered job: Event Reminders (every 1 minute)")

    # Job 2: Goal Deadline Warnings - Daily at 9:00 AM
    scheduler.add_job(
        func=goal_deadlines.check_and_send_warnings,
        trigger='cron',
        hour=9,
        minute=0,
        id='goal_deadlines',
        name='Goal Deadline Warnings',
        replace_existing=True
    )
    logger.info("✅ Registered job: Goal Deadline Warnings (daily at 9:00)")

    # Job 3: Unfinished Step Reminders - Daily at 8:00 PM
    scheduler.add_job(
        func=step_reminders.check_and_send_reminders,
        trigger='cron',
        hour=20,
        minute=0,
        id='step_reminders',
        name='Unfinished Step Reminders',
        replace_existing=True
    )
    logger.info("✅ Registered job: Unfinished Step Reminders (daily at 20:00)")

    # Job 4: Motivational Messages - Daily at 8:00 AM
    scheduler.add_job(
        func=motivational.send_daily_motivation,
        trigger='cron',
        hour=8,
        minute=0,
        id='motivational',
        name='Daily Motivational Messages',
        replace_existing=True
    )
    logger.info("✅ Registered job: Daily Motivational Messages (daily at 8:00)")
