import json

from db.db import Session
from db.db_models import Order


def check_order(order_data):
    try:
        json_data = json.loads(order_data)

        with Session() as session:
            order_data = session.query(Order).filter(Order.id == json_data['order_id']).first()
            if order_data:
                customer_data = order_data.customer
                if customer_data.secret_key == json_data['secret_key']:
                    return True

            return False
    except Exception as e:
        print(e)
