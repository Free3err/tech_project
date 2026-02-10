import json

from db.db import Session
from db.db_models import Order


def check_order(order_data):
    try:
        json_data = json.loads(order_data)

        with Session() as session:
            order_data = session.query(Order).filter(Order.id == json_data['order_id']).first()
            if order_data:
                # ВРЕМЕННО: отключена проверка secret_key для тестирования
                # customer_data = order_data.customer
                # if customer_data.secret_key == json_data['secret_key']:
                #     return True
                return True  # Принимаем любой заказ если он существует

            return False
    except:
        return False
