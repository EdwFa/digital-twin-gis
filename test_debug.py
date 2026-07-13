import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tests.test_validation import setup_gis
from models.passport import PatientPassport_GIS
from models.messages import MealIntakeMsg

passport = PatientPassport_GIS(
    age=30, sex='M', weight_kg=70, height_cm=175,
    fasting_glucose_mmol_L=5.0, fasting_insulin_pmol_L=60.0, HbA1c_percent=5.0
)
engine, blood, msg_bus = setup_gis(passport)

engine.run(60)
print(f"Fasting 60: G={blood.glucose:.1f}, I={blood.insulin:.1f}, Glu={blood.glucagon:.1f}")

msg_bus.publish(MealIntakeMsg(carbs_g=75.0))

for t in range(45):
    engine.run(1.0)
    print(f"T={t}: G={blood.glucose:.1f}, I={blood.insulin:.1f}, Glu={blood.glucagon:.1f}, Inc={blood.incretin:.1f}")
