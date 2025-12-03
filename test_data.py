from db.db import Session, init_db
from db.db_models import Customer, Order

if __name__ == '__main__':
    init_db()
    with Session() as session:
        customer = Customer(name="Данис", surname="Абдреев", phone=79872378827, secret_key="ZGFuaXNfcGlkcg==")
        session.add(customer)
        session.commit()

        order = Order(customer_id=customer.id)
        session.add(order)
        session.commit()

        customer = Customer(name="Роман", surname="Ключаров", phone=79520313144, secret_key="11111")
        session.add(customer)
        session.commit()

        order = Order(customer_id=customer.id)
        session.add(order)
        session.commit()


