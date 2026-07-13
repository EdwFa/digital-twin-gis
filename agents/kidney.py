from .base import BaseAgent

class KidneyAgent(BaseAgent):
    def __init__(self, blood_pool, message_bus):
        super().__init__("Kidney", blood_pool, message_bus)
        self.G_threshold = 10.0 # mmol/L (~180 mg/dL)
        self.excretion_rate = 0.1 # Excretion rate when above threshold

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        g = blood_state["glucose"]
        
        # Glycosuria (excretion of glucose in urine)
        if g > self.G_threshold:
            excretion = self.excretion_rate * (g - self.G_threshold)
            self.blood_pool.add_glucose_delta(-excretion)
