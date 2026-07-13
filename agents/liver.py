import math
from .base import BaseAgent

class LiverAgent(BaseAgent):
    def __init__(self, blood_pool, message_bus):
        super().__init__("Liver", blood_pool, message_bus)
        self.egp_fasting = 0.179 # Endogenous Glucose Production at fasting (mmol/L/min)
        self.liver_SI = 1.0 # Liver insulin sensitivity
        
        # Glycogen Pool (Capacity equivalent in mmol/L: ~100g / 16L = ~35.0 mmol/L)
        self.max_glycogen = 35.0
        self.glycogen_pool = 25.0 # ~70% full at start
        
        self.k_uptake = 0.0001 # Rate constant for insulin-dependent glucose uptake

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        from models.messages import AdaptationMsg
        for msg in messages:
            if isinstance(msg, AdaptationMsg):
                self.liver_SI = msg.insulin_sensitivity_multiplier

        g = max(0.1, blood_state["glucose"])
        i = max(0.1, blood_state["insulin"])
        glu = max(0.1, blood_state["glucagon"])
        
        # Basal ratios (30% GNG, 70% GGL)
        GNG_basal = 0.3 * self.egp_fasting
        GGL_basal = 0.7 * self.egp_fasting
        
        # Hormonal multipliers
        i_factor = max(0.1, (i / 60.0) * self.liver_SI)
        glu_factor = glu / 50.0
        hormonal_drive = glu_factor / i_factor
        
        # 1. Gluconeogenesis (GNG)
        GNG = GNG_basal * hormonal_drive
        
        # 2. Glycogenolysis (GGL)
        GGL = GGL_basal * hormonal_drive
        if self.glycogen_pool < 5.0:
            GGL *= max(0.0, self.glycogen_pool / 5.0) # Linearly drops to 0
            
        # 3. Glucose Uptake (Glycogenesis)
        # capacity_factor: slows down uptake sharply as pool gets close to max
        capacity_factor = max(0.0, 1.0 - (self.glycogen_pool / self.max_glycogen)**4)
        uptake = self.k_uptake * g * i * self.liver_SI * capacity_factor
        
        # Apply to local pool
        self.glycogen_pool += (uptake - GGL) * step_size
        self.glycogen_pool = max(0.0, min(self.max_glycogen, self.glycogen_pool))
        
        # Add net glucose to blood (GNG + GGL - uptake)
        net_glucose_flux = GNG + GGL - uptake
        self.blood_pool.add_glucose_delta(net_glucose_flux)
