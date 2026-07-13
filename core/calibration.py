from models.passport import PatientPassport_GIS

class GISParameters:
    def __init__(self):
        # Default reference values
        self.S_I = 5.0e-4
        self.adipose_SI = 1.0e-4
        self.beta_mass = 1.0
        self.V_G = 16.0 # L
        self.V_I = 12.0 # L
        self.egp_fasting = 0.179

def calibrate_patient(passport: PatientPassport_GIS) -> GISParameters:
    """Projects patient clinical data onto ODE simulation parameters."""
    params = GISParameters()
    
    BMI = passport.weight_kg / (passport.height_cm / 100)**2
    
    # HOMA-IR calculation (fasting_insulin_pmol_L / 6 gives approx mU/L)
    insulin_mU_L = passport.fasting_insulin_pmol_L / 6.0
    HOMA_IR = (passport.fasting_glucose_mmol_L * insulin_mU_L) / 22.5
    
    HOMA_IR_ref = (5.0 * 10.0) / 22.5 # Reference normal
    
    # 1. Insulin Resistance Shift
    params.S_I = params.S_I * (HOMA_IR_ref / HOMA_IR)
    params.adipose_SI = params.adipose_SI * (HOMA_IR_ref / HOMA_IR)
    
    # 2. Volumes of distribution (Liters)
    params.V_G = 0.18 * passport.weight_kg
    params.V_I = 0.12 * passport.weight_kg
    
    # 3. Base EGP (Liver) adjustments
    if BMI > 25:
        params.egp_fasting = 0.179 * (1 + 0.1 * (BMI - 25))
    
    # 4. Physical activity modifications
    muscle_SI_factor = 1.0 + 0.05 * min(passport.physical_activity_MET_h_week, 15)
    params.S_I *= muscle_SI_factor
    
    # 5. Age modifications
    age_factor_SI = 1.0 - 0.005 * max(0, passport.age - 40)
    params.S_I *= age_factor_SI
    
    # 6. Glucotoxicity (T2D reduction in beta cell capacity)
    if passport.HbA1c_percent > 6.5:
        params.beta_mass = 0.4 # Significant reduction
        
    return params
