import csv
import datetime as dt
from pathlib import Path

CSV_PATH = Path("payments.csv")


async def save_payment_csv(tg_id: int, amount: int, currency: str) -> None:
    is_new = not CSV_PATH.exists()
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        if is_new:
            writer.writerow(["datetime", "tg_id", "amount", "currency"])
        writer.writerow([dt.datetime.now().isoformat(timespec="seconds"),
                         tg_id, amount, currency])
