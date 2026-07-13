from .base import BaseAgent

class KidneyAgent(BaseAgent):
    """
    Агент Почек (Kidney Agent).
    Выполняет роль фильтра крови. При нормальном уровне сахара не влияет на глюкозу.
    При превышении почечного порога выводит излишки сахара с мочой (глюкозурия).
    """
    def __init__(self, blood_pool, message_bus):
        super().__init__("Kidney", blood_pool, message_bus)
        self.G_threshold = 10.0 # Почечный порог (ммоль/Л) - примерно 180 мг/дл
        self.excretion_rate = 0.1 # Скорость выведения (экскреции) при превышении порога

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        g = blood_state["glucose"]
        
        # Глюкозурия (выведение глюкозы с мочой)
        if g > self.G_threshold:
            excretion = self.excretion_rate * (g - self.G_threshold)
            self.blood_pool.add_glucose_delta(-excretion)
