from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, ForeignKey, func

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id:       Mapped[int]       = mapped_column(Integer, primary_key=True)
    tg_id:    Mapped[int]       = mapped_column(Integer, unique=True, index=True)
    name:     Mapped[str]       = mapped_column(String(100))
    phone:    Mapped[str]       = mapped_column(String(30))
    product:  Mapped[str]       = mapped_column(String(255))
    created:  Mapped[datetime]  = mapped_column(DateTime, server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"

    id:       Mapped[int]       = mapped_column(Integer, primary_key=True)
    user_id:  Mapped[int]       = mapped_column(ForeignKey("users.id"))
    amount:   Mapped[int]       = mapped_column(Integer)
    currency: Mapped[str]       = mapped_column(String(10))
    paid_at:  Mapped[datetime]  = mapped_column(DateTime, server_default=func.now())
