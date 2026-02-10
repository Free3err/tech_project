#include <FastLED.h>
#include <Servo.h>

// === Пины (Распиновка) ===
#define PWD_R 5      // Скорость правого мотора
#define PWD_L 6      // Скорость левого мотора
#define DIR_R 4      // Направление правого мотора
#define DIR_L 7      // Направление левого мотора
#define IK_SENS A1   // ИК-датчик
#define LED_PIN1 11  // Глаз 1
#define LED_PIN2 12  // Глаз 2
#define SERVO_PIN 10  // Сервопривод коробки

// Пины энкодеров
#define ENCODER_L_A 2   // Левый энкодер, канал A
#define ENCODER_L_B 3   // Левый энкодер, канал B
#define ENCODER_R_A 18  // Правый энкодер, канал A
#define ENCODER_R_B 19  // Правый энкодер, канал B

// === Настройки ленты ===
#define NUM_LEDS 64
#define COLOR_ORDER GRB
#define CHIPSET WS2812B
#define EYE_COLOR CRGB(255, 120, 40)

CRGB leds1[NUM_LEDS];
CRGB leds2[NUM_LEDS];

// === Маски ===
const uint8_t fullEyeMask[64] PROGMEM = {
  0, 0, 1, 1, 1, 1, 0, 0,
  0, 1, 1, 1, 1, 1, 1, 0,
  1, 1, 1, 1, 1, 1, 1, 1,
  1, 1, 1, 1, 1, 1, 1, 1,
  1, 1, 1, 1, 1, 1, 1, 1,
  1, 1, 1, 1, 1, 1, 1, 1,
  0, 1, 1, 1, 1, 1, 1, 0,
  0, 0, 1, 1, 1, 1, 0, 0
};

const uint8_t crossMask[64] PROGMEM = {
  1, 0, 0, 0, 0, 0, 0, 1,
  0, 1, 0, 0, 0, 0, 1, 0,
  0, 0, 1, 0, 0, 1, 0, 0,
  0, 0, 0, 1, 1, 0, 0, 0,
  0, 0, 0, 1, 1, 0, 0, 0,
  0, 0, 1, 0, 0, 1, 0, 0,
  0, 1, 0, 0, 0, 0, 1, 0,
  1, 0, 0, 0, 0, 0, 0, 1
};

// === Состояния и таймеры ===
enum EyeState { EYE_IDLE_OPEN,
                EYE_CLOSING,
                EYE_CLOSED,
                EYE_OPENING };
EyeState eyeState = EYE_IDLE_OPEN;

unsigned long lastEyeUpdate = 0;
unsigned long lastBlink = 0;
int eyeStep = 0;

const unsigned long eyeFrameDelay = 80;
const unsigned long eyeClosedDelay = 300;
const unsigned long eyeIdleDelay = 3000;

// === Переменные управления моторами ===
int leftMotorSpeed = 0;   // Скорость левого мотора (0-255)
int rightMotorSpeed = 0;  // Скорость правого мотора (0-255)
int leftMotorDir = 0;     // Направление левого мотора (0 или 1)
int rightMotorDir = 0;    // Направление правого мотора (0 или 1)

// === Сервопривод ===
Servo boxServo;
int currentServoAngle = 0;  // Текущий угол сервопривода

// === Энкодеры ===
volatile long leftEncoderTicks = 0;   // Счетчик тиков левого энкодера
volatile long rightEncoderTicks = 0;  // Счетчик тиков правого энкодера
unsigned long lastEncoderReport = 0;  // Время последней отправки данных энкодеров
const unsigned long encoderReportInterval = 100;  // Интервал отправки (мс)

// === ИК-датчик ===
unsigned long lastIRReport = 0;  // Время последней отправки данных ИК-датчика
const unsigned long irReportInterval = 200;  // Интервал отправки (мс)

// === Эффекты ===
enum EyeEffect { EFFECT_NONE,
                 EFFECT_SUCCESS,
                 EFFECT_FAILURE,
                 EFFECT_IDLE,
                 EFFECT_WAITING,
                 EFFECT_MOVING };
EyeEffect currentEffect = EFFECT_NONE;
unsigned long effectStart = 0;
const unsigned long effectDuration = 3000;

// === Рисование ===
void drawMask(CRGB *leds, const uint8_t *mask, CRGB color) {
  for (int i = 0; i < 64; i++) {
    leds[i] = pgm_read_byte(&mask[i]) ? color : CRGB::Black;
  }
}

void drawBoth(const uint8_t *mask, CRGB color) {
  drawMask(leds1, mask, color);
  drawMask(leds2, mask, color);
  FastLED.show();
}

void drawEyesFull(CRGB color = EYE_COLOR) {
  drawBoth(fullEyeMask, color);
}

// === Эффект: плавная пульсация (SUCCESS_SCAN) ===
void updateSuccessPulse() {
  unsigned long elapsed = millis() - effectStart;
  if (elapsed > effectDuration) {
    currentEffect = EFFECT_NONE;
    drawEyesFull();
    return;
  }

  float phase = (elapsed % 1000) / 1000.0 * 2 * PI;
  float brightness = 0.6 + 0.4 * sin(phase);
  CRGB color = CRGB(80 * brightness, 255 * brightness, 80 * brightness);

  drawBoth(fullEyeMask, color);
}

// === Эффект: мигающий крест (FAILURE_SCAN) ===
void updateFailureCross() {
  unsigned long elapsed = millis() - effectStart;
  if (elapsed > effectDuration) {
    currentEffect = EFFECT_NONE;
    drawEyesFull();
    return;
  }

  float phase = (elapsed % 600) / 600.0 * 2 * PI;
  float brightness =  0.7 + 0.3 * sin(phase);
  CRGB color = CRGB(255 * brightness, 0, 0);

  drawBoth(crossMask, color);
}

// === Эффект: анимация ожидания (WAITING) ===
void updateWaitingAnimation() {
  // Медленная пульсация синим цветом
  unsigned long elapsed = millis() - effectStart;
  float phase = (elapsed % 2000) / 2000.0 * 2 * PI;
  float brightness =0.5 + 0.5 * sin(phase);
  CRGB color = CRGB(100 * brightness, 150 * brightness, 255 * brightness);
  
  drawBoth(fullEyeMask, color);
}

// === Эффект: анимация движения (MOVING) ===
void updateMovingAnimation() {
  // Быстрая пульсация оранжевым цветом
  unsigned long elapsed = millis() - effectStart;
  float phase = (elapsed % 800) / 800.0 * 2 * PI;
  float brightness = 0.6 + 0.4 * sin(phase);
  CRGB color = CRGB(255 * brightness, 140 * brightness, 0);
  
  drawBoth(fullEyeMask, color);
}

// === Управление строками глаз (для моргания) ===
void setEyeLine(CRGB *leds, int row, bool on, CRGB color = EYE_COLOR) {
  CRGB c = on ? color : CRGB::Black;
  for (int col = 0; col < 8; col++) {
    int index = row * 8 + col;
    if (pgm_read_byte(&fullEyeMask[index])) leds[index] = c;
  }
}

// === Обновление состояния глаз (моргание) ===
void updateEyes() {
  if (currentEffect != EFFECT_NONE && currentEffect != EFFECT_IDLE) return;

  unsigned long now = millis();

  switch (eyeState) {
    case EYE_IDLE_OPEN:
      if (now - lastBlink > eyeIdleDelay) {
        eyeState = EYE_CLOSING;
        eyeStep = 0;
        lastEyeUpdate = now;
      }
      break;

    case EYE_CLOSING:
      if (now - lastEyeUpdate > eyeFrameDelay) {
        setEyeLine(leds1, eyeStep, false);
        setEyeLine(leds1, 7 - eyeStep, false);
        setEyeLine(leds2, eyeStep, false);
        setEyeLine(leds2, 7 - eyeStep, false);
        FastLED.show();

        eyeStep++;
        lastEyeUpdate = now;

        if (eyeStep > 3) {
          eyeState = EYE_CLOSED;
          lastEyeUpdate = now;
        }
      }
      break;

    case EYE_CLOSED:
      if (now - lastEyeUpdate > eyeClosedDelay) {
        eyeState = EYE_OPENING;
        eyeStep = 3;
        lastEyeUpdate = now;
      }
      break;

    case EYE_OPENING:
      if (now - lastEyeUpdate > eyeFrameDelay) {
        setEyeLine(leds1, eyeStep, true);
        setEyeLine(leds1, 7 - eyeStep, true);
        setEyeLine(leds2, eyeStep, true);
        setEyeLine(leds2, 7 - eyeStep, true);
        FastLED.show();

        eyeStep--;
        lastEyeUpdate = now;

        if (eyeStep < 0) {
          eyeState = EYE_IDLE_OPEN;
          drawEyesFull();
          lastBlink = now;
        }
      }
      break;
  }
}

// === Запуск эффектов ===
void eyesSuccessEffect() {
  currentEffect = EFFECT_SUCCESS;
  effectStart = millis();
}

void eyesFailureEffect() {
  currentEffect = EFFECT_FAILURE;
  effectStart = millis();
}

void eyesIdleAnimation() {
  currentEffect = EFFECT_IDLE;
  effectStart = millis();
}

void eyesWaitingAnimation() {
  currentEffect = EFFECT_WAITING;
  effectStart = millis();
}

void eyesMovingAnimation() {
  currentEffect = EFFECT_MOVING;
  effectStart = millis();
}

// === Управление моторами ===
// Функция установки скорости и направления моторов
void setMotorSpeed(int leftSpeed, int rightSpeed, int leftDir, int rightDir) {
  // Ограничение значений скорости
  leftSpeed = constrain(leftSpeed, 0, 255);
  rightSpeed = constrain(rightSpeed, 0, 255);
  
  // Установка направления
  digitalWrite(DIR_L, leftDir);
  digitalWrite(DIR_R, rightDir);
  
  // Установка скорости через PWM
  analogWrite(PWD_L, leftSpeed);
  analogWrite(PWD_R, rightSpeed);
  
  // Сохранение текущих значений
  leftMotorSpeed = leftSpeed;
  rightMotorSpeed = rightSpeed;
  leftMotorDir = leftDir;
  rightMotorDir = rightDir;
}

// Парсинг команды управления моторами
// Формат: MOTOR:<left_speed>,<right_speed>,<left_dir>,<right_dir>
void parseMotorCommand(String cmd) {
  // Удаляем префикс "MOTOR:"
  cmd = cmd.substring(6);
  
  // Парсим параметры
  int firstComma = cmd.indexOf(',');
  int secondComma = cmd.indexOf(',', firstComma + 1);
  int thirdComma = cmd.indexOf(',', secondComma + 1);
  
  if (firstComma == -1 || secondComma == -1 || thirdComma == -1) {
    Serial.println("ERROR: Invalid MOTOR command format");
    return;
  }
  
  int leftSpeed = cmd.substring(0, firstComma).toInt();
  int rightSpeed = cmd.substring(firstComma + 1, secondComma).toInt();
  int leftDir = cmd.substring(secondComma + 1, thirdComma).toInt();
  int rightDir = cmd.substring(thirdComma + 1).toInt();
  
  setMotorSpeed(leftSpeed, rightSpeed, leftDir, rightDir);
  Serial.println("ACK");
}

// === Управление сервоприводом ===
// Функция установки угла сервопривода
void setServoAngle(int angle) {
  // Ограничение угла в диапазоне 0-90 градусов
  angle = constrain(angle, 0, 180);
  
  boxServo.write(angle);
  currentServoAngle = angle;
}

// Парсинг команды управления сервоприводом
// Формат: SERVO:<angle>
void parseServoCommand(String cmd) {
  // Удаляем префикс "SERVO:"
  cmd = cmd.substring(6);
  
  int angle = cmd.toInt();
  
  if (angle < 0 || angle > 180) {
    Serial.println("ERROR: Invalid SERVO angle (must be 0-90)");
    return;
  }
  
  setServoAngle(angle);
  Serial.println("ACK");
}

// === Энкодеры ===
// Обработчики прерываний для энкодеров
void leftEncoderISR() {
  // Простой подсчет тиков (можно улучшить с учетом направления)
  if (digitalRead(ENCODER_L_B) == HIGH) {
    leftEncoderTicks++;
  } else {
    leftEncoderTicks--;
  }
}

void rightEncoderISR() {
  // Простой подсчет тиков (можно улучшить с учетом направления)
  if (digitalRead(ENCODER_R_B) == HIGH) {
    rightEncoderTicks++;
  } else {
    rightEncoderTicks--;
  }
}

// Отправка данных энкодеров на Raspberry Pi
void sendEncoderData() {
  Serial.print("ENCODER:");
  Serial.print(leftEncoderTicks);
  Serial.print(",");
  Serial.println(rightEncoderTicks);
}

// === ИК-датчик ===
// Чтение данных ИК-датчика
int readIRSensor() {
  // Читаем аналоговое значение с ИК-датчика
  int rawValue = analogRead(IK_SENS);
  
  // Преобразование в расстояние (зависит от конкретного датчика)
  // Для Sharp GP2Y0A21YK: distance (cm) ≈ 27.86 * (rawValue^-1.15)
  // Упрощенная линейная аппроксимация для диапазона 10-80 см
  // Возвращаем сырое значение, преобразование будет на стороне Raspberry Pi
  return rawValue;
}

// Отправка данных ИК-датчика на Raspberry Pi
void sendIRData() {
  int distance = readIRSensor();
  Serial.print("IR:");
  Serial.println(distance);
}

// === Инициализация ===
void setup() {
  Serial.begin(9600);
  while (!Serial) {}

  // Инициализация пинов моторов (чтобы они не висели в воздухе)
  pinMode(DIR_R, OUTPUT);
  pinMode(PWD_R, OUTPUT);
  pinMode(DIR_L, OUTPUT);
  pinMode(PWD_L, OUTPUT);
  pinMode(IK_SENS, INPUT);

  // Инициализация энкодеров
  pinMode(ENCODER_L_A, INPUT_PULLUP);
  pinMode(ENCODER_L_B, INPUT_PULLUP);
  pinMode(ENCODER_R_A, INPUT_PULLUP);
  pinMode(ENCODER_R_B, INPUT_PULLUP);
  
  // Подключение прерываний для энкодеров
  attachInterrupt(digitalPinToInterrupt(ENCODER_L_A), leftEncoderISR, RISING);
  attachInterrupt(digitalPinToInterrupt(ENCODER_R_A), rightEncoderISR, RISING);

  // Инициализация сервопривода
  boxServo.attach(SERVO_PIN);
  // Не устанавливаем начальную позицию - серво остается на своем месте
  currentServoAngle = 62;  // Неизвестная позиция, будет установлена командой

  // Инициализация ленты
  FastLED.addLeds<CHIPSET, LED_PIN1, COLOR_ORDER>(leds1, NUM_LEDS);
  FastLED.addLeds<CHIPSET, LED_PIN2, COLOR_ORDER>(leds2, NUM_LEDS);
  FastLED.setBrightness(25);

  drawEyesFull();
  FastLED.show();
  lastBlink = millis();
  lastEncoderReport = millis();
  lastIRReport = millis();

  // Серво
  boxServo.write(112);
  delay(500);
  boxServo.write(35);
  delay(500);
  boxServo.write(62);
}

// === Главный цикл ===
void loop() {
  // Команды по Serial
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input == "SUCCESS_SCAN") {
      eyesSuccessEffect();
      Serial.println("ACK");
    } else if (input == "FAILURE_SCAN") {
      eyesFailureEffect();
      Serial.println("ACK");
    } else if (input == "LED_IDLE") {
      eyesIdleAnimation();
      Serial.println("ACK");
    } else if (input == "LED_WAITING") {
      eyesWaitingAnimation();
      Serial.println("ACK");
    } else if (input == "LED_MOVING") {
      eyesMovingAnimation();
      Serial.println("ACK");
    } else if (input.startsWith("MOTOR:")) {
      parseMotorCommand(input);
    } else if (input.startsWith("SERVO:")) {
      parseServoCommand(input);
    } else if (input == "STOP") {
      setMotorSpeed(0, 0, 0, 0);
      Serial.println("ACK");
    }
  }

  // Периодическая отправка данных энкодеров
  unsigned long currentTime = millis();
  if (currentTime - lastEncoderReport >= encoderReportInterval) {
    sendEncoderData();
    lastEncoderReport = currentTime;
  }

  // Периодическая отправка данных ИК-датчика
  if (currentTime - lastIRReport >= irReportInterval) {
    sendIRData();
    lastIRReport = currentTime;
  }

  // Обновление эффектов и состояния глаз
  if (currentEffect == EFFECT_SUCCESS) updateSuccessPulse();
  else if (currentEffect == EFFECT_FAILURE) updateFailureCross();
  else if (currentEffect == EFFECT_WAITING) updateWaitingAnimation();
  else if (currentEffect == EFFECT_MOVING) updateMovingAnimation();
  else updateEyes();
}