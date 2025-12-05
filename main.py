from db.db import init_db
from qrScanner import qr_scanner
from serialConnection import init_serial

if __name__ == '__main__':
    init_serial()
    init_db()
    qr_scanner()
