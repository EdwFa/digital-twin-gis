class BloodPool:
    def __init__(self):
        self.glucose = 5.0 # mmol/L
        self.insulin = 60.0 # pmol/L (fasting normal)
        self.glucagon = 70.0 # pg/mL
        
        self.glucose_deltas = []
        self.insulin_deltas = []
        self.glucagon_deltas = []

    def get_state(self):
        return {
            "glucose": self.glucose, 
            "insulin": self.insulin,
            "glucagon": self.glucagon
        }

    def add_glucose_delta(self, amount):
        self.glucose_deltas.append(amount)

    def add_insulin_delta(self, amount):
        self.insulin_deltas.append(amount)
        
    def add_glucagon_delta(self, amount):
        self.glucagon_deltas.append(amount)

    def resolve_step(self, step_size_min):
        total_g_delta = sum(self.glucose_deltas)
        total_i_delta = sum(self.insulin_deltas)
        total_glu_delta = sum(self.glucagon_deltas)
        
        self.glucose += total_g_delta * step_size_min
        self.insulin += total_i_delta * step_size_min
        self.glucagon += total_glu_delta * step_size_min
        
        self.glucose_deltas.clear()
        self.insulin_deltas.clear()
        self.glucagon_deltas.clear()
        
        self.glucose = max(0.0, self.glucose)
        self.insulin = max(0.0, self.insulin)
        self.glucagon = max(0.0, self.glucagon)
