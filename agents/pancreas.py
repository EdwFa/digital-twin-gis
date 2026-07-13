from .base import BaseAgent
from models.messages import HormoneSecretionMsg

class PancreasAgent(BaseAgent):
    def __init__(self, blood_pool, message_bus):
        super().__init__("Pancreas", blood_pool, message_bus)
        # Beta Cell Pools (Insulin)
        self.beta_mass = 1.0
        self.M1 = 100.0   # Readily Releasable Pool (RRP)
        self.M2 = 1000.0  # Reserve Pool
        self.k_release_max = 0.072
        self.k_transfer = 0.00072
        self.basal_synthesis = 3.6
        self.alpha_hill = 25.0
        self.k_I_clearance = 0.06
        
        # Alpha Cell (Glucagon)
        self.k_Glu_clearance = 0.05
        self.basal_glu_secr = 2.5
        
        # Delta Cell (Somatostatin paracrine effect)
        self.k_sst = 0.2
        
    def calculate_delta(self, current_time, step_size, blood_state, messages):
        from models.messages import AdaptationMsg
        for msg in messages:
            if isinstance(msg, AdaptationMsg):
                self.beta_mass = msg.beta_mass_multiplier

        g = max(0.1, blood_state["glucose"]) # avoid div by zero
        i = max(0.1, blood_state["insulin"])
        glu = max(0.1, blood_state["glucagon"])
        inc = max(1.0, blood_state["incretin"])
        
        incretin_factor = inc / 10.0
        # Cap incretin multiplier to a biological maximum (e.g. 5x) to prevent instantaneous M1 depletion
        incretin_factor = min(5.0, incretin_factor)
        
        # --- Delta Cells (Somatostatin) ---
        # Somatostatin is stimulated by Glucose and Incretins. 
        # Normalized to 1.0 at basal fasting state.
        sst_factor = (g / 5.0) * incretin_factor
        basal_inhibition_val = 1.0 / (1.0 + self.k_sst)
        paracrine_inhibition = (1.0 / (1.0 + self.k_sst * sst_factor)) / basal_inhibition_val
        
        # --- Beta Cells (Insulin 2-pool model) ---
        # 1. Release from M1 to blood
        k_release = self.k_release_max * (g**2) / (self.alpha_hill + g**2) * incretin_factor
        actual_release_rate = k_release * paracrine_inhibition * self.beta_mass
        secretion_i = actual_release_rate * self.M1
        
        # 2. Transfer M2 -> M1 (GLP-1 highly stimulates mobilization)
        transfer_rate = self.k_transfer * self.M2 * g * incretin_factor
        
        # 3. Synthesis into M2
        synthesis = self.basal_synthesis * (g / 5.0) * self.beta_mass
        
        # Update intra-cellular pools
        self.M1 += (transfer_rate - secretion_i) * step_size
        self.M2 += (synthesis - transfer_rate) * step_size
        self.M1 = max(0.0, self.M1)
        self.M2 = max(0.0, self.M2)
        
        clearance_i = self.k_I_clearance * i
        self.blood_pool.add_insulin_delta(secretion_i - clearance_i)
        
        # --- Alpha Cells (Glucagon) ---
        # Inhibited by Glucose, Insulin, Incretin, and Somatostatin
        glu_secretion = self.basal_glu_secr * (25.0 / (g**2)) * (60.0 / i) * (1.0 / incretin_factor) * paracrine_inhibition
        glu_secretion = min(glu_secretion, 50.0) # Prevent runaway math at very low G
        
        glu_clearance = self.k_Glu_clearance * glu
        self.blood_pool.add_glucagon_delta(glu_secretion - glu_clearance)
