from .base import BaseAgent

class AdiposeAgent(BaseAgent):
    """
    Агент Жировой ткани (Adipose Agent).
    Управляет процессами Липолиза (выделение жирных кислот) и Липогенеза (запасание жира).
    Также выполняет эндокринную функцию (Лептин, Адипонектин).
    """
    def __init__(self, blood_pool, message_bus):
        super().__init__("Adipose", blood_pool, message_bus)
        self.adipose_SI = 1.0 # Чувствительность жировой ткани к инсулину (1.0 = норма)
        self.f_adipose = 0.0001 # Константа захвата глюкозы для конвертации в жир
        
        # Параметры липолиза
        self.basal_lipolysis = 0.04 # Базовая скорость выделения свободных жирных кислот (FFA) в кровь (ммоль/Л/мин)
        self.k_ffa_clearance = 0.1 # Скорость потребления FFA другими тканями (мышцами, печенью) /мин
        
        # Эндокринные маркеры
        self.leptin_level = 10.0 # Лептин (сигнал сытости для мозга)
        self.adiponectin_level = 15.0 # Адипонектин (маркер инсулиночувствительности)

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        from models.messages import AdaptationMsg
        
        # Обновление чувствительности к инсулину при развитии липотоксичности
        for msg in messages:
            if isinstance(msg, AdaptationMsg):
                self.adipose_SI = msg.insulin_sensitivity_multiplier

        g = max(0.1, blood_state["glucose"])
        i = max(0.1, blood_state["insulin"])
        glu = max(0.1, blood_state["glucagon"])
        ffa = max(0.0, blood_state["ffa"])
        
        # 1. Захват Глюкозы (Липогенез) - превращение излишков сахара в жир
        uptake = self.f_adipose * self.adipose_SI * i * g
        self.blood_pool.add_glucose_delta(-uptake)
        
        # 2. Липолиз (Высвобождение FFA в кровь)
        # Строго (квадратично) подавляется даже малыми дозами инсулина, стимулируется глюкагоном
        i_factor = max(0.1, (i / 60.0) * self.adipose_SI)
        glu_factor = glu / 50.0
        
        lipolysis_rate = self.basal_lipolysis * (glu_factor / (i_factor**2))
        
        # Ткани (мышцы/печень) постоянно потребляют FFA для базовой энергии
        ffa_clearance = self.k_ffa_clearance * ffa
        
        self.blood_pool.add_ffa_delta(lipolysis_rate - ffa_clearance)
        
        # 3. Адипокины (Эндокринная функция)
        # Лептин растет пропорционально инсулиновому сигналу (индикатор наполненности энергией)
        self.leptin_level = 10.0 * i_factor
        # Адипонектин падает при инсулинорезистентности
        self.adiponectin_level = 15.0 * self.adipose_SI
