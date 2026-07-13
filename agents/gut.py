from .base import BaseAgent
from models.messages import MealIntakeMsg

class GutAgent(BaseAgent):
    def __init__(self, blood_pool, message_bus):
        super().__init__("Gut", blood_pool, message_bus)
        self.stomach_glucose_load = 0.0
        self.V_G = 16.0 # Liters

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        # Process incoming meals
        for msg in messages:
            if isinstance(msg, MealIntakeMsg):
                self.stomach_glucose_load += msg.carbs_g * 5.55 # Rough conversion of g to mmol: 1g = 5.55 mmol

        if self.stomach_glucose_load > 0:
            # Simple exponential decay gastric emptying
            absorption_rate = self.stomach_glucose_load * 0.05 
            concentration_delta = absorption_rate / self.V_G # Divide by V_G
            
            self.blood_pool.add_glucose_delta(concentration_delta)
            self.stomach_glucose_load -= absorption_rate * step_size
