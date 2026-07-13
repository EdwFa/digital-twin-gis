from .base import BaseAgent
from models.messages import MealIntakeMsg

class GutAgent(BaseAgent):
    def __init__(self, blood_pool, message_bus):
        super().__init__("Gut", blood_pool, message_bus)
        self.stomach_glucose_load = 0.0
        self.V_G = 16.0 # Liters
        
        # Incretin (GLP-1/GIP) params
        self.k_incretin_clearance = 0.35 # /min (DPP-4 rapid degradation, half-life ~2 mins)
        self.incretin_basal_secretion = 3.5 # Maintains basal 10.0 pmol/L (10 * 0.35 = 3.5)
        self.incretin_secretion_factor = 2.0 # GLP-1 secreted per mmol of glucose absorbed
        
        from models.messages import MealIntakeMsg
        self.message_bus.subscribe(self.name, MealIntakeMsg)

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        inc = blood_state["incretin"]
        
        # Process incoming meals
        for msg in messages:
            if isinstance(msg, MealIntakeMsg):
                self.stomach_glucose_load += msg.carbs_g * 5.55 # Rough conversion of g to mmol: 1g = 5.55 mmol

        absorption_rate = 0.0
        if self.stomach_glucose_load > 0:
            # Simple exponential decay gastric emptying
            absorption_rate = self.stomach_glucose_load * 0.05 
            concentration_delta = absorption_rate / self.V_G # Divide by V_G
            
            self.blood_pool.add_glucose_delta(concentration_delta)
            self.stomach_glucose_load -= absorption_rate * step_size
            
        # L/K-cells Incretin secretion
        secretion_inc = self.incretin_basal_secretion + (absorption_rate * self.incretin_secretion_factor)
        clearance_inc = self.k_incretin_clearance * inc
        
        self.blood_pool.add_incretin_delta(secretion_inc - clearance_inc)
