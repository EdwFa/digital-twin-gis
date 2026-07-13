from .base import BaseAgent

class BrainAgent(BaseAgent):
    """
    Агент Мозга (Brain Agent).
    Облигатный (обязательный) потребитель глюкозы. Не зависит от инсулина.
    """
    def __init__(self, blood_pool, message_bus):
        super().__init__("Brain", blood_pool, message_bus)
        
    def calculate_delta(self, current_time, step_size, blood_state, messages):
        # Мозг потребляет глюкозу с постоянной скоростью.
        # Примерно 120 г/день = 0.083 г/мин.
        # При объеме V_G = 16 Л, 0.083 г = 0.46 ммоль -> 0.0288 ммоль/Л/мин падение концентрации
        uptake_rate = 0.0288
        
        # Защита от падения концентрации глюкозы ниже нуля
        if blood_state["glucose"] > 0:
            self.blood_pool.add_glucose_delta(-uptake_rate)
