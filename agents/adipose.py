from .base import BaseAgent

class AdiposeAgent(BaseAgent):
    def __init__(self, blood_pool, message_bus):
        super().__init__("Adipose", blood_pool, message_bus)
        self.adipose_SI = 1.0e-4 # Less sensitive than muscle

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        g = blood_state["glucose"]
        i = blood_state["insulin"]
        
        # Lipogenesis (glucose uptake by fat cells)
        uptake = self.adipose_SI * i * g
        
        self.blood_pool.add_glucose_delta(-uptake)
