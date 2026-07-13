from .base import BaseAgent

class AdiposeAgent(BaseAgent):
    def __init__(self, blood_pool, message_bus):
        super().__init__("Adipose", blood_pool, message_bus)
        self.adipose_SI = 1.0 # Adipose insulin sensitivity
        self.f_adipose = 0.0001
        
        # Lipolysis parameters
        self.basal_lipolysis = 0.04 # mmol/L/min FFA release
        self.k_ffa_clearance = 0.1 # /min (uptake by muscle/liver)
        
        # Endocrine state
        self.leptin_level = 10.0
        self.adiponectin_level = 15.0

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        from models.messages import AdaptationMsg
        for msg in messages:
            if isinstance(msg, AdaptationMsg):
                self.adipose_SI = msg.insulin_sensitivity_multiplier

        g = max(0.1, blood_state["glucose"])
        i = max(0.1, blood_state["insulin"])
        glu = max(0.1, blood_state["glucagon"])
        ffa = max(0.0, blood_state["ffa"])
        
        # 1. Glucose Uptake (Lipogenesis) - converts glucose to fat
        uptake = self.f_adipose * self.adipose_SI * i * g
        self.blood_pool.add_glucose_delta(-uptake)
        
        # 2. Lipolysis (FFA release)
        # Strongly suppressed by insulin (quadratic), stimulated by glucagon
        i_factor = max(0.1, (i / 60.0) * self.adipose_SI)
        glu_factor = glu / 50.0
        
        lipolysis_rate = self.basal_lipolysis * (glu_factor / (i_factor**2))
        
        # Tissues (muscle/liver) continuously consume FFA for basal energy
        ffa_clearance = self.k_ffa_clearance * ffa
        
        self.blood_pool.add_ffa_delta(lipolysis_rate - ffa_clearance)
        
        # 3. Adipokines (Endocrine function)
        # Leptin rises with insulin (satiety signal for Brain in Phase 4)
        self.leptin_level = 10.0 * i_factor
        # Adiponectin represents insulin sensitivity
        self.adiponectin_level = 15.0 * self.adipose_SI
