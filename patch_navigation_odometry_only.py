#!/usr/bin/env python3
"""
Патч для navigation.py - использовать только одометрию
Временное решение пока не исправим парсинг LiDAR
"""

import fileinput
import sys

print("Патчинг navigation.py для использования только одометрии...")

# Читаем файл
with open('navigation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим метод update_localization
start_marker = "def update_localization(self) -> None:"
end_marker = "raise LocalizationFailureError(f\"Критическая ошибка локализации: {e}\")"

if start_marker in content and end_marker in content:
    # Находим начало и конец метода
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker, start_idx) + len(end_marker)
    
    # Новая реализация метода
    new_method = '''def update_localization(self) -> None:
        """
        Обновление локализации робота
        
        ВРЕМЕННО: Используем только одометрию без LiDAR
        из-за проблем с парсингом данных LiDAR
        """
        try:
            # Используем только одометрию
            x, y, theta = self.odometry.get_pose()
            self.estimated_position = Position(x, y, theta)
            
            self.logger.debug(f"Позиция (одометрия): x={x:.3f}, y={y:.3f}, theta={theta:.3f}")
            
        except Exception as e:
            self.logger.error(f"Ошибка обновления локализации: {e}")
            raise LocalizationFailureError(f"Критическая ошибка локализации: {e}")'''
    
    # Заменяем метод
    new_content = content[:start_idx] + new_method + content[end_idx:]
    
    # Записываем обратно
    with open('navigation.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✓ Патч применен успешно!")
    print("  Теперь используется только одометрия без LiDAR")
    print("  Это временное решение для тестирования")
else:
    print("✗ Не удалось найти метод update_localization")
    sys.exit(1)
