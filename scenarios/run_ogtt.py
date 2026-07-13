import sys
import os
import matplotlib.pyplot as plt

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import SimulationEngine
from core.blood_pool import BloodPool
from core.message_bus import MessageBus
from models.messages import MealIntakeMsg
from models.passport import PatientPassport_GIS
from agents.gis_super_agent import GISSuperAgent
from agents.pancreas import PancreasAgent
from agents.liver import LiverAgent
from agents.muscle import MuscleAgent
from agents.brain import BrainAgent
from agents.gut import GutAgent
from agents.adipose import AdiposeAgent
from agents.kidney import KidneyAgent
from agents.slow_adaptation import SlowAdaptationAgent

def run():
    print("Initializing Digital Twin (Glucose-Insulin MVP)...")
    
    passport = PatientPassport_GIS(
        age=30, sex='M', weight_kg=75, height_cm=180,
        fasting_glucose_mmol_L=5.0, fasting_insulin_pmol_L=60.0, HbA1c_percent=5.0
    )
    
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
    gis.add_subagent(SlowAdaptationAgent(blood, msg_bus))
    
    gis.calibrate(passport)
    
    engine.set_blood_pool(blood)
    engine.add_agent(gis)
    
    history_time = []
    history_g = []
    history_i = []

    def record_state():
        history_time.append(engine.time_min)
        history_g.append(blood.glucose)
        history_i.append(blood.insulin)

    print("Simulating fasting baseline (60 min)...")
    for _ in range(60):
        engine.run(1.0)
        record_state()
        
    print(f"Time: {engine.time_min} min | Glucose: {blood.glucose:.2f} | Insulin: {blood.insulin:.2f}")
    
    print("--- Administering 75g Glucose (OGTT) ---")
    msg_bus.publish(MealIntakeMsg(carbs_g=75.0))
    
    for _ in range(180):
        engine.run(1.0)
        record_state()
    
    print(f"Time: {engine.time_min} min | Glucose: {blood.glucose:.2f} | Insulin: {blood.insulin:.2f}")
    print("Simulation complete. Generating plot...")

    fig, ax1 = plt.subplots(figsize=(10, 5))

    color = 'tab:red'
    ax1.set_xlabel('Time (min)')
    ax1.set_ylabel('Glucose (mmol/L)', color=color)
    ax1.plot(history_time, history_g, color=color, label='Glucose')
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  
    color = 'tab:blue'
    ax2.set_ylabel('Insulin (pmol/L)', color=color)  
    ax2.plot(history_time, history_i, color=color, label='Insulin')
    ax2.tick_params(axis='y', labelcolor=color)

    fig.tight_layout()  
    plt.title("Glucose-Insulin Simulation (MVP)")
    plt.grid(True, alpha=0.3)
    
    plt.savefig('ogtt_result.png')
    print("Plot saved to 'ogtt_result.png'")

if __name__ == "__main__":
    run()
