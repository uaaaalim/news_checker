from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.entities.user_check import UserCheckEntity


async def get_by_tg_id(
    session: AsyncSession,
    tg_id: int,
) -> list[UserCheckEntity]:
    stmt = (
        select(UserCheckEntity)
        .where(UserCheckEntity.tg_id == tg_id)
        .order_by(UserCheckEntity.date.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_user_check(
    session: AsyncSession,
    tg_id: int,
    date: datetime,
) -> UserCheckEntity:
    entity = UserCheckEntity(
        tg_id=tg_id,
        date=date,
    )
    session.add(entity)
    await session.flush()
    return entity


async def delete_oldest_by_tg_id(
    session: AsyncSession,
    tg_id: int,
) -> UserCheckEntity | None:
    stmt = (
        select(UserCheckEntity)
        .where(UserCheckEntity.tg_id == tg_id)
        .order_by(UserCheckEntity.date.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    entity = result.scalar_one_or_none()

    if entity is None:
        return None

    await session.delete(entity)
    await session.flush()
    return entity