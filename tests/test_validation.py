import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import SimulationEngine
from core.blood_pool import BloodPool
from agents.gis_super_agent import GISSuperAgent
from agents.pancreas import PancreasAgent
from agents.liver import LiverAgent
from agents.muscle import MuscleAgent
from agents.brain import BrainAgent
from agents.gut import GutAgent
from agents.adipose import AdiposeAgent
from agents.kidney import KidneyAgent
from models.passport import PatientPassport_GIS
from models.messages import MealIntakeMsg

def setup_gis(passport=None):
    engine = SimulationEngine(step_size_min=1.0)
    blood = BloodPool()
    msg_bus = engine.message_bus
    
    gis = GISSuperAgent(blood, msg_bus)
    gis.add_subagent(GutAgent(blood, msg_bus))
    gis.add_subagent(PancreasAgent(blood, msg_bus))
    gis.add_subagent(LiverAgent(blood, msg_bus))
    gis.add_subagent(MuscleAgent(blood, msg_bus))
    gis.add_subagent(BrainAgent(blood, msg_bus))
    gis.add_subagent(AdiposeAgent(blood, msg_bus))
    gis.add_subagent(KidneyAgent(blood, msg_bus))
    
    if passport:
        gis.calibrate(passport)
        
    engine.set_blood_pool(blood)
    engine.add_agent(gis)
    return engine, blood, msg_bus

class TestGISValidation(unittest.TestCase):
    
    def test_healthy_ogtt(self):
        passport = PatientPassport_GIS(
            age=30, sex='M', weight_kg=70, height_cm=175,
            fasting_glucose_mmol_L=5.0, fasting_insulin_pmol_L=60.0, HbA1c_percent=5.0
        )
        engine, blood, msg_bus = setup_gis(passport)
        
        # Fasting 60 mins
        engine.run(60)
        self.assertAlmostEqual(blood.glucose, 5.0, delta=1.5, msg="Fasting baseline unstable")
        
        # Eat 75g
        msg_bus.publish(MealIntakeMsg(carbs_g=75.0))
        
        # Run to peak
        peak_g = 0
        for _ in range(45):
            engine.run(1.0)
            if blood.glucose > peak_g:
                peak_g = blood.glucose
                
        self.assertLess(peak_g, 10.0, "Healthy peak too high (> 10.0)")
        
        # Run to 120 mins
        engine.run(75)
        self.assertLess(blood.glucose, 7.8, "Did not return to normal (< 7.8) after 2h")

    def test_t2d_ogtt(self):
        passport = PatientPassport_GIS(
            age=55, sex='M', weight_kg=100, height_cm=170,
            fasting_glucose_mmol_L=7.5, fasting_insulin_pmol_L=150.0, HbA1c_percent=7.2
        )
        engine, blood, msg_bus = setup_gis(passport)
        
        engine.run(60)
        
        msg_bus.publish(MealIntakeMsg(carbs_g=75.0))
        
        peak_g = 0
        for _ in range(45):
            engine.run(1.0)
            if blood.glucose > peak_g:
                peak_g = blood.glucose
                
        self.assertGreater(peak_g, 10.0, "T2D peak too low")
        
        engine.run(75)
        self.assertGreater(blood.glucose, 7.8, "T2D returned to normal, which is incorrect")

if __name__ == '__main__':
    unittest.main()
