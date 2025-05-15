from aiogram import Router, types, F
from aiogram.filters import Command
from bot.config import CHANNEL_ID
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import URLInputFile

router = Router()

@router.message(Command("start"))
async def cmd_start(msg: types.Message):
    text = ("Подпишись на наш Telegram-канал "
            "https://t.me/INTECOcertification, чтобы быть в курсе всех новостей")
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="Я подписался!", callback_data="check_subscribe"))
    await msg.answer_photo(
        URLInputFile("https://i.ibb.co/JW5hb4cv/123321.jpg"),
        caption=text,
        reply_markup=kb.as_markup()
    )

async def _is_subscribed(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("creator", "administrator", "member")
    except Exception:
        return False


@router.callback_query(F.data == "check_subscribe")
async def check_sub(cb: types.CallbackQuery, bot):
    if await _is_subscribed(bot, cb.from_user.id):
        from handlers.orig import send_main_menu
        await send_main_menu(cb.message)
    else:
        await cb.answer("Похоже, что вы ещё не подписались", show_alert=True)

