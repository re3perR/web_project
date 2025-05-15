import contextvars
from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession
)
from aiogram import BaseMiddleware
from typing import Any, Dict, Callable, Awaitable
from bot.config import SQLITE_DSN

engine = create_async_engine(
    SQLITE_DSN,
    echo=True,
    pool_pre_ping=True
)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

db_context: contextvars.ContextVar[AsyncSession] = contextvars.ContextVar("db_session")


class DBSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ):
        async with SessionLocal() as session:
            token = db_context.set(session)
            data["db"] = session
            try:
                return await handler(event, data)
            finally:
                db_context.reset(token)
