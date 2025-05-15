from db.session import db_context
from db.models  import Payment
from utils.payments import save_payment_csv
import logging

async def save_payment(message):
    total_amount = message.successful_payment.total_amount // 100
    currency     = message.successful_payment.currency

    session = db_context.get()
    session.add(Payment(
        user_id = message.from_user.id,
        amount  = total_amount,
        currency= currency
    ))
    await session.commit()
    logging.info("SQLite ► payments insert ok for %s", message.from_user.id)

    await save_payment_csv(message.from_user.id, total_amount, currency)
