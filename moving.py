# --- ДВИЖЕНИЕ НА СКЛАД ---
        
        # Фаза 0: Поворот назад (0-1.9 сек)
        if self._movement_phase == 0:
            if elapsed < 0.1:
                if not hasattr(self, '_turn_command_sent'):
                    # Поворот (левый мотор назад, правый вперед) или наоборот, как настроено
                    self.serial.send_motor_command(140, 140, 0, 1)
                    self._turn_command_sent = True
                    self.logger.info("Имитация: поворот назад к складу")
                return
            elif elapsed >= 1.9:
                self._movement_phase = 1
                self._loading_step_start = time.time() # Сброс таймера
                if hasattr(self, '_turn_command_sent'):
                    delattr(self, '_turn_command_sent')
                self.logger.info("Имитация: поворот завершен")
                return

        # Фаза 1: Движение назад (или вперед вглубь склада)
        elif self._movement_phase == 1:
            if elapsed < 0.1:
                if not hasattr(self, '_backward_command_sent'):
                    # Движение (1, 1 - это вперед в текущей ориентации)
                    self.serial.send_motor_command(140, 140, 1, 1)
                    self._backward_command_sent = True
                    self.logger.info("Имитация: движение к складу")
                return
            elif elapsed >= 2.0: # Длительность движения
                self._movement_phase = 2
                self._loading_step_start = time.time()
                if hasattr(self, '_backward_command_sent'):
                    delattr(self, '_backward_command_sent')
                self.logger.info("Имитация: движение завершено")
                return

        # Фаза 2: Остановка на складе
        elif self._movement_phase == 2:
            if not hasattr(self, '_stop_command_sent'):
                self.serial.send_motor_command(0, 0, 1, 1)
                self._stop_command_sent = True
                self.logger.info("Имитация: остановка на складе")
            
            # Сразу переходим к ожиданию, но сначала озвучиваем номер
            if self.context.current_order_id is not None:
                self.audio.announce_order_number(self.context.current_order_id)
            
            self._movement_phase = 3
            self._loading_step_start = time.time()
            if hasattr(self, '_stop_command_sent'):
                delattr(self, '_stop_command_sent')
            self.logger.info(f"=== Прибытие, ожидание загрузки ({config.LOADING_CONFIRMATION_TIMEOUT}с) ===")
            return