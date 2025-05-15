from aiogram import Router
router = Router()

from db.session import db_context
from db.models import User
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert
import logging

async def save_user(message, data: dict):
    stmt = sqlite_upsert(User).values(
        tg_id   = message.from_user.id,
        name    = data.get("name"),
        phone   = data.get("phon"),
        product = data.get("tov")
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[User.tg_id],
        set_={
            "name": stmt.excluded.name,
            "phone": stmt.excluded.phone,
            "product": stmt.excluded.product,
        }
    )

    session = db_context.get()
    await session.execute(stmt)
    await session.commit()
    logging.info("SQLite ► users UPSERT ok for %s", message.from_user.id)

