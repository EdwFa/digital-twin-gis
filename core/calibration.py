from models.passport import PatientPassport_GIS

class GISParameters:
    """
    Класс, хранящий откалиброванные множители и параметры для органов.
    Эти параметры проецируются на внутренние уравнения ОДУ (ODE) симуляции.
    """
    def __init__(self):
        # Базовые референсные множители (1.0 = здоровый идеальный человек)
        self.muscle_SI = 1.0   # Чувствительность мышц к инсулину
        self.adipose_SI = 1.0  # Чувствительность жировой ткани к инсулину
        self.liver_SI = 1.0    # Чувствительность печени к инсулину
        self.beta_mass = 1.0   # Относительная масса бета-клеток поджелудочной
        self.V_G = 16.0        # Объем распределения глюкозы (Литры)
        self.V_I = 12.0        # Объем распределения инсулина (Литры)
        self.egp_fasting = 0.179 # Базовая эндогенная продукция глюкозы печенью

def calibrate_patient(passport: PatientPassport_GIS) -> GISParameters:
    """
    Проецирует клинические данные пациента (Паспорт) на параметры симуляции (ODE).
    """
    params = GISParameters()
    
    # Расчет индекса массы тела (BMI)
    BMI = passport.weight_kg / (passport.height_cm / 100)**2
    
    # Расчет индекса инсулинорезистентности HOMA-IR
    # Перевод инсулина из pmol/L в mU/L (примерно делим на 6)
    insulin_mU_L = passport.fasting_insulin_pmol_L / 6.0
    HOMA_IR = (passport.fasting_glucose_mmol_L * insulin_mU_L) / 22.5
    
    HOMA_IR_ref = (5.0 * 10.0) / 22.5 # Референсный (здоровый) HOMA-IR (~2.22)
    
    # 1. Смещение инсулинорезистентности (Для всех тканей)
    # Чем выше HOMA-IR пациента, тем ниже множители SI (чувствительности)
    params.muscle_SI *= (HOMA_IR_ref / HOMA_IR)
    params.adipose_SI *= (HOMA_IR_ref / HOMA_IR)
    params.liver_SI *= (HOMA_IR_ref / HOMA_IR)
    
    # 2. Объемы распределения (Литры) зависят от веса
    params.V_G = 0.18 * passport.weight_kg
    params.V_I = 0.12 * passport.weight_kg
    
    # 3. Базовая выработка глюкозы печенью (EGP)
    # У людей с избыточным весом (BMI > 25) печень больше и вырабатывает больше сахара
    if BMI > 25:
        params.egp_fasting = 0.179 * (1 + 0.1 * (BMI - 25))
    
    # 4. Модификаторы физической активности
    # Спорт напрямую улучшает чувствительность мышц к инсулину (независимо от веса)
    muscle_SI_factor = 1.0 + 0.05 * min(passport.physical_activity_MET_h_week, 15)
    params.muscle_SI *= muscle_SI_factor
    
    # 5. Возрастные модификаторы
    # После 40 лет эластичность тканей падает (естественное старение)
    age_factor_SI = 1.0 - 0.005 * max(0, passport.age - 40)
    params.muscle_SI *= age_factor_SI
    params.liver_SI *= age_factor_SI
    
    # 6. Глюкотоксичность (Снижение массы бета-клеток при диабете 2 типа)
    # Если HbA1c > 6.5%, считаем, что часть бета-клеток погибла
    if passport.HbA1c_percent > 6.5:
        params.beta_mass = 0.4 # Значительное снижение (осталось 40%)
        
    return params
