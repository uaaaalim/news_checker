from datetime import datetime

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import BaseEntity


class UserCheckEntity(BaseEntity):
    __tablename__ = 'usercheck'

    tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
