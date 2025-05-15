from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

BOT_TOKEN  = "7364889529:AAFiGP2EvzSaCH0foyVe2egk8Vk_3t-S5Lc"
PAY_TOKEN  = '390540012:LIVE:52757'
CHANNEL_ID = -1001785856277

SQLITE_DSN = f"sqlite+aiosqlite:///{BASE_DIR/'bot.db'}"

RATES_URL = "https://api.exchangerate.host/latest?base=RUB&symbols=USD,EUR"
