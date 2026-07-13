from .base import BaseAgent

class MuscleAgent(BaseAgent):
    def __init__(self, blood_pool, message_bus):
        super().__init__("Muscle", blood_pool, message_bus)
        self.muscle_SI = 1.0 # Muscle insulin sensitivity
        self.f_muscle = 0.0003
        
        # Glycogen Pool (Capacity equivalent in mmol/L: ~400g / 16L = ~140.0 mmol/L)
        self.max_glycogen = 140.0
        self.glycogen_pool = 100.0 # ~70% full at start
        
        self.basal_burn_rate = 0.09 # mmol/L/min (burns glucose internally)

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        from models.messages import AdaptationMsg
        for msg in messages:
            if isinstance(msg, AdaptationMsg):
                self.muscle_SI = msg.insulin_sensitivity_multiplier

        g = blood_state["glucose"]
        i = blood_state["insulin"]
        
        # Capacity factor: 1.0 normally, drops sharply to 0 as pool nears max
        capacity_factor = max(0.0, 1.0 - (self.glycogen_pool / self.max_glycogen)**4)
        
        # Insulin-dependent glucose uptake (GLUT4) from blood into muscle
        uptake = self.f_muscle * self.muscle_SI * i * g * capacity_factor
        
        # Muscle constantly burns its glycogen for energy
        burn = min(self.basal_burn_rate, self.glycogen_pool / step_size)
        
        # Update local glycogen
        self.glycogen_pool += (uptake - burn) * step_size
        self.glycogen_pool = max(0.0, min(self.max_glycogen, self.glycogen_pool))
        
        # Uptake removes glucose from the blood pool
        self.blood_pool.add_glucose_delta(-uptake)
