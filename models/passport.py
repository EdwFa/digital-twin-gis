from dataclasses import dataclass
from typing import Literal

@dataclass
class PatientPassport_GIS:
    """
    Паспорт Пациента (Patient Passport).
    Содержит демографические и базовые клинические данные цифрового двойника.
    Эти данные используются модулем `calibration.py` для генерации индивидуальных параметров ODE.
    """
    age: int                     # Возраст (годы)
    sex: Literal['M', 'F']       # Пол (М/Ж)
    weight_kg: float             # Вес (кг)
    height_cm: float             # Рост (см)
    
    # Лабораторные маркеры
    fasting_glucose_mmol_L: float     # Тощаковая глюкоза
    fasting_insulin_pmol_L: float     # Тощаковый инсулин
    HbA1c_percent: float              # Гликированный гемоглобин (маркер хронического сахара)
    
    # Образ жизни и генетика
    family_history_diabetes: bool = False       # Семейная история диабета (генетический риск)
    physical_activity_MET_h_week: float = 10.0  # Уровень физической активности (влияет на чувствительность мышц)
