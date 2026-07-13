from .base import BaseAgent

class MuscleAgent(BaseAgent):
    """
    Агент Скелетных Мышц (Muscle Agent).
    Главный потребитель глюкозы в организме. Захват глюкозы строго зависит от инсулина (через GLUT4).
    Имеет гигантский пул гликогена, который не может высвобождать глюкозу обратно в кровь 
    (мышцы сжигают гликоген только для собственных нужд).
    """
    def __init__(self, blood_pool, message_bus):
        super().__init__("Muscle", blood_pool, message_bus)
        self.muscle_SI = 1.0 # Чувствительность мышц к инсулину (1.0 = норма)
        self.f_muscle = 0.0003 # Константа захвата
        
        # Пул гликогена в мышцах (~400г).
        # В пересчете на концентрацию в 16Л крови: 400г = 2222 ммоль -> 2222/16 ≈ 140.0 ммоль/Л
        self.max_glycogen = 140.0
        self.glycogen_pool = 100.0 # Изначально заполнено на ~70%
        
        # Базовая скорость сжигания гликогена мышцами для поддержания тонуса
        self.basal_burn_rate = 0.09 # ммоль/Л/мин 

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        from models.messages import AdaptationMsg
        
        # Обработка системной инсулинорезистентности
        for msg in messages:
            if isinstance(msg, AdaptationMsg):
                self.muscle_SI = msg.insulin_sensitivity_multiplier

        g = blood_state["glucose"]
        i = blood_state["insulin"]
        
        # Фактор емкости (Capacity factor): 
        # Если мышцы не тренируются и бак гликогена заполняется до 140.0, 
        # захват падает до 0 (возникает физиологическая мышечная инсулинорезистентность)
        capacity_factor = max(0.0, 1.0 - (self.glycogen_pool / self.max_glycogen)**4)
        
        # Инсулин-зависимый захват глюкозы (Транслокация GLUT4)
        uptake = self.f_muscle * self.muscle_SI * i * g * capacity_factor
        
        # Внутреннее сжигание гликогена (не может сжечь больше, чем есть в пуле)
        burn = min(self.basal_burn_rate, self.glycogen_pool / step_size)
        
        # Обновление локального пула
        self.glycogen_pool += (uptake - burn) * step_size
        self.glycogen_pool = max(0.0, min(self.max_glycogen, self.glycogen_pool))
        
        # Захват уменьшает количество глюкозы в системном кровотоке
        self.blood_pool.add_glucose_delta(-uptake)
