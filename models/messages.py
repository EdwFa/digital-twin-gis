from dataclasses import dataclass
from typing import Any

@dataclass
class MealIntakeMsg:
    """Incoming message from Orchestrator simulating a meal."""
    carbs_g: float
    fiber_g: float = 0.0
    gi_index: float = 70.0
    protein_g: float = 0.0
    fat_g: float = 0.0
    meal_duration_min: float = 20.0

@dataclass
class HormoneSecretionMsg:
    """Internal message from Pancreas to Blood Pool."""
    substance: str
    secretion_rate_pmol_min: float
    phase: str = "basal"
    
@dataclass
class GISStateMsg:
    """Outgoing message publishing the state of the GIS."""
    glucose_mmol_L: float
    insulin_pmol_L: float
    glucagon_pmol_L: float
    incretin_pmol_L: float
    ffa_mmol_L: float
    # We will expand this as we add more agents

@dataclass
class AdaptationMsg:
    beta_mass_multiplier: float
    insulin_sensitivity_multiplier: float
