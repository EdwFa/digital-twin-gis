from .base import BaseAgent

class SlowAdaptationAgent(BaseAgent):
    def __init__(self, blood_pool, message_bus):
        super().__init__("SlowAdaptation", blood_pool, message_bus, tick_rate=1440) # Tick once a day
        self.HbA1c = 5.0 # Baseline %
        
    def calculate_delta(self, current_time, step_size, blood_state, messages):
        g = blood_state["glucose"]
        
        # Approximate target A1c based on current glucose.
        # eAG(mg/dL) = 28.7 * A1c - 46.7
        # In mmol/L: G = 1.59 * A1c - 2.59
        A1c_target = (g + 2.59) / 1.59
        
        # dHbA1c/dt = (A1c_target - HbA1c) / tau
        tau_days = 30.0
        days_passed = step_size / 1440.0
        
        self.HbA1c += ((A1c_target - self.HbA1c) / tau_days) * days_passed
