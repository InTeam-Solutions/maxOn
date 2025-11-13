from __future__ import annotations

import secrets
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models


async def create_calendar(
    session: AsyncSession, *, name: Optional[str], user_id: int
) -> models.Calendar:
    for _ in range(5):
        calendar = models.Calendar(name=name, user_id=user_id, public_token=_generate_token())
        session.add(calendar)
        try:
            await session.commit()
            await session.refresh(calendar)
            return calendar
        except IntegrityError:
            await session.rollback()
    raise RuntimeError("Unable to generate unique calendar token")


async def get_calendar(session: AsyncSession, calendar_id: UUID) -> Optional[models.Calendar]:
    result = await session.execute(select(models.Calendar).where(models.Calendar.id == calendar_id))
    return result.scalar_one_or_none()


async def get_calendar_with_events(
    session: AsyncSession, calendar_id: UUID
) -> Optional[models.Calendar]:
    stmt = (
        select(models.Calendar)
        .options(selectinload(models.Calendar.events))
        .where(models.Calendar.id == calendar_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_calendar_by_token(session: AsyncSession, public_token: str) -> Optional[models.Calendar]:
    result = await session.execute(
        select(models.Calendar).where(models.Calendar.public_token == public_token)
    )
    return result.scalar_one_or_none()


async def get_calendar_by_user(session: AsyncSession, user_id: int) -> Optional[models.Calendar]:
    result = await session.execute(select(models.Calendar).where(models.Calendar.user_id == user_id))
    return result.scalar_one_or_none()


async def ensure_calendar(
    session: AsyncSession, *, user_id: int, name: Optional[str] = None
) -> models.Calendar:
    calendar = await get_calendar_by_user(session, user_id)
    if calendar:
        return calendar
    return await create_calendar(session, name=name, user_id=user_id)


async def list_events_for_calendar(session: AsyncSession, calendar_id: UUID) -> list[models.Event]:
    result = await session.execute(
        select(models.Event)
        .where(models.Event.calendar_id == calendar_id)
        .order_by(models.Event.start_datetime)
    )
    return list(result.scalars())


def _generate_token() -> str:
    return secrets.token_urlsafe(16)
