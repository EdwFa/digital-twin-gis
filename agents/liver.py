import math
from .base import BaseAgent

class LiverAgent(BaseAgent):
    def __init__(self, blood_pool, message_bus):
        super().__init__("Liver", blood_pool, message_bus)
        self.egp_fasting = 0.179 # Tuned to balance Brain + Muscle at resting G=5.0
        self.f_liver = 0.0001
        
    def calculate_delta(self, current_time, step_size, blood_state, messages):
        g = blood_state["glucose"]
        i = blood_state["insulin"]
        glu = blood_state["glucagon"]
        
        # EGP: Suppressed by insulin, stimulated by glucagon
        insulin_factor = math.exp(-0.01 * (i - 60.0))
        glucagon_factor = math.exp(0.01 * (glu - 70.0))
        
        egp = self.egp_fasting * insulin_factor * glucagon_factor
        
        # Uptake by liver (insulin dependent)
        u_liver = self.f_liver * i * g
        
        net_delta = egp - u_liver
        self.blood_pool.add_glucose_delta(net_delta)
