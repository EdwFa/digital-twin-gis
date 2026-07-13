class BloodPool:
    def __init__(self):
        # Base concentrations
        self.glucose = 5.0  # mmol/L
        self.insulin = 60.0 # pmol/L
        self.glucagon = 50.0 # pg/mL
        self.incretin = 10.0 # pmol/L (GLP-1 basal)
        self.ffa = 0.4 # mmol/L (Free fatty acids)
        
        # Delta buffers for integration step
        self._g_delta = 0.0
        self._i_delta = 0.0
        self._glu_delta = 0.0
        self._inc_delta = 0.0
        self._ffa_delta = 0.0
        
    def add_glucose_delta(self, amount):
        self._g_delta += amount
        
    def add_insulin_delta(self, amount):
        self._i_delta += amount
        
    def add_glucagon_delta(self, amount):
        self._glu_delta += amount

    def add_incretin_delta(self, amount):
        self._inc_delta += amount

    def add_ffa_delta(self, amount):
        self._ffa_delta += amount
        
    def get_state(self):
        return {
            "glucose": self.glucose,
            "insulin": self.insulin,
            "glucagon": self.glucagon,
            "incretin": self.incretin,
            "ffa": self.ffa
        }
        
    def resolve_step(self, step_size_min):
        # Basic Euler integration
        self.glucose = max(0.0, self.glucose + self._g_delta * step_size_min)
        self.insulin = max(0.0, self.insulin + self._i_delta * step_size_min)
        self.glucagon = max(0.0, self.glucagon + self._glu_delta * step_size_min)
        self.incretin = max(0.0, self.incretin + self._inc_delta * step_size_min)
        self.ffa = max(0.0, self.ffa + self._ffa_delta * step_size_min)
        
        # Reset deltas
        self._g_delta = 0.0
        self._i_delta = 0.0
        self._glu_delta = 0.0
        self._inc_delta = 0.0
        self._ffa_delta = 0.0
