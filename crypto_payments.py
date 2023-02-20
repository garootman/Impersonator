from nowpayments import NOWPayments
from bot_config import NOWPAYMENTS_KEY

payment = NOWPayments(NOWPAYMENTS_KEY)
status = payment.get_api_status()
print (f"NowPayments status: {status}")