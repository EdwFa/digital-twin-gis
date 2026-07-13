from dataclasses import dataclass
from typing import Literal

@dataclass
class PatientPassport_GIS:
    """Demographic and clinical data for the digital twin."""
    age: int
    sex: Literal['M', 'F']
    weight_kg: float
    height_cm: float
    
    fasting_glucose_mmol_L: float     
    fasting_insulin_pmol_L: float     
    HbA1c_percent: float              
    
    family_history_diabetes: bool = False
    physical_activity_MET_h_week: float = 10.0
