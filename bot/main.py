import asyncio, logging
from aiogram import Bot
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode

from handlers.orig import dp
from handlers import all_routers
from db.session import DBSessionMiddleware, engine
from db.models import Base
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp.message.middleware(DBSessionMiddleware())
dp.callback_query.middleware(DBSessionMiddleware())

for r in all_routers:
    dp.include_router(r)

# ——————————————————————————————————————————
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logging.info("DB schema ✔")

async def main():
    await on_startup()
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types()
    )

if __name__ == "__main__":
    asyncio.run(main())
