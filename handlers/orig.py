import asyncio
from aiogram import Router, F
import logging
import sys
from datetime import datetime, timedelta
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
from aiogram.types import ContentType, LabeledPrice, PreCheckoutQuery
from aiogram import types
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from aiogram.utils.markdown import hbold
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardRemove
from aiogram.methods.forward_message import ForwardMessage
from aiogram.methods.send_message import SendMessage
import json
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime
from aiogram.filters import Command
from aiogram import html
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from random import randint
from contextlib import suppress
from aiogram.types import FSInputFile, URLInputFile, BufferedInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from utils.external_api import price_in_fx
from db.db_save import save_user
from handlers.consultation import save_payment

logging.basicConfig(level=logging.INFO)

bot = Bot(token="7364889529:AAFiGP2EvzSaCH0foyVe2egk8Vk_3t-S5Lc")
dp = Dispatcher(storage=MemoryStorage())

# ---------
# ВАЖНО: Установите ID канала, на который нужно подписываться
CHANNEL_ID = -1001785856277  # Пример: "-1001234567890"
# ---------

f = ''
time = None
PAYMENTS_PROVIDER_TOKEN = '390540012:LIVE:52757'
PRICE = types.LabeledPrice(label='Онлайн-консультация', amount=99000)

# Пример provider_data с позицией "Онлайн-консультация"
provider_data1 = {
    "receipt": {
        "items": [
            {
                "description": "Онлайн консультация",
                "quantity": "1.00",
                "amount": {
                    "value": "990.00",
                    "currency": "RUB"
                },
                "vat_code": 1
            }
        ],
    }
}

# ============================================================
# Вспомогательные функции для проверки подписки и отложенных сообщений
# ============================================================

async def check_user_subscription(user_id: int) -> bool:
    """
    Функция для проверки, подписан ли пользователь на канал CHANNEL_ID
    Требует, чтобы бот был администратором или имел достаточные права.
    """
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ("creator", "administrator", "member"):
            return True
        return False
    except:
        return False


# Список задач (для напоминаний), чтобы не отправлять повторно при повторном взаимодействии
pending_tasks_15min = {}
pending_tasks_2h = {}
pending_tasks_after_final = {}

async def reminder_after_15min(user_id: int, state: FSMContext):
    """
    Напоминание через 15 минут, если юзер не подписался.
    """
    await asyncio.sleep(15 * 60)  # 15 минут
    # Повторно проверяем подписку, если юзер не успел подписаться
    is_subscribed = await check_user_subscription(user_id)
    if not is_subscribed:
        # Отправляем сообщение-напоминание, предлагаем продолжить
        text = ("Привет ☺️\n"
                "Тебя, наверное, отвлекли, и ты так и не узнал, как продавать товар, чтобы не нарушать законодательство РФ и не получать штрафы.\n"
                "Давай продолжим?")
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="Уже подписался!", callback_data="check_again_subscribe"))
        await bot.send_message(user_id, text, reply_markup=builder.as_markup())

async def reminder_after_2h(user_id: int):
    """
    Напоминание через 2 часа, если пользователь завис на каком-то не конечном шаге (не нажал кнопку).
    """
    await asyncio.sleep(2 * 60 * 60)  # 2 часа
    text = ("Вижу, что ты ничего не успеваешь, даже нажать на кнопку - и протестировать свою нишу 🥵\n\n"
            "Очень знакомая ситуация, сам когда-то был в такой гонке, и только заботливые руки наших экспертов "
            "помогли структурировать мою работу ❤️\n\n"
            "Не откладывай свой бизнес на потом, жми на кнопку ниже ⬇️")
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Выбрать товар", callback_data="go_to_main_menu"))
    await bot.send_message(user_id, text, reply_markup=builder.as_markup())


from aiogram import types
from aiogram.types import URLInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio


async def final_reminder_after_15min(user_id: int):
    """
    15 минут после конечного шага выбора товара - финальное сообщение о консультации со скидкой.
    """
    await asyncio.sleep(15 * 60)
    text = (
        "Вижу, что ты получил(а) ответ на вопрос, какие документы нужны, чтобы полностью легально продавать товар 😊\n\n"
        "У тебя еще есть шанс получить консультацию специалиста по суперцене - 990 рублей, вместо 2500 рублей и узнать:\n"
        "✅ Как выбрать товар для хорошей продажи (самые топовые ниши)?\n"
        "✅ Как проанализировать своих конкурентов?\n"
        "✅ Где закупать товар или производить?\n"
        "✅ Что делать, если конкурент стал продавать под вашим брендом (логотипом, названии)?\n"
        "✅ Как сэкономить на сертификации (какие товары можно указать в одном сертификате и т.п.)?\n\n"
        "Это мое последнее напоминание для тебя 🤝\n"
        "Просто подумай, что уже более 60 селлеров маркетплейсов воспользовались моим предложением и вышли на результат 🤑."
    )

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Записаться на консультацию", callback_data="button1111"))

    photo = URLInputFile("https://i.ibb.co/ccR0XfYt/15ad202e-246e-46a3-a19d-899cd49f17f9.jpg")

    await bot.send_photo(
        chat_id=user_id,
        photo=photo,
        caption=text,
        reply_markup=builder.as_markup()
    )

# Доп. напоминания после оплаты
async def remind_consultation_day_before(user_id: int, date_str: str, time_str: str):
    """
    Напоминалка за день до консультации (здесь - упрощённый пример).
    В реальной практике это делается через планировщик APScheduler и т.п.
    """
    # Пример: ждем 2 минуты, потом отправляем
    await asyncio.sleep(120)  # 2 минуты
    text = (
        "Не переживай, за день (в нашей демо-версии через 2 минуты) до консультации я заботливо напомню тебе о ней.\n"
        "Чтобы консультация прошла ещё более продуктивно, можешь написать свои вопросы в ответном сообщении ❤️\n"
        "Ждем тебя!"
    )
    await bot.send_message(user_id, text)

async def remind_consultation_in_day(user_id: int, date_str: str, time_str: str):
    """
    Напоминание в день консультации (упрощённый пример).
    """
    # Ждем ещё 2 минуты
    await asyncio.sleep(120)
    text = (
        f"Напоминаем, что сегодня в {time_str} состоится ваша консультация с экспертом. Увидимся!❤️\n"
        "Помни, что часть вопросов можно подготовить заранее!"
    )
    await bot.send_message(user_id, text)


# ============================================================
# Главный «старт» - здесь запускается новый сценарий
# ============================================================
@dp.message(Command("start"))
async def send_welcome(message: types.Message, state: FSMContext):
    """
    1 шаг: Привет! 😉 ... Для начала работы нажми /start
    2 шаг: Подпишись на наш Телеграм-канал...
    Потом проверка подписки
    """
    # Сбрасываем все state, если остались
    await state.clear()

    text = (" Подпишись на наш Telegram-канал https://t.me/INTECOcertification, чтобы быть в курсе всех новостей ")

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Я подписался!", callback_data="check_subscribe"))

    await message.answer_photo(
        URLInputFile("https://i.ibb.co/JW5hb4cv/123321.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )
    #await message.answer(text, reply_markup=builder.as_markup())

    # Запускаем отложенную задачу на 15 мин (напоминание) - если не подписался
    if message.from_user.id not in pending_tasks_15min:
        task = asyncio.create_task(reminder_after_15min(message.from_user.id, state))
        pending_tasks_15min[message.from_user.id] = task


@dp.callback_query(F.data == "check_subscribe")
async def process_check_subscribe(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработка нажатия "Я подписался!"
    Проверка подписки на канал.
    """
    user_id = callback_query.from_user.id
    # Отменяем таск на 15 минут (если он есть), чтобы не дублировать напоминания
    if user_id in pending_tasks_15min:
        pending_tasks_15min[user_id].cancel()
        del pending_tasks_15min[user_id]

    is_subscribed = await check_user_subscription(user_id)
    if is_subscribed:
        # 4 шаг: Если подписался: "А теперь выбери, какой у тебя товар..."
        #await callback_query.message.delete()
        await send_main_menu(callback_query.message)

        # Запускаем задачу на 2 часа (если пользователь вдруг "зависнет")
        if user_id not in pending_tasks_2h:
            task = asyncio.create_task(reminder_after_2h(user_id))
            pending_tasks_2h[user_id] = task
    else:
        # Не подписался -> Через 15 минут напомним (уже идёт таск)
        await callback_query.answer("Похоже, что вы еще не подписались. Подпишитесь, пожалуйста!", show_alert=True)


@dp.callback_query(F.data == "check_again_subscribe")
async def process_check_again_subscribe(callback_query: CallbackQuery, state: FSMContext):
    """
    Повторная проверка подписки через 15 минут, если пользователь не подписался изначально.
    """
    user_id = callback_query.from_user.id
    is_subscribed = await check_user_subscription(user_id)
    if is_subscribed:
        #await callback_query.message.delete()
        await send_main_menu(callback_query.message)

        # Запускаем задачу на 2 часа (если пользователь вдруг "зависнет")
        if user_id not in pending_tasks_2h:
            task = asyncio.create_task(reminder_after_2h(user_id))
            pending_tasks_2h[user_id] = task
    else:
        await callback_query.answer("Вы всё ещё не подписались на канал :(", show_alert=True)


# ============================================================
# Главное меню – выбор товара (шаг 4, если пользователь подписан)
# ============================================================
async def send_main_menu(message: types.Message):
    """
    6 шаг: Инлайн-кнопки с категориями товаров
    """
    text = ("Теперь выбери, какой у тебя товар, а я подскажу, какие документы нужны для его продажи ✅")
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Одежда и обувь", callback_data="button1"))
    builder.add(types.InlineKeyboardButton(text="Косметика и парфюмерия", callback_data="button2"))
    builder.add(types.InlineKeyboardButton(text="Продукты питания", callback_data="button3"))
    builder.add(types.InlineKeyboardButton(text="Электроника и гаджеты", callback_data="button4"))
    builder.add(types.InlineKeyboardButton(text="Строительство и ремонт", callback_data="button5"))
    builder.add(types.InlineKeyboardButton(text="Товары для дома", callback_data="button88"))
    builder.add(types.InlineKeyboardButton(text="Детские товары", callback_data="button6"))
    builder.add(types.InlineKeyboardButton(text="Спорт и активный отдых", callback_data="button7"))
    builder.add(types.InlineKeyboardButton(text="Товары для животных", callback_data="button8"))
    builder.add(types.InlineKeyboardButton(text="Автотовары", callback_data="button9"))
    builder.add(types.InlineKeyboardButton(text="Бытовая химия", callback_data="button77"))
    builder.add(types.InlineKeyboardButton(text="Другое", callback_data="button10"))
    builder.add(types.InlineKeyboardButton(text="Ещё не определился", callback_data="button11114241"))
    builder.adjust(1)

    await message.answer_photo(
        URLInputFile("https://i.ibb.co/DDgzCxwB/018ce401-06e5-4dd3-8c26-3518f63c4ab2.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    # Если пользователь снова взаимодействует, значит он не "завис" => отменяем задачу на 2 часа (если была)
    user_id = message.from_user.id
    if user_id in pending_tasks_2h:
        pending_tasks_2h[user_id].cancel()
        del pending_tasks_2h[user_id]

    # Запускаем задачу - через 15 минут (после конечного выбора) дать финальное сообщение, но сделаем это,
    # когда пользователь действительно что-то выберет (см. ниже логику).


@dp.callback_query(F.data == 'go_to_main_menu')
async def go_to_main_menu_callback(callback_query: CallbackQuery):
    """
    Если юзеру пришло сообщение, чтобы он нажал "Выбрать товар"
    """
    #await callback_query.message.delete()
    await send_main_menu(callback_query.message)


# ============================================================
# Обработка выбора категорий товаров
# ============================================================

@dp.callback_query(lambda c: c.data == 'button1')
async def process_button1(callback_query: types.CallbackQuery):
    """
    Одежда и обувь
    """
   #await callback_query.message.delete()
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Одежда или обувь для взрослых", callback_data="button01"))
    builder.add(types.InlineKeyboardButton(text="Одежда или обувь для детей", callback_data="button88_child"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back_main_menu"))
    builder.adjust(1)
    await callback_query.message.answer("Отлично! Давай уточним, какая именно одежда тебя интересует?", reply_markup=builder.as_markup())

    # Отменяем задачу на 2 часа и запускаем новую – если снова не выберет ничего
    user_id = callback_query.from_user.id
    if user_id in pending_tasks_2h:
        pending_tasks_2h[user_id].cancel()
        del pending_tasks_2h[user_id]
    pending_tasks_2h[user_id] = asyncio.create_task(reminder_after_2h(user_id))


@dp.callback_query(lambda c: c.data == 'button2')
async def process_button2(callback_query: types.CallbackQuery):
    """
    Косметика и парфюмерия
    """
    #await callback_query.message.delete()
    text = ("Как правило, на данные товары требуется получение декларации о соответствии по ТР ТС 009/2011, "
            "но есть часть продукции, которая требует обязательную государственную регистрацию (СГР), "
            "а также маркировка Честный знак.")

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Записаться на консультацию", callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)
    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/whBxCPTV/412cf3dc-0205-474e-8761-f669492109b0.png"),
        caption=text
    )

    await asyncio.sleep(10)

    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    # Запускаем финальный таймер на 15 минут (напоминание о консультации),
    # т.к. пользователь уже получил итоговую информацию
    user_id = callback_query.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
        del pending_tasks_after_final[user_id]
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(lambda c: c.data == 'button3')
async def process_button3(callback_query: types.CallbackQuery):
    """
    Продукты питания
    """
    #await callback_query.message.delete()
    text = ("Как правило, на данные товары требуется получение декларации о соответствии по ТР ТС 021/2011, "
            "а также применение системы ХАССП (HACCP). На часть продуктов питания нужна маркировка Честный знак.")


    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Записаться на консультацию", callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)


    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/jPdGvxvY/b557868d-277c-4629-a90b-d4b151243e07.png"),
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
        del pending_tasks_after_final[user_id]
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(lambda c: c.data == 'button4')
async def process_button4(callback_query: types.CallbackQuery):
    """
    Электроника и гаджеты
    """
    #await callback_query.message.delete()
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Для бытового применения", callback_data="button441"))
    builder.add(types.InlineKeyboardButton(text="Промышленного назначения", callback_data="button442"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.adjust(1)
    await callback_query.message.answer("Выберите назначение электроники и гаджетов:", reply_markup=builder.as_markup())

    user_id = callback_query.from_user.id
    # Сбрасываем/обновляем 2-часовой таймер
    if user_id in pending_tasks_2h:
        pending_tasks_2h[user_id].cancel()
        del pending_tasks_2h[user_id]
    pending_tasks_2h[user_id] = asyncio.create_task(reminder_after_2h(user_id))


@dp.callback_query(lambda c: c.data == 'button5')
async def process_button5(callback_query: types.CallbackQuery):
    """
    Строительство и ремонт
    """
    #await callback_query.message.delete()
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Для общестроительных работ', callback_data="button551"))
    builder.add(types.InlineKeyboardButton(text="Для дорожного строительсва", callback_data="button552"))
    builder.add(types.InlineKeyboardButton(text='Для отделочных работ', callback_data="button553"))
    builder.add(types.InlineKeyboardButton(text='Металлоконструкции', callback_data="button554"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.adjust(1)
    await callback_query.message.answer("Каким видом строительства вы занимаетесь?", reply_markup=builder.as_markup())

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_2h:
        pending_tasks_2h[user_id].cancel()
        del pending_tasks_2h[user_id]
    pending_tasks_2h[user_id] = asyncio.create_task(reminder_after_2h(user_id))


@dp.callback_query(lambda c: c.data == 'button88')
async def process_button88(callback_query: types.CallbackQuery):
    """
    Товары для дома
    """
    #await callback_query.message.delete()
    text = ("Что именно вас интересует?")
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Мебель', callback_data="button66"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.adjust(1)

    await callback_query.message.answer(text, reply_markup=builder.as_markup())

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_2h:
        pending_tasks_2h[user_id].cancel()
        del pending_tasks_2h[user_id]
    pending_tasks_2h[user_id] = asyncio.create_task(reminder_after_2h(user_id))


@dp.callback_query(lambda c: c.data == 'button6')
async def process_button6(callback_query: types.CallbackQuery):
    """
    Детские товары
    """
    #await callback_query.message.delete()
    text = ("Как правило требуется получение сертификата соответствия по ТР ТС 007/2011, "
            "для игрушек ТР ТС 008/2011. На ряд продукции требуется получение свидетельства "
            "о государственной регистрации (СГР), а также на часть продукции требуется маркировка Честный знак")

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Записаться на консультацию", callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    imageurl = URLInputFile('https://i.ibb.co/VYgCJ4pY/34befe44-db36-4511-956c-91a9ffcacc8b.png')
    await callback_query.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(lambda c: c.data == 'button7')
async def process_button7(callback_query: types.CallbackQuery):
    """
    Спорт и активный отдых
    """
    #await callback_query.message.delete()
    text = ("Как правило требуется получение отказного письма (отрицательного решения), "
            "при этом на ряд товаров требуется сертификат соответствия.")

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Записаться на консультацию", callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    imageurl = URLInputFile('https://i.ibb.co/CKgRDd06/76a18ecd-18f5-4921-9f66-dd246e6bdb38.png')

    await callback_query.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(lambda c: c.data == 'button8')
async def process_button8(callback_query: types.CallbackQuery):
    """
    Товары для животных
    """
    #await callback_query.message.delete()
    text = ("Как правило требуется получение отказного письма (отрицательного решения), "
            "при этом на ряд товаров требуется сертификат соответствия, а также на часть продукции требуется маркировка Честный знак")


    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Записаться на консультацию", callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    imageurl = URLInputFile('https://i.ibb.co/XrSwWYYt/image.jpg')

    await callback_query.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(lambda c: c.data == 'button9')
async def process_button9(callback_query: types.CallbackQuery):
    """
    Автотовары
    """
    #await callback_query.message.delete()
    text = ("Как правило требуется получение отказного письма (отрицательного решения), "
            "при этом на ряд товаров требуется сертификат соответствия по ТР ТС 018/2011 "
            "\"О безопасности колесных транспортных средств\".")

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Записаться на консультацию", callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    imageurl = URLInputFile('https://i.ibb.co/svpdTSKn/c866f266-cff0-4707-9195-083e88ecd539.png')

    await callback_query.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(lambda c: c.data == 'button77')
async def process_button77(callback_query: types.CallbackQuery):
    """
    Бытовая химия
    """
    #await callback_query.message.delete()
    text = ("Как правило, требуется получение свидетельства о государственной регистрации (СГР) "
            "и декларации ГОСТ Р., а также на часть продукции требуется маркировка Честный знак.")

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Записаться на консультацию", callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    imageurl = URLInputFile('https://i.ibb.co/dw0W4y3W/5b1180c2-fecb-40d2-8bd2-b9308136d952.png')
    await callback_query.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


# ============================================================
# "Другое" - пользователь вводит сам товар
# ============================================================

class UserState(StatesGroup):
    tov = State()
    phon = State()
    name = State()

@dp.callback_query(lambda c: c.data == 'button10')
async def process_button10(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Другое
    """
    #await callback_query.message.delete()
    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/9kfKPjdp/F6697cee-e64f-49a5-b9e8-ff52eeb173ec-1.jpg"),
        caption="Напишите, пожалуйста, продукцию, которую планируете реализовывать"
    )
    await state.set_state(UserState.tov)


@dp.message(UserState.tov)
async def forward_message(message: types.Message, state: FSMContext):
    """
    Как я могу к вам обращаться?
    """
    await state.update_data(tov=message.text)
    await message.answer("Как я могу к вам обращаться?")
    await state.set_state(UserState.name)

@dp.message(UserState.name)
async def forward_message(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(
        "Укажите телефон, чтобы специалист по сертификации мог связаться с вами удобным для вас способом")
    await state.set_state(UserState.phon)


@dp.message(UserState.phon)
async def forward_message1(message: Message, state: FSMContext):
    # 1) телефон кладём в state
    await state.update_data(phon=message.text)
    data = await state.get_data()

    # 2)  ⬇  сохраняем/обновляем пользователя в SQLite
    await save_user(message, data)       # ← новинка

    # 3) служебное сообщение админу (оставляем как было)
    await bot.send_message(
        1495460633,
        str(data) + ' от юзера ' + str(message.from_user.id)
    )

    # 4) очищаем state и продолжаем
    await state.clear()

    # ... дальше кнопки «Позвонить / WhatsApp / Telegram» (без изменений)



@dp.callback_query(F.data == 'button123')
async def process_button99(callback: CallbackQuery):
    await bot.send_message(1495460633, 'Позвонить юзеру ' + str(callback.from_user.id))
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.adjust(1)
    await callback.message.answer("Благодарим вас за доверие к нашей компании! Передаю ваш вопрос специалисту по сертификации, он свяжется с вами и ответит на все вопросы по разрешительным документам", reply_markup=builder.as_markup())


    # Запускаем финальный таймер (после конечного шага)
    #user_id = callback.from_user.id
    #if user_id in pending_tasks_after_final:
    #    pending_tasks_after_final[user_id].cancel()
    #pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(F.data == 'button124')
async def process_button99(callback: CallbackQuery):
    await bot.send_message(1495460633, 'В ватсап юзеру ' + str(callback.from_user.id))
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.adjust(1)
    await callback.message.answer(
        "Благодарим вас за доверие к нашей компании! Передаю ваш вопрос специалисту по сертификации, он свяжется с вами и ответит на все вопросы по разрешительным документам",
        reply_markup=builder.as_markup())

    # Запускаем финальный таймер (после конечного шага)
    # user_id = callback.from_user.id
    # if user_id in pending_tasks_after_final:
    #    pending_tasks_after_final[user_id].cancel()
    # pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(F.data == 'button125')
async def process_button99(callback: CallbackQuery):
    await bot.send_message(1495460633, 'В тг юзеру ' + str(callback.from_user.id))
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.adjust(1)
    await callback.message.answer(
        "Благодарим вас за доверие к нашей компании! Передаю ваш вопрос специалисту по сертификации, он свяжется с вами и ответит на все вопросы по разрешительным документам",
        reply_markup=builder.as_markup())

    # Запускаем финальный таймер (после конечного шага)
    # user_id = callback.from_user.id
    # if user_id in pending_tasks_after_final:
    #    pending_tasks_after_final[user_id].cancel()
    # pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))

# @dp.message(UserState.name)
# async def forward_message_name(message: types.Message, state: FSMContext):
#     """
#     Укажите телефон...
#     """
#     await state.update_data(name=message.text)
#     await message.answer("Укажите телефон, чтобы специалист по сертификации мог связаться с вами "
#                          "удобным для вас способом")
#     await state.set_state(UserState.phon)
#
#
# @dp.message(UserState.phon)
# async def forward_message_phone(message: Message, state: FSMContext):
#     """
#     Завершаем "Другое"
#     """
#     await state.update_data(phon=message.text)
#     data = await state.get_data()
#     await bot.send_message(
#         1623431342,
#         str(data) + ' от юзера ' + str(message.from_user.id) +
#         '. Нужно связаться по вопросу "Другое"'
#     )
#     await state.clear()
#     await asyncio.sleep(6)
#     text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
#         "Самое время узнать, как его можно получить!\n\n"
#         "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
#         "специалиста по сертификации. Чтобы связаться со специалистом, "
#         "запишись на онлайн-консультацию. 📲")
#
#     builder = InlineKeyboardBuilder()
#     builder.add(types.InlineKeyboardButton(text="Записаться на консультацию", callback_data="button1111"))
#     builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
#     builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
#     builder.adjust(1)
#
#     await message.answer_photo(
#         URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
#         caption=text,
#         reply_markup=builder.as_markup()
#     )
#
#     # Запускаем финальный таймер (после конечного шага)
#     user_id = message.from_user.id
#     if user_id in pending_tasks_after_final:
#         pending_tasks_after_final[user_id].cancel()
#     pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


# ============================================================
# Ещё не определился
# ============================================================
@dp.callback_query(F.data == 'button11114241')
async def command_start_handler(callback: CallbackQuery) -> None:
    """
    Предлагаю записаться на консультацию, чтобы подобрать товар.
    """
    #await callback.message.delete()
    text = (
        "Предлагаю записаться на консультацию нашего специалиста, чтобы подобрать товар, "
        "который принесёт тебе от 1 млн рублей в месяц.\n\n"
        "Выберите удобное время для консультации."
    )
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Записаться на консультацию", callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    await callback.message.answer_photo(
        URLInputFile("https://i.ibb.co/394v1dR8/51185ebb-d585-44b8-b7ed-4f8c5aa80228-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )


# ============================================================
# Логика "Одежда и обувь" -> уточнение: для взрослых или детей
# ============================================================

@dp.callback_query(F.data == 'button01')
async def process_button01(callback: CallbackQuery):
    """
    Одежда или обувь для взрослых
    """
    #await callback.message.delete()
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Одежда первого слоя (нательное или постельное белье)", callback_data="button111"))
    builder.add(types.InlineKeyboardButton(text="Одежда второго слоя (повседневная)", callback_data="button222"))
    builder.add(types.InlineKeyboardButton(text="Одежда третьего слоя (верхняя одежда)", callback_data="button333"))
    builder.add(types.InlineKeyboardButton(text="Текстиль, сумки, обувь", callback_data="button444"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.adjust(1)
    await callback.message.answer(
        "Какая именно одежда вас интересует?",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data == 'button88_child')
async def process_button88_child(callback: CallbackQuery):
    """
    Одежда или обувь для детей
    """
    #await callback.message.delete()
    text = ("Как правило требуется получение сертификата соответствия по ТР ТС 007/2011, "
            "для игрушек ТР ТС 008/2011. На ряд продукции требуется получение свидетельства "
            "о государственной регистрации (СГР).")

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Записаться на консультацию", callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)
    await callback.message.answer_photo(
        URLInputFile("https://i.ibb.co/NdZs23qR/30c38436-3213-441e-8216-ca0b02414dc8.png"),
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


# ============================================================
# Детализация для "Электроника и гаджеты"
# ============================================================
@dp.callback_query(F.data == 'button441')
async def process_button441(callback_query: CallbackQuery):
    """
    Электроника и гаджеты для бытового применения
    """
    #await callback_query.message.delete()
    text = (
        "Как правило, на данные товары требуется получение сертификата соответствия по ТР ТС 004/2011, "
        "ТР ТС 020/2011 и декларации о соответствии по ТР ЕАЭС 037/2016. "
        "Важно обратить внимание на источник питания и вольтаж, а также на часть продукции требуется маркировка Честный знак."
    )
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Записаться на консультацию', callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    imageurl = URLInputFile('https://i.ibb.co/Z1dzYdNp/Bit.jpg')
    await callback_query.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(F.data == 'button442')
async def process_button442(callback_query: CallbackQuery):
    """
    Электроника и гаджеты промышленного назначения
    """
    #await callback_query.message.delete()
    text = (
        "Как правило, на данные товары требуется получение декларации о соответствии по ТР ТС 004/2011, "
        "ТР ТС 020/2011, а также на часть продукции требуется маркировка Честный знак."
    )
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Записаться на консультацию', callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    imageurl = URLInputFile('https://i.ibb.co/qFXnGMPN/Prom.jpg')
    await callback_query.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


# ============================================================
# Детализация для "Строительство и ремонт"
# ============================================================
@dp.callback_query(F.data == 'button551')
async def process_button551(callback_query: CallbackQuery):
    """
    Общестроительные работы
    """
    #await callback_query.message.delete()
    text = (
        "Как правило, данная продукция не требует подтверждения соответствия и на нее оформляется добровольный сертификат, а также на часть продукции требуется маркировка Честный знак."
    )
    imageurl = URLInputFile('https://i.ibb.co/vCX2xdsj/270b6594-3cf8-4372-a96a-a4d1fa20f5c9.png')
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Записаться на консультацию', callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    await callback_query.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(F.data == 'button552')
async def process_button552(callback_query: CallbackQuery):
    """
    Для дорожного строительства
    """
    #await callback_query.message.delete()
    text = (
        "Как правило на материалы для дорожного строительства, требуется получение декларации о соответствии по ТР ТС 014/2012, а также на часть продукции требуется маркировка Честный знак."
    )
    imageurl = URLInputFile('https://i.ibb.co/LFpFm2Y/b8266a5d-b993-4bed-bd96-2515b7e22e11.png')
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Записаться на консультацию', callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    await callback_query.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(F.data == 'button553')
async def process_button553(callback_query: CallbackQuery):
    """
    Для отделочных работ
    """
    #await callback_query.message.delete()
    text = (
        "На часть продукции для отделочных работ, требуется получение свидетельства о государственной регистрации (СГР) "
        "и декларации ГОСТ Р, а также на часть продукции требуется маркировка Честный знак."
    )
    imageurl = URLInputFile('https://i.ibb.co/Wpszp1pt/76b72b23-107c-466d-99fe-364b0e1c0af4.png')
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Записаться на консультацию', callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    await callback_query.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(F.data == 'button554')
async def process_button554(callback_query: CallbackQuery):
    """
    Металлоконструкции
    """
    #await callback_query.message.delete()
    text = (
        "Как правило, данная продукция не требует подтверждения соответствия и на нее оформляется добровольный сертификат, а также на часть продукции требуется маркировка Честный знак."
    )
    imageurl = URLInputFile('https://i.ibb.co/ZRGPXspG/6a091eb6-05d6-4325-acb0-eb66a9b9e46f.png')
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Записаться на консультацию', callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    await callback_query.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


# ============================================================
# Детализация "Мебель"
# ============================================================
@dp.callback_query(F.data == 'button66')
async def process_button66(callback_query: CallbackQuery):
    """
    Мебель
    """
    #await callback_query.message.delete()
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Для детей', callback_data="button661"))
    builder.add(types.InlineKeyboardButton(text="Для взрослых", callback_data="button662"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.adjust(1)
    await callback_query.message.answer("Для кого предназначается мебель?", reply_markup=builder.as_markup())

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_2h:
        pending_tasks_2h[user_id].cancel()
        del pending_tasks_2h[user_id]
    pending_tasks_2h[user_id] = asyncio.create_task(reminder_after_2h(user_id))


@dp.callback_query(F.data == 'button661')
async def process_button661(callback_query: CallbackQuery):
    """
    Мебель для детей
    """
    #await callback_query.message.delete()
    text = (
        "Как правило, на данные товары требуется получение сертификата соответствия по ТР ТС 025/2012."
    )
    imageurl = URLInputFile('https://i.ibb.co/Lz3GWmcL/b1e64e57-5d1f-4fcc-ae95-8bf03c23afb5.png')
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Записаться на консультацию', callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    await callback_query.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback_query.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(F.data == 'button662')
async def process_button662(callback_query: CallbackQuery):
    """
    Мебель для взрослых
    """
    #await callback_query.message.delete()
    text = (
        "Как правило, на данные товары требуется получение декларации о соответствии по ТР ТС 025/2012."
    )
    imageurl = URLInputFile('https://i.ibb.co/67p9qfL6/b1ea81f6-1596-48ce-9fed-2ab7b535a272.png')
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Записаться на консультацию', callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    await callback_query.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback_query.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )
    user_id = callback_query.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


# ============================================================
# Детализация "Одежда первого, второго, третьего слоя..."
# ============================================================
@dp.callback_query(F.data == 'button111')
async def process_button111(callback: CallbackQuery):
    """
    Одежда первого слоя
    """
    #await callback.message.delete()
    text = (
        "Как правило, на данные товары требуется получение сертификата соответствия по ТР ТС 017/2011, "
        "а также на часть продукции требуется маркировка Честный знак."
    )
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Записаться на консультацию', callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    imageurl = URLInputFile('https://i.ibb.co/zV9ZQrbb/b83bd184-afb8-4452-a3fa-0ce330ccf349.png')
    await callback.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(F.data == 'button222')
async def process_button222(callback: CallbackQuery):
    """
    Одежда второго слоя
    """
    #await callback.message.delete()
    text = (
        "Как правило, на данные товары требуется получение декларации о соответствии по ТР ТС 017/2011, "
        "а также на часть продукции требуется маркировка Честный знак."
        "Для связи со специалистом запишитесь на онлайн консультацию."
    )
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Записаться на консультацию', callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    imageurl = URLInputFile('https://i.ibb.co/WWNb3TG8/2.jpg')
    await callback.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(F.data == 'button333')
async def process_button333(callback: CallbackQuery):
    """
    Одежда третьего слоя
    """
    #await callback.message.delete()
    text = (
        "Как правило, на данные товары требуется получение декларации о соответствии по ТР ТС 017/2011, "
        "а также на часть продукции требуется маркировка Честный знак."
    )
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Записаться на консультацию', callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    imageurl = URLInputFile('https://i.ibb.co/LXq5DDHY/ab39738d-13b3-409f-968e-964870beec32.png')
    await callback.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


@dp.callback_query(F.data == 'button444')
async def process_button444(callback: CallbackQuery):
    """
    Текстиль, сумки, обувь
    """
    #await callback.message.delete()
    text = (
        "Как правило, на данные товары требуется получение декларации о соответствии по ТР ТС 017/2011, "
        "а также на часть продукции требуется маркировка Честный знак."
        "Для связи со специалистом запишитесь на онлайн консультацию."
    )
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Записаться на консультацию', callback_data="button1111"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    imageurl = URLInputFile('https://i.ibb.co/qMHfXWNZ/a6a5ad2b-a4e2-4337-96ca-836212c4b72c.png')
    await callback.message.answer_photo(
        imageurl,
        caption=text
    )
    await asyncio.sleep(10)
    text = ("Теперь ты знаешь, какой документ нужен, чтобы продавать без штрафов. "
        "Самое время узнать, как его можно получить!\n\n"
        "Так как стоимость и сроки зависят от разных факторов, я передам тебя в надёжные руки "
        "специалиста по сертификации. Чтобы связаться со специалистом, "
        "запишись на онлайн-консультацию. 📲")

    await callback.message.answer_photo(
        URLInputFile("https://i.ibb.co/GftshF5Q/691d121a-c832-495e-a7fa-0417946c09a7-1.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )

    user_id = callback.from_user.id
    if user_id in pending_tasks_after_final:
        pending_tasks_after_final[user_id].cancel()
    pending_tasks_after_final[user_id] = asyncio.create_task(final_reminder_after_15min(user_id))


# ============================================================
# Возвращаемся в главное меню
# ============================================================
@dp.callback_query(F.data == 'back_main_menu')
async def process_back_main(callback: CallbackQuery):
    #await callback.message.delete()
    await send_main_menu(callback.message)

@dp.callback_query(F.data == 'back')
async def process_back(callback: CallbackQuery):
    #await callback.message.delete()
    await send_main_menu(callback.message)


# ============================================================
# Логика консультации: выбор даты, времени, оплата
# ============================================================

# Используем уже существующие состояния
class UserState2(StatesGroup):
    tov = State()
    mail = State()
    phon = State()
    name = State()

@dp.callback_query(F.data == 'button1111')
async def callback_consultation(callback: CallbackQuery):
    """
    При нажатии 'Записаться на консультацию'
    (После того, как пользователь увидел, какие документы нужны).
    """
    #await callback.message.delete()
    text = (
        "Хочешь выйти на миллион с продаж? 🔥\n\n"
        "Подтверди запись на консультацию с экспертом по СУПЕРЦЕНЕ - 990 рублей, ВМЕСТО 2500 рублей 🔥\n\n"
        "На консультации ты узнаешь:\n"
        "✅ Как выбрать товар для хорошей продажи (самые топовые ниши)?\n"
        "✅ Как проанализировать своих конкурентов?\n"
        "✅ Где закупать товар или производить?\n"
        "✅ Что делать, если конкурент стал продавать под вашим брендом (логотипом, названии)?\n"
        "✅ Как сэкономить на сертификации (какие товары можно указать в одном сертификате и т.п.)?\n"
    )
    rates_txt, usd, eur = await price_in_fx(990)
    await callback.message.answer(
        f"{rates_txt}\n\n"
        f"Стоимость консультации — 990 ₽ ≈ {usd:.2f} $ или {eur:.2f} €"
    )
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Оплатить 990 руб.', callback_data="button_pay_consult"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.add(types.InlineKeyboardButton(text="Связаться со специалистом", url="https://t.me/intecocert"))
    builder.adjust(1)

    await callback.message.answer_photo(
        URLInputFile("https://i.ibb.co/Lzw2D3sW/B5ae4573-58a0-4b54-aa84-52a55891f2f0.jpg"),
        caption=text,
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data == 'button_pay_consult')
async def pay_consultation(callback: CallbackQuery):
    """
    Кнопка оплаты консультации.
    """
    #await callback.message.delete()
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        need_email=True,
        send_email_to_provider=True,
        title='Онлайн-консультация (акция)',
        description='Подтверди запись на консультацию с экспертом по СУПЕРЦЕНЕ - 990 рублей, вместо 2500 рублей!',
        provider_token=PAYMENTS_PROVIDER_TOKEN,
        currency='RUB',
        is_flexible=False,
        prices=[PRICE],
        start_parameter='time-machine-example',
        payload='some-invoice-payload-for-our-internal-use',
        provider_data=json.dumps(provider_data1)
    )


@dp.pre_checkout_query(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """
    Ответ на pre_checkout
    """
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """
    Если оплата прошла успешно
    """

    total_amount = message.successful_payment.total_amount / 100
    currency = message.successful_payment.currency

    await save_payment(message)

    thank_you_message = (
        f"Оплата прошла ✅, благодарим вас за доверие к нашей компании! Желаем хорошей консультации! ❤️\n\n"
        f"Вы оплатили {total_amount} {currency}. \n"
        "Чтобы консультация прошла ещё более продуктивно, вы можете написать свои вопросы в ответном сообщении.\n"
        "Я заботливо напомню тебе о консультации за день и в день консультации."
    )
    await message.answer(thank_you_message)

    # Через пару минут напомним "за день до консультации", затем ещё раз "в день консультации" (демо-режим)
    asyncio.create_task(remind_consultation_day_before(message.from_user.id, f, time))
    asyncio.create_task(remind_consultation_in_day(message.from_user.id, f, time))

    await bot.send_message(
        1623431342,
        'юзер ' + str(message.from_user.id) + ' оплатил консультацию.'
    )


# ============================================================
# Логика выбора даты (только для "Ещё не определился", когда предлагаем календарь)
# (используем aiogram_calendar)
# ============================================================

@dp.callback_query(SimpleCalendarCallback.filter())
async def process_simple_calendar(callback_query: CallbackQuery, callback_data: SimpleCalendarCallback):
    global f
    calendar = SimpleCalendar(show_alerts=True)
    calendar.set_dates_range(datetime(2024, 1, 1), datetime(2025, 12, 31))
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)

    if selected and date:
        f = date.strftime("%d/%m/%Y")
        text = (f"Вы выбрали дату: {f}.\n"
                "А теперь успей занять самое удобное время для тебя!")
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text='Продолжить', callback_data="button111115"))
        builder.add(types.InlineKeyboardButton(text='Выбрать другую дату', callback_data="button1111"))
        builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
        builder.adjust(1)
        await callback_query.message.answer(text, reply_markup=builder.as_markup())

    elif callback_data.act == 'CANCEL':
        # Если пользователь нажал CANCEL, возвращаем в главное меню
        #await callback_query.message.delete()
        await send_main_menu(callback_query.message)


@dp.callback_query(F.data == 'button111115')
async def process_time_choice(callback: CallbackQuery):
    """
    Просим выбрать время
    """
    global f
    #await callback.message.delete()
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='10:00', callback_data="time_10"))
    builder.add(types.InlineKeyboardButton(text='11:00', callback_data="time_11"))
    builder.add(types.InlineKeyboardButton(text='12:00', callback_data="time_12"))
    builder.add(types.InlineKeyboardButton(text='13:00', callback_data="time_13"))
    builder.add(types.InlineKeyboardButton(text='14:00', callback_data="time_14"))
    builder.add(types.InlineKeyboardButton(text='15:00', callback_data="time_15"))
    builder.add(types.InlineKeyboardButton(text='16:00', callback_data="time_16"))
    builder.add(types.InlineKeyboardButton(text='17:00', callback_data="time_17"))
    builder.add(types.InlineKeyboardButton(text='18:00', callback_data="time_18"))
    builder.adjust(3)
    await callback.message.answer(
        f"Самое удобное время для тебя на {f}",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(lambda c: c.data.startswith("time_"))
async def confirm_time_consultation(callback: CallbackQuery):
    """
    Подтверждение конкретного времени консультации
    """
    global time
    time = callback.data.split("_")[1] + ":00"
    #await callback.message.delete()
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Продолжить', callback_data="proceed_to_payment"))
    builder.add(types.InlineKeyboardButton(text='Выбрать другое время', callback_data="button111115"))
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.adjust(1)

    text = (
        f"Для подтверждения записи на {f} в {time}, скорее переходи на страницу оплаты "
        "консультации специалиста по суперцене - 990 рублей, чтобы узнать:\n"
        "- Как выбрать правильный товар\n"
        "- Как проанализировать конкурентов\n"
        "- Где найти производителя продукции, заинтересованного в твоих продажах\n"
        "- Как создать собственный бренд и не попасть на штрафы\n"
        "- Как сэкономить на сертификации и приумножить вложенные деньги."
    )
    await callback.message.answer(text, reply_markup=builder.as_markup())


@dp.callback_query(F.data == 'proceed_to_payment')
async def pay_consultation_choice(callback: CallbackQuery):
    """
    Пользователь подтверждает, что хочет оплатить консультацию в выбранный день и время.
    """
    global f, time
    #await callback.message.delete()
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back"))
    builder.adjust(1)

    # Вызываем оплату
    await bot.send_invoice(
        callback.message.chat.id,
        need_email=True,
        send_email_to_provider=True,
        title=f'Онлайн-консультация {f} в {time}',
        description=(f'Наш квалифицированный специалист свяжется с вами перед онлайн-консультацией {f} в {time}, '
                     'чтобы обсудить все необходимые вопросы. На самой консультации он предоставит вам всю необходимую '
                     'информацию о сертификации нужных вам документов.'),
        provider_token=PAYMENTS_PROVIDER_TOKEN,
        currency='RUB',
        is_flexible=False,
        prices=[PRICE],
        start_parameter='time-machine-example',
        payload='some-invoice-payload-for-our-internal-use',
        provider_data=json.dumps(provider_data1),
        reply_markup=builder.as_markup()
    )


# ============================================================
# Запуск
# ============================================================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
