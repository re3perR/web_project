from aiogram import Router, F, types
from aiogram.enums import ContentType
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

def _main_menu_button() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(
        text="Вернуться в главное меню",
        callback_data="go_to_main_menu"
    ))
    kb.adjust(1)
    return kb.as_markup()


@router.message(F.content_type == ContentType.PHOTO)
async def echo_photo(msg: types.Message):
    await msg.answer("Прекрасное фото 📸", reply_markup=_main_menu_button())
    await msg.answer_photo(msg.photo[-1].file_id)


@router.message(F.content_type == ContentType.AUDIO)
async def echo_audio(msg: types.Message):
    await msg.answer("Прекрасный звук 🎵", reply_markup=_main_menu_button())
    await msg.answer_audio(msg.audio.file_id)
