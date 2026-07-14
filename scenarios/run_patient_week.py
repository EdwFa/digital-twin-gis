import sys
import os

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import SimulationEngine
from core.blood_pool import BloodPool
from core.message_bus import MessageBus
from models.passport import PatientPassport_GIS
from agents.gis_super_agent import GISSuperAgent
from agents.pancreas import PancreasAgent
from agents.liver_pbpk import LiverPBPKSuperAgent
from agents.muscle import MuscleAgent
from agents.brain import BrainAgent
from agents.gut import GutAgent
from agents.adipose import AdiposeAgent
from agents.kidney import KidneyAgent
from agents.slow_adaptation import SlowAdaptationAgent
from core.orchestrator import SimulationOrchestrator
from models.events import MealEvent, DrugEvent, SleepEvent
from agents.ai_clinical_assistant import AIClinicalAssistant

def run():
    print("=== Инициализация Цифрового Двойника (Фаза 4: AI-Оркестратор) ===")
    
    # 1. Ядро
    engine = SimulationEngine(step_size_min=1.0)
    blood = BloodPool()
    msg_bus = engine.message_bus
    
    passport = PatientPassport_GIS(
        age=45, sex='M', weight_kg=85, height_cm=175,
        fasting_glucose_mmol_L=5.5, fasting_insulin_pmol_L=80.0, HbA1c_percent=6.0
    )
    
    # 2. Агенты (Полный стек ГИС + Печень L5)
    gis = GISSuperAgent(blood, msg_bus)
    gis.add_subagent(GutAgent(blood, msg_bus))
    gis.add_subagent(PancreasAgent(blood, msg_bus))
    
    liver_agent = LiverPBPKSuperAgent(blood, msg_bus)
    # Задаем пациенту тяжелую патологию (Цирроз Child-Pugh C)
    liver_agent.pathologies["cirrhosis_child_pugh"] = "C"
    gis.add_subagent(liver_agent)
    
    gis.add_subagent(MuscleAgent(blood, msg_bus))
    gis.add_subagent(BrainAgent(blood, msg_bus))
    gis.add_subagent(AdiposeAgent(blood, msg_bus))
    gis.add_subagent(KidneyAgent(blood, msg_bus))
    gis.add_subagent(SlowAdaptationAgent(blood, msg_bus))
    
    gis.calibrate(passport)
    
    engine.set_blood_pool(blood)
    engine.add_agent(gis)
    
    # 3. Оркестратор и AI-Аналитик
    orchestrator = SimulationOrchestrator(engine)
    ai_assistant = AIClinicalAssistant(orchestrator)
    
    # 4. Планируем Жизнь (Timeline) на 2 суток (48 часов = 2880 минут)
    
    # --- ДЕНЬ 1 ---
    orchestrator.schedule_event(MealEvent(time_minutes=8*60, description="Завтрак (60г углеводов)", carbs_g=60.0))
    orchestrator.schedule_event(DrugEvent(time_minutes=8.5*60, description="Прием Парацетамола 500мг", substance="paracetamol", dose_mg=500.0))
    orchestrator.schedule_event(MealEvent(time_minutes=14*60, description="Обед (80г углеводов)", carbs_g=80.0))
    orchestrator.schedule_event(MealEvent(time_minutes=20*60, description="Ужин (50г углеводов)", carbs_g=50.0))
    
    orchestrator.schedule_event(SleepEvent(time_minutes=23*60, description="Отход ко сну", duration_minutes=8*60))
    
    # --- ДЕНЬ 2 ---
    orchestrator.schedule_event(MealEvent(time_minutes=32*60, description="Завтрак День 2 (60г углеводов)", carbs_g=60.0))
    orchestrator.schedule_event(DrugEvent(time_minutes=32.5*60, description="Прием Парацетамола 500мг", substance="paracetamol", dose_mg=500.0))
    orchestrator.schedule_event(MealEvent(time_minutes=38*60, description="Обед День 2 (80г углеводов)", carbs_g=80.0))
    
    print("Запуск симуляции на 48 часов...")
    orchestrator.run_until(48 * 60)
    print("Симуляция завершена.\n")
    
    # 5. Вызов AI-Ассистента
    print(ai_assistant.generate_report())

if __name__ == "__main__":
    run()
