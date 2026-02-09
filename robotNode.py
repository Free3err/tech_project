import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
import serial
import time
import cv2
import numpy as np
from playsound3 import playsound
import threading

# Твои модули базы данных
from db.db import init_db
from db.functions import check_order


class RobotController(Node):
    def __init__(self):
        super().__init__('robot_controller')

        # 1. Настройка Serial (Arduino)
        # ВАЖНО: Проверь порт! Обычно /dev/ttyUSB1 или /dev/ttyACM0
        try:
            self.ser = serial.Serial('/dev/ttyUSB1', 9600, timeout=1)
            time.sleep(2)  # Ждем перезагрузки Arduino
            self.get_logger().info('Serial Connected!')
        except Exception as e:
            self.get_logger().error(f'Serial Error: {e}')
            self.ser = None

        # 2. База данных
        init_db()

        # 3. Подписка на Лидар
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.lidar_callback,
            10)
        self.lidar_data = None

        # 4. Камера и QR
        self.cap = cv2.VideoCapture(0)
        self.detector = cv2.QRCodeDetector()
        self.last_qr_data = None
        self.qr_cooldown = 0

        # 5. Таймер управления (10 Гц - 10 раз в секунду)
        self.timer = self.create_timer(0.1, self.control_loop)

        # Параметры движения
        self.wall_distance_target = 0.5  # Метры до стены
        self.wall_tolerance = 0.1  # Погрешность
        self.front_stop_dist = 0.4  # Остановка перед препятствием

    def send_cmd(self, cmd):
        if self.ser:
            try:
                self.ser.write((cmd + '\n').encode('utf-8'))
            except Exception as e:
                self.get_logger().error(f"Write error: {e}")

    def lidar_callback(self, msg):
        # Сохраняем данные сканирования
        self.lidar_data = msg

    def process_qr(self):
        ret, frame = self.cap.read()
        if not ret:
            return False

        data, bbox, _ = self.detector.detectAndDecode(frame)

        # Отрисовка для отладки (в отдельном окне)
        if bbox is not None:
            for i in range(len(bbox)):
                pt1 = tuple(map(int, bbox[i][0]))
                pt2 = tuple(map(int, bbox[(i + 1) % len(bbox)][0]))
                cv2.line(frame, pt1, pt2, color=(255, 0, 0), thickness=2)

        cv2.imshow("Robot Eye", frame)
        cv2.waitKey(1)

        if data and data != self.last_qr_data:
            self.last_qr_data = data
            self.get_logger().info(f"QR Detect: {data}")

            # Останавливаем робота при сканировании
            self.send_cmd("CMD_STOP")

            if check_order(data):
                self.get_logger().info("Order Valid!")
                # Используем threading чтобы звук не тормозил робота
                threading.Thread(target=playsound, args=('assets/successScan.wav',)).start()
                self.send_cmd("SUCCESS_SCAN")
            else:
                self.get_logger().info("Order Invalid!")
                threading.Thread(target=playsound, args=('assets/failureScan.wav',)).start()
                self.send_cmd("FAILURE_SCAN")

            # Пауза, чтобы полюбоваться эффектом
            time.sleep(3)
            return True

        return False

    def get_avg_range(self, ranges, start_angle, end_angle):
        # Функция берет среднее расстояние в секторе углов
        # ROS Лидар: 0 - спереди, 90 - слева, 270 (-90) - справа (обычно)
        # Нужно проверить, как D500 отдает данные. Обычно индекс = градус.

        # Фильтруем inf и 0
        sector = []
        num_readings = len(ranges)

        for i in range(start_angle, end_angle):
            # Обработка переполнения индекса (например 350-370)
            idx = i % num_readings
            dist = ranges[idx]
            if dist > 0.05 and dist < 3.0:  # Игнорируем ошибки и дальние точки
                sector.append(dist)

        if len(sector) == 0:
            return 999.0  # Нет препятствий
        return sum(sector) / len(sector)

    def control_loop(self):
        # 1. Сначала проверяем QR
        if self.process_qr():
            return  # Если нашли QR, пропускаем цикл движения

        # 2. Если данных лидара еще нет
        if self.lidar_data is None:
            return

        ranges = self.lidar_data.ranges

        # 3. Анализ расстояний (D500 обычно выдает массив по индексам)
        # Сектор спереди (от -10 до +10 градусов)
        front_dist = self.get_avg_range(ranges, -15, 15)

        # Сектор справа (от -100 до -80 градусов) -> Стена справа
        right_dist = self.get_avg_range(ranges, -100, -80)

        # 4. Логика движения (Вдоль правой стены)
        cmd = "CMD_STOP"

        if front_dist < self.front_stop_dist:
            # Препятствие спереди -> Поворот влево (от стены/препятствия)
            self.get_logger().info("Obstacle Front! Turning Left.")
            cmd = "CMD_LEFT"

        else:
            # Контроль стены (Bang-Bang controller)
            error = right_dist - self.wall_distance_target

            if right_dist > 2.0:
                # Стены справа нет -> Ищем стену (поворот направо или едем прямо, если потеряли)
                # Тут аккуратно: можно закрутиться. Пусть едет прямо и чуть вправо.
                self.get_logger().info("No wall. Searching...")
                cmd = "CMD_RIGHT"

            elif error > self.wall_tolerance:
                # Далеко от стены -> Повернуть направо (к стене)
                self.get_logger().info("Too far from wall -> Right")
                cmd = "CMD_RIGHT"

            elif error < -self.wall_tolerance:
                # Слишком близко к стене -> Повернуть налево (от стены)
                self.get_logger().info("Too close to wall -> Left")
                cmd = "CMD_LEFT"

            else:
                # Идеально -> Едем прямо
                self.get_logger().info("Moving Forward")
                cmd = "CMD_FWD"

        self.send_cmd(cmd)

    def __del__(self):
        self.send_cmd("CMD_STOP")
        if self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()


def main(args=None):
    rclpy.init(args=args)
    robot = RobotController()
    try:
        rclpy.spin(robot)
    except KeyboardInterrupt:
        pass
    finally:
        robot.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()