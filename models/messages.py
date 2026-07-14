from dataclasses import dataclass
from typing import Any

@dataclass
class MealIntakeMsg:
    """
    Сообщение о приеме пищи (Входящее из внешнего мира/Оркестратора).
    Служит триггером для GutAgent начать процесс пищеварения.
    """
    carbs_g: float           # Углеводы (граммы)
    fiber_g: float = 0.0     # Клетчатка (граммы) - замедляет всасывание
    gi_index: float = 70.0   # Гликемический индекс
    protein_g: float = 0.0   # Белки (граммы)
    fat_g: float = 0.0       # Жиры (граммы)
    meal_duration_min: float = 20.0 # Длительность приема пищи

@dataclass
class HormoneSecretionMsg:
    """Внутреннее сообщение от Поджелудочной железы (пока не используется напрямую, заменено на delta в BloodPool)."""
    substance: str
    secretion_rate_pmol_min: float
    phase: str = "basal"
    
@dataclass
class GISStateMsg:
    """
    Исходящее сообщение о текущем состоянии метаболической системы (GIS).
    Используется для отправки данных Оркестратору (Уровень 0) или другим системам (Уровень 1).
    """
    glucose_mmol_L: float
    insulin_pmol_L: float
    glucagon_pmol_L: float
    incretin_pmol_L: float
    ffa_mmol_L: float

@dataclass
class AdaptationMsg:
    """
    Сообщение долгосрочной адаптации от SlowAdaptationAgent.
    Переносит модификаторы, вызванные старением или хроническими болезнями (например, диабетом).
    """
    beta_mass_multiplier: float             # Множитель массы бета-клеток (падает при глюкотоксичности)
    insulin_sensitivity_multiplier: float   # Множитель чувствительности к инсулину (падает при липотоксичности)

@dataclass
class DrugAdministrationMsg:
    """Сообщение о приеме лекарства (Фармакокинетика)."""
    substance: str
    dose_mg: float
    route: str = "oral"
    formulation: str = "tablet"
    
@dataclass
class PortalVeinInflowMsg:
    """Сообщение о поступлении веществ из воротной вены в печень."""
    blood_flow_L_min: float
    substances_mmol_L: dict  # {"glucose": 6.5, "ethanol": 0.0, "drug_X": ...}

