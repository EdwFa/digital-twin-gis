import sys
import os
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import SimulationEngine
from core.blood_pool import BloodPool
from agents.cardiovascular import CardiovascularAgent
from core.orchestrator import SimulationOrchestrator
from models.events import Event

def run():
    print("=== Демонстрация Фазы 3: Сердечно-сосудистая система (CVS) ===")
    
    engine = SimulationEngine(step_size_min=1.0)
    blood = BloodPool()
    engine.set_blood_pool(blood)
    
    cvs_agent = CardiovascularAgent(blood, engine.message_bus)
    engine.add_agent(cvs_agent)
    
    orchestrator = SimulationOrchestrator(engine)
    
    history_time = []
    history_hr = []
    history_map = []
    history_sv = []
    
    # Чтобы собрать графики каждую минуту, пропатчим tick
    original_tick = engine.tick
    def hooked_tick():
        original_tick()
        history_time.append(engine.time_min)
        history_hr.append(blood.hemodynamics["heart_rate"])
        history_map.append(blood.hemodynamics["mean_arterial_pressure"])
        history_sv.append(blood.hemodynamics["stroke_volume"])
    engine.tick = hooked_tick
    
    print("1. Базовая симуляция (в норме) - 60 минут...")
    orchestrator.run_until(60.0)
    
    print(f"Пульс: {blood.hemodynamics['heart_rate']:.1f}, Давление: {blood.hemodynamics['mean_arterial_pressure']:.1f}")
    
    print("\n2. [СОБЫТИЕ] Массивное кровотечение (Hemorrhage)!")
    def trigger_hemorrhage():
        cvs_agent.pathologies["hemorrhage"] = True
    
    bleed_event = Event(time_minutes=60.0, description="Начало кровотечения")
    bleed_event.action = trigger_hemorrhage
    orchestrator.schedule_event(bleed_event)
    
    print("Симуляция шока - 60 минут...")
    orchestrator.run_until(120.0)
    print(f"Пульс: {blood.hemodynamics['heart_rate']:.1f}, Давление: {blood.hemodynamics['mean_arterial_pressure']:.1f}, УО: {blood.hemodynamics['stroke_volume']:.1f}")
    
    print("\n3. [СОБЫТИЕ] Остановка кровотечения (реанимация). Возврат ОЦК.")
    def stop_hemorrhage():
        cvs_agent.pathologies["hemorrhage"] = False
        # Вливаем физраствор/кровь, восстанавливаем ударный объем
        blood.hemodynamics["stroke_volume"] = 70.0
        
    heal_event = Event(time_minutes=120.0, description="Реанимация (инфузия)")
    heal_event.action = stop_hemorrhage
    orchestrator.schedule_event(heal_event)
    
    print("Симуляция восстановления - 60 минут...")
    orchestrator.run_until(180.0)
    print(f"Пульс: {blood.hemodynamics['heart_rate']:.1f}, Давление: {blood.hemodynamics['mean_arterial_pressure']:.1f}")
    
    print("\nСимуляция завершена. Создание графиков...")
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    
    ax1.plot(history_time, history_map, color='blue', label='MAP (Давление)')
    ax1.axhline(90, color='gray', linestyle='--', alpha=0.5)
    ax1.set_ylabel('mmHg')
    ax1.set_title('Среднее артериальное давление (MAP) при кровотечении')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    ax2.plot(history_time, history_hr, color='red', label='Heart Rate (Пульс)')
    ax2.plot(history_time, history_sv, color='green', label='Stroke Volume (УО)')
    ax2.set_xlabel('Время (минуты)')
    ax2.set_ylabel('Value')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('cvs_shock_result.png')
    print("Графики сохранены в 'cvs_shock_result.png'")

if __name__ == "__main__":
    run()
