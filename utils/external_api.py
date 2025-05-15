import aiohttp, asyncio, logging, time
from decimal import Decimal
from typing import Tuple

log = logging.getLogger(__name__)

EX_HOST = "https://api.exchangerate.host/latest?base=RUB&symbols=USD,EUR"
ERAPI   = "https://open.er-api.com/v6/latest/RUB"
CBR_DAILY = "https://www.cbr-xml-daily.ru/daily_json.js"

_cache: dict[str, Tuple[float, Tuple[Decimal, Decimal]]] = {}
TTL = 300  # секунд

def _put_cache(key: str, value: Tuple[Decimal, Decimal]):
    _cache[key] = (time.time() + TTL, value)

def _get_cache(key: str):
    exp, val = _cache.get(key, (0, None))
    return val if exp > time.time() else None


async def _fetch_json(url: str, timeout: int = 8) -> dict:
    async with aiohttp.ClientSession() as s:
        async with s.get(url, timeout=timeout) as r:
            r.raise_for_status()
            return await r.json()


async def _fetch_rates() -> Tuple[Decimal, Decimal]:
    """
    Возвращает (usd_per_rub, eur_per_rub).
    Кэшируется на TTL секунд.
    """
    if cached := _get_cache("rates"):
        return cached

    try:
        data = await _fetch_json(EX_HOST)
        usd = Decimal(str(data["rates"]["USD"]))
        eur = Decimal(str(data["rates"]["EUR"]))
        _put_cache("rates", (usd, eur))
        return usd, eur
    except Exception as e:
        log.warning("⚠️ exchangerate.host failed: %s", e)

    try:
        data = await _fetch_json(ERAPI)
        usd = Decimal(str(data["rates"]["USD"]))
        eur = Decimal(str(data["rates"]["EUR"]))
        _put_cache("rates", (Decimal(1)/usd, Decimal(1)/eur))
        usd_per_rub = usd if usd < 1 else Decimal(1) / usd
        eur_per_rub = eur if eur < 1 else Decimal(1) / eur
        _put_cache("rates", (usd_per_rub, eur_per_rub))
        return usd_per_rub, eur_per_rub
    except Exception as e:
        log.warning("⚠️ open.er-api.com failed: %s", e)

    try:
        data = await _fetch_json(CBR_DAILY)
        usd = Decimal("1") / Decimal(str(data["Valute"]["USD"]["Value"]))
        eur = Decimal("1") / Decimal(str(data["Valute"]["EUR"]["Value"]))
        _put_cache("rates", (usd, eur))
        log.info("✅ rate via CBR")
        return usd, eur
    except Exception as e:
        log.error("❌ всё сломалось: %s", e)
        return Decimal("0"), Decimal("0")


async def get_fx_rates_text() -> str:
    usd_per_rub, eur_per_rub = await _fetch_rates()
    if usd_per_rub == 0:
        return "💱 Курс валют сейчас недоступен"
    rub_per_usd = 1 / usd_per_rub
    rub_per_eur = 1 / eur_per_rub
    return (f"💱 1 USD ≈ {rub_per_usd:.2f} ₽\n"
            f"💱 1 EUR ≈ {rub_per_eur:.2f} ₽")


async def price_in_fx(rubles: int) -> Tuple[str, Decimal, Decimal]:
    usd_per_rub, eur_per_rub = await _fetch_rates()
    if usd_per_rub == 0:
        return "💱 Курс валют сейчас недоступен", Decimal("0"), Decimal("0")
    usd_price = Decimal(rubles) * usd_per_rub
    eur_price = Decimal(rubles) * eur_per_rub
    return await get_fx_rates_text(), usd_price, eur_price
