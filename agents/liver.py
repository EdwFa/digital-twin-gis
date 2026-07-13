import math
from .base import BaseAgent

class LiverAgent(BaseAgent):
    """
    Агент Печени (Liver Agent).
    Главный буфер глюкозы в организме. Моделирует два процесса выработки глюкозы (EGP):
    Глюконеогенез (из аминокислот/лактата) и Гликогенолиз (расщепление гликогена).
    Также моделирует захват глюкозы (Гликогенез) для пополнения физического пула гликогена.
    """
    def __init__(self, blood_pool, message_bus):
        super().__init__("Liver", blood_pool, message_bus)
        self.egp_fasting = 0.179 # Базовая эндогенная продукция глюкозы (ммоль/Л/мин)
        self.liver_SI = 1.0 # Чувствительность печени к инсулину (1.0 = норма)
        
        # Пул гликогена в печени (~100г). 
        # В пересчете на концентрацию в 16Л крови: 100г = 555 ммоль -> 555/16 ≈ 35.0 ммоль/Л
        self.max_glycogen = 35.0
        self.glycogen_pool = 25.0 # Изначально заполнено на ~70% (состояние после ночного сна)
        
        self.k_uptake = 0.0001 # Константа скорости захвата глюкозы печенью

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        from models.messages import AdaptationMsg
        
        # Обработка сигналов о системной инсулинорезистентности (липотоксичность)
        for msg in messages:
            if isinstance(msg, AdaptationMsg):
                self.liver_SI = msg.insulin_sensitivity_multiplier

        g = max(0.1, blood_state["glucose"])
        i = max(0.1, blood_state["insulin"])
        glu = max(0.1, blood_state["glucagon"])
        
        # Разделение базовой выработки: 30% Глюконеогенез (неистощимый), 70% Гликогенолиз
        GNG_basal = 0.3 * self.egp_fasting
        GGL_basal = 0.7 * self.egp_fasting
        
        # Гормональный драйв (Hormonal Drive) - отношение Глюкагона к Инсулину
        # Если глюкагон высок, а инсулин низок - печень активно выбрасывает сахар
        i_factor = max(0.1, (i / 60.0) * self.liver_SI)
        glu_factor = glu / 50.0
        hormonal_drive = glu_factor / i_factor
        
        # 1. Глюконеогенез (GNG) - синтез глюкозы de-novo
        GNG = GNG_basal * hormonal_drive
        
        # 2. Гликогенолиз (GGL) - расщепление запасов гликогена
        GGL = GGL_basal * hormonal_drive
        # Если бак гликогена пустеет (< 5.0), гликогенолиз линейно затухает до нуля
        if self.glycogen_pool < 5.0:
            GGL *= max(0.0, self.glycogen_pool / 5.0) 
            
        # 3. Захват глюкозы (Гликогенез)
        # Фактор емкости: захват резко замедляется (стремится к 0), когда бак заполнен (100%)
        capacity_factor = max(0.0, 1.0 - (self.glycogen_pool / self.max_glycogen)**4)
        uptake = self.k_uptake * g * i * self.liver_SI * capacity_factor
        
        # Обновление локального физического пула гликогена
        self.glycogen_pool += (uptake - GGL) * step_size
        self.glycogen_pool = max(0.0, min(self.max_glycogen, self.glycogen_pool))
        
        # Отправка чистого потока глюкозы в кровь (Продукция - Захват)
        net_glucose_flux = GNG + GGL - uptake
        self.blood_pool.add_glucose_delta(net_glucose_flux)
