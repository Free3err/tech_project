import serial
import time

ser = None

def init_serial(port='COM10', baudrate=9600):
    global ser
    ser = serial.Serial(port, 9600)
    time.sleep(2)
