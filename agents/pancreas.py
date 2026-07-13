from .base import BaseAgent
from models.messages import HormoneSecretionMsg

class PancreasAgent(BaseAgent):
    def __init__(self, blood_pool, message_bus):
        super().__init__("Pancreas", blood_pool, message_bus)
        # Topp model params
        self.alpha = 25.0
        self.k_I = 0.06 # Insulin clearance rate (/min)
        self.beta_mass = 1.0 # Beta cell mass multiplier
        
        # Glucagon params
        self.n_glu = 2.0
        self.G_ref = 5.0
        self.k_Glu = 0.05
        
    def calculate_delta(self, current_time, step_size, blood_state, messages):
        g = blood_state["glucose"]
        i = blood_state["insulin"]
        glu = blood_state["glucagon"]
        
        # --- Beta Cells (Insulin) ---
        # Secretion (Hill function) tuned for fasting state I=60 at G=5.0
        secretion_i = 7.2 * self.beta_mass * (g**2) / (self.alpha + g**2)
        clearance_i = self.k_I * i
        
        self.blood_pool.add_insulin_delta(secretion_i - clearance_i)
        
        # --- Alpha Cells (Glucagon) ---
        # Secretion tuned for fasting state Glu=70 at G=5.0
        secretion_glu = 3.5 * ((self.G_ref / g) ** self.n_glu) if g > 0.1 else 0
        clearance_glu = self.k_Glu * glu
        
        self.blood_pool.add_glucagon_delta(secretion_glu - clearance_glu)
