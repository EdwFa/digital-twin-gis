from .base import BaseAgent
from models.messages import AdaptationMsg
import math

class SlowAdaptationAgent(BaseAgent):
    def __init__(self, blood_pool, message_bus):
        super().__init__("SlowAdaptation", blood_pool, message_bus)
        # Smoothing factor for HbA1c (roughly 30 days half-life)
        self.k_hba1c = 1.0 / 43200.0
        self.hba1c_estimate = 5.0 # Starting safe assumption (%)
        
        # Lipotoxicity tracking (average FFA over ~7 days)
        self.k_ffa_avg = 1.0 / 10000.0 
        self.ffa_avg = 0.4 
        
        self.beta_mass_multiplier = 1.0
        self.si_multiplier = 1.0
        
        self.k_apoptosis = 1.0e-6
        self.k_lipotoxicity = 1.0e-6

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        g = blood_state["glucose"]
        ffa = max(0.0, blood_state["ffa"])
        
        # 1. HbA1c Glucotoxicity
        # Convert glucose (mmol/L) to instantaneous HbA1c contribution (%)
        instant_hba1c = (g + 2.59) / 1.59
        self.hba1c_estimate += (instant_hba1c - self.hba1c_estimate) * self.k_hba1c * step_size
        
        if self.hba1c_estimate > 6.5:
            # Beta cells die (apoptosis)
            degradation = self.k_apoptosis * (self.hba1c_estimate - 6.5) * step_size
            self.beta_mass_multiplier = max(0.1, self.beta_mass_multiplier - degradation)
            
        # 2. FFA Lipotoxicity (Insulin Resistance drift)
        self.ffa_avg += (ffa - self.ffa_avg) * self.k_ffa_avg * step_size
        if self.ffa_avg > 0.6:
            # Insulin sensitivity drops globally
            degradation_si = self.k_lipotoxicity * (self.ffa_avg - 0.6) * step_size
            self.si_multiplier = max(0.1, self.si_multiplier - degradation_si)
            
        # 3. Publish adaptation message for target organs
        msg = AdaptationMsg(
            beta_mass_multiplier=self.beta_mass_multiplier,
            insulin_sensitivity_multiplier=self.si_multiplier
        )
        self.message_bus.publish(msg)
