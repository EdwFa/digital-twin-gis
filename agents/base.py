from core.message_bus import MessageBus

class BaseAgent:
    """
    Базовый класс для всех агентов органов.
    Обеспечивает подключение к шине сообщений и пулу крови, а также задает
    интерфейс для расчета биологических изменений.
    """
    def __init__(self, name: str, blood_pool, message_bus: MessageBus, tick_rate: int = 1):
        self.name = name
        self.blood_pool = blood_pool
        self.message_bus = message_bus
        
        # Возможность обновлять орган реже, чем базовый тик движка (например, для медленных процессов)
        self.tick_rate = tick_rate 
        self.ticks_since_update = 0
        
        # Регистрация почтового ящика на шине сообщений
        self.message_bus.register_mailbox(name)

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        """
        Метод расчета влияния органа на систему за текущий шаг времени.
        Должен быть переопределен в дочерних классах (органах).
        
        :param current_time: Текущее время симуляции (мин)
        :param step_size: Размер временного шага интеграции (мин)
        :param blood_state: Снимок текущих концентраций в крови
        :param messages: Список сообщений, полученных органом с момента прошлого тика
        """
        raise NotImplementedError
        
    def _tick(self, current_time, step_size, blood_state):
        """
        Внутренний метод обновления агента. Вызывается движком.
        Управляет частотой обновления (tick_rate) и сбором сообщений.
        """
        self.ticks_since_update += 1
        if self.ticks_since_update >= self.tick_rate:
            # Чтение и очистка почтового ящика
            messages = self.message_bus.consume(self.name)
            # Фактический шаг времени для агента (если он обновляется реже)
            actual_step = step_size * self.tick_rate
            self.calculate_delta(current_time, actual_step, blood_state, messages)
            self.ticks_since_update = 0
