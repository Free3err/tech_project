#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Веб-интерфейс для управления RelayBot
- Управление движением
- Трансляция камеры
- Визуализация LiDAR карты
"""

from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO, emit
import cv2
import json
import threading
import time
import logging
from typing import Optional
import numpy as np

# Импорт модулей робота
import config
import serialConnection
from lidar_interface import LiDARInterface

app = Flask(__name__)
app.config['SECRET_KEY'] = 'relaybot_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

logger = logging.getLogger(__name__)

# Глобальные переменные
camera = None
lidar = None
camera_lock = threading.Lock()
lidar_lock = threading.Lock()


def init_camera():
    """Инициализация камеры"""
    global camera
    try:
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        camera.set(cv2.CAP_PROP_FPS, 30)
        logger.info("Камера инициализирована")
        return True
    except Exception as e:
        logger.error(f"Ошибка инициализации камеры: {e}")
        return False


def init_lidar():
    """Инициализация LiDAR"""
    global lidar
    try:
        lidar = LiDARInterface(config.LIDAR_PORT, config.LIDAR_BAUDRATE)
        logger.info("LiDAR инициализирован")
        return True
    except Exception as e:
        logger.error(f"Ошибка инициализации LiDAR: {e}")
        return False


def generate_camera_frames():
    """Генератор кадров с камеры для MJPEG стрима"""
    global camera
    
    while True:
        if camera is None or not camera.isOpened():
            time.sleep(0.1)
            continue
        
        with camera_lock:
            success, frame = camera.read()
        
        if not success:
            time.sleep(0.1)
            continue
        
        # Кодирование кадра в JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            continue
        
        frame_bytes = buffer.tobytes()
        
        # Отправка кадра в формате MJPEG
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


def lidar_data_thread():
    """Поток для отправки данных LiDAR через WebSocket"""
    global lidar
    
    while True:
        if lidar is None:
            time.sleep(0.5)
            continue
        
        try:
            with lidar_lock:
                scan = lidar.get_scan()
            
            if scan and len(scan) > 0:
                # Преобразование данных LiDAR в формат для визуализации
                points = []
                for point in scan:
                    x = point.distance * np.cos(point.angle) * 1000  # В миллиметры
                    y = point.distance * np.sin(point.angle) * 1000
                    points.append({
                        'x': float(x),
                        'y': float(y),
                        'intensity': int(point.intensity)
                    })
                
                # Отправка данных через WebSocket
                socketio.emit('lidar_data', {'points': points})
        
        except Exception as e:
            logger.error(f"Ошибка получения данных LiDAR: {e}")
        
        time.sleep(0.1)  # 10 Гц


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    """Видео поток с камеры"""
    return Response(generate_camera_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/move', methods=['POST'])
def move():
    """API для управления движением робота"""
    try:
        data = request.json
        direction = data.get('direction')
        speed = data.get('speed', 120)
        
        if direction == 'forward':
            serialConnection.send_motor_command(speed, speed, 0, 0)
        elif direction == 'backward':
            serialConnection.send_motor_command(speed, speed, 1, 1)
        elif direction == 'left':
            serialConnection.send_motor_command(speed, speed, 1, 0)
        elif direction == 'right':
            serialConnection.send_motor_command(speed, speed, 0, 1)
        elif direction == 'stop':
            serialConnection.send_motor_command(0, 0, 0, 0)
        else:
            return jsonify({'error': 'Invalid direction'}), 400
        
        return jsonify({'status': 'ok', 'direction': direction})
    
    except Exception as e:
        logger.error(f"Ошибка управления движением: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/servo', methods=['POST'])
def servo():
    """API для управления сервоприводом"""
    try:
        data = request.json
        angle = data.get('angle', 0)
        
        serialConnection.send_servo_command(angle)
        
        return jsonify({'status': 'ok', 'angle': angle})
    
    except Exception as e:
        logger.error(f"Ошибка управления сервоприводом: {e}")
        return jsonify({'error': str(e)}), 500


@socketio.on('connect')
def handle_connect():
    """Обработка подключения клиента"""
    logger.info("Клиент подключен к WebSocket")
    emit('status', {'message': 'Connected to RelayBot'})


@socketio.on('disconnect')
def handle_disconnect():
    """Обработка отключения клиента"""
    logger.info("Клиент отключен от WebSocket")


def run_web_interface(host='0.0.0.0', port=5000):
    """Запуск веб-интерфейса"""
    logger.info("=" * 60)
    logger.info("Запуск веб-интерфейса RelayBot")
    logger.info("=" * 60)
    
    # Инициализация Serial
    logger.info("Подключение к Arduino...")
    try:
        serialConnection.init_serial(config.ARDUINO_PORT, config.ARDUINO_BAUDRATE)
        logger.info(f"✓ Arduino подключен: {config.ARDUINO_PORT}")
    except Exception as e:
        logger.error(f"✗ Ошибка подключения Arduino: {e}")
    
    # Инициализация камеры
    logger.info("Инициализация камеры...")
    if init_camera():
        logger.info("✓ Камера готова")
    else:
        logger.warning("⚠ Камера недоступна")
    
    # Инициализация LiDAR
    logger.info("Инициализация LiDAR...")
    if init_lidar():
        logger.info("✓ LiDAR готов")
        # Запуск потока отправки данных LiDAR
        lidar_thread = threading.Thread(target=lidar_data_thread, daemon=True)
        lidar_thread.start()
    else:
        logger.warning("⚠ LiDAR недоступен")
    
    logger.info("=" * 60)
    logger.info(f"Веб-интерфейс доступен по адресу: http://{host}:{port}")
    logger.info("=" * 60)
    
    # Запуск Flask приложения
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run_web_interface()
