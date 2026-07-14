from dataclasses import dataclass
from typing import Optional

@dataclass
class Event:
    """Базовый класс события на временной шкале (Timeline)"""
    time_minutes: float
    description: str

@dataclass
class MealEvent(Event):
    """Событие: Прием пищи"""
    carbs_g: float

@dataclass
class DrugEvent(Event):
    """Событие: Прием лекарства"""
    substance: str
    dose_mg: float
    is_oral: bool = True # По умолчанию перорально (в Portal Vein), иначе В/В

@dataclass
class SleepEvent(Event):
    """Событие: Сон (снижает базальный метаболизм, повышает чувствительность к инсулину)"""
    duration_minutes: float
