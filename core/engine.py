from .message_bus import MessageBus

class SimulationEngine:
    """
    Движок симуляции (Simulation Engine).
    Управляет течением времени и координирует вызовы агентов.
    Основан на дискретном времени (Tick-based).
    """
    def __init__(self, step_size_min=1.0):
        self.time_min = 0.0 # Текущее время симуляции в минутах
        self.step_size_min = step_size_min # Шаг интеграции (обычно 1 минута)
        self.agents = [] # Список зарегистрированных агентов верхнего уровня
        self.blood_pool = None # Ссылка на центральный резервуар крови
        self.message_bus = MessageBus() # Локальная шина сообщений

    def add_agent(self, agent):
        """Регистрирует агента верхнего уровня (например, GIS_SuperAgent)."""
        self.agents.append(agent)
    
    def set_blood_pool(self, pool):
        """Подключает центральный резервуар крови."""
        self.blood_pool = pool

    def run(self, duration_min):
        """Запускает симуляцию на заданное количество минут."""
        steps = int(duration_min / self.step_size_min)
        for _ in range(steps):
            self.tick()

    def tick(self):
        """
        Один шаг симуляции (Tick).
        1. Получает неизменяемый снимок состояния крови.
        2. Вызывает метод `_tick` у всех агентов, передавая им состояние крови.
        3. Разрешает (применяет) все накопленные изменения в пуле крови.
        4. Продвигает время вперед.
        """
        blood_state = self.blood_pool.get_state()
        
        # Агенты вычисляют дельты (изменения) на основе текущего состояния
        for agent in self.agents:
            agent._tick(self.time_min, self.step_size_min, blood_state)
        
        # Применение дельт (Euler integration)
        self.blood_pool.resolve_step(self.step_size_min)
        self.time_min += self.step_size_min
