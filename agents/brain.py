from .base import BaseAgent

class BrainAgent(BaseAgent):
    def __init__(self, blood_pool, message_bus):
        super().__init__("Brain", blood_pool, message_bus)
        
    def calculate_delta(self, current_time, step_size, blood_state, messages):
        # Brain consumes glucose at a constant rate, independent of insulin
        # Approx 120 g/day = 0.083 g/min.
        # Assuming V_G = 16 L, 0.083 g = 0.46 mmol -> 0.0288 mmol/L/min drop
        uptake_rate = 0.0288
        
        # Don't let glucose drop below zero
        if blood_state["glucose"] > 0:
            self.blood_pool.add_glucose_delta(-uptake_rate)
