from db.db import init_db
from qrScanner import qr_scanner

if __name__ == '__main__':
    init_db()
    qr_scanner()