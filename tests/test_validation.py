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
                
        self.assertLess(peak_g, 13.0, "Healthy peak too high (> 13.0)")
        
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
                
        self.assertGreater(peak_g, 9.0, "T2D peak too low")
        
        engine.run(75)
        self.assertGreater(blood.glucose, 7.8, "T2D returned to normal, which is incorrect")

    def test_incretin_effect(self):
        # 1. Oral test
        engine_oral, blood_oral, msg_bus_oral = setup_gis()
        msg_bus_oral.publish(MealIntakeMsg(carbs_g=50.0))
        
        peak_insulin_oral = 0
        for _ in range(60):
            engine_oral.run(1.0)
            if blood_oral.insulin > peak_insulin_oral:
                peak_insulin_oral = blood_oral.insulin
                
        # 2. IV test (inject 50g directly into blood over 10 mins)
        engine_iv, blood_iv, msg_bus_iv = setup_gis()
        peak_insulin_iv = 0
        
        # 50g = ~277 mmol. Inject 27.7 mmol per min for 10 mins
        for i in range(60):
            if i < 10:
                blood_iv.add_glucose_delta(27.7 / 16.0)
            engine_iv.run(1.0)
            if blood_iv.insulin > peak_insulin_iv:
                peak_insulin_iv = blood_iv.insulin
                
        self.assertGreater(peak_insulin_oral, peak_insulin_iv, "Incretin effect missing! Oral should produce more insulin than IV.")

    def test_glycogen_depletion(self):
        engine, blood, msg_bus = setup_gis()
        liver = next(a for a in engine.agents[0].subagents if a.name == "Liver")
        
        # Fast for 48 hours (2880 mins)
        engine.run(2880)
        
        self.assertLess(liver.glycogen_pool, 5.0, "Glycogen should be severely depleted after 48h fast")
        self.assertGreater(blood.glucose, 2.5, "Patient died from hypoglycemia! Gluconeogenesis failed.")

if __name__ == '__main__':
    unittest.main()
