class BloodPool:
    """
    Класс BloodPool (Кровяной Пул).
    Выступает в качестве центральной среды (плазмы крови), в которую органы выделяют 
    или из которой поглощают метаболиты, гормоны и лекарства.
    Поддерживает динамический реестр веществ (PBPK-архитектура).
    """
    def __init__(self):
        # Универсальный реестр концентраций веществ
        self.concentrations = {
            "glucose": 5.0,    # Глюкоза (ммоль/Л)
            "insulin": 60.0,   # Инсулин (пмоль/Л)
            "glucagon": 50.0,  # Глюкагон (пг/мл)
            "incretin": 10.0,  # Инкретин / GLP-1 (пмоль/Л)
            "ffa": 0.4         # Свободные жирные кислоты / FFA (ммоль/Л)
        }
        
        # Буферы изменений (дельта) для шага численного интегрирования (Euler step)
        self.deltas = {
            "glucose": 0.0,
            "insulin": 0.0,
            "glucagon": 0.0,
            "incretin": 0.0,
            "ffa": 0.0
        }
        
        # ==========================================
        # ГЕМОДИНАМИКА (Фаза 3 - CVS)
        # ==========================================
        self.hemodynamics = {
            "heart_rate": 70.0,            # Пульс (уд/мин)
            "stroke_volume": 70.0,         # Ударный объем (мл)
            "cardiac_output": 4.9,         # Сердечный выброс (Л/мин) = HR * SV / 1000
            "mean_arterial_pressure": 90.0,# Среднее артериальное давление (MAP, мм рт. ст.)
            "total_peripheral_resistance": 90.0 / 4.9 # TPR = MAP / CO
        }
        
        # Распределение кровотока (Фракции от Cardiac Output)
        self.blood_flow_fractions = {
            "liver": 0.25,     # 25% печени
            "kidney": 0.20,    # 20% почкам
            "brain": 0.15,     # 15% мозгу
            "muscle": 0.20,    # 20% мышцам
            "adipose": 0.05,   # 5% жиру
            "gut": 0.10,       # 10% кишечнику
            "other": 0.05      # Остальное
        }

    # ==========================================
    # PBPK ИНТЕРФЕЙС (Фаза 3)
    # ==========================================
    def add_delta(self, substance: str, amount: float):
        """Добавить изменение концентрации произвольного вещества."""
        if substance not in self.deltas:
            self.deltas[substance] = 0.0
            if substance not in self.concentrations:
                self.concentrations[substance] = 0.0
        self.deltas[substance] += amount

    def get_concentration(self, substance: str) -> float:
        """Получить текущую концентрацию произвольного вещества."""
        return self.concentrations.get(substance, 0.0)

    # ==========================================
    # ОБРАТНАЯ СОВМЕСТИМОСТЬ (Для Фазы 2 ГИС)
    # ==========================================
    @property
    def glucose(self): return self.get_concentration("glucose")
    
    @glucose.setter
    def glucose(self, val): self.concentrations["glucose"] = val
    
    @property
    def insulin(self): return self.get_concentration("insulin")
    
    @insulin.setter
    def insulin(self, val): self.concentrations["insulin"] = val
    
    @property
    def glucagon(self): return self.get_concentration("glucagon")
    
    @glucagon.setter
    def glucagon(self, val): self.concentrations["glucagon"] = val
    
    @property
    def incretin(self): return self.get_concentration("incretin")
    
    @incretin.setter
    def incretin(self, val): self.concentrations["incretin"] = val
    
    @property
    def ffa(self): return self.get_concentration("ffa")
    
    @ffa.setter
    def ffa(self, val): self.concentrations["ffa"] = val

    def add_glucose_delta(self, amount): self.add_delta("glucose", amount)
    def add_insulin_delta(self, amount): self.add_delta("insulin", amount)
    def add_glucagon_delta(self, amount): self.add_delta("glucagon", amount)
    def add_incretin_delta(self, amount): self.add_delta("incretin", amount)
    def add_ffa_delta(self, amount): self.add_delta("ffa", amount)
        
    def get_state(self):
        """Получить текущее состояние всех биомаркеров и гемодинамики."""
        state = self.concentrations.copy()
        state.update(self.hemodynamics)
        return state
        
    def get_regional_blood_flow(self, organ_name: str) -> float:
        """Получить локальный кровоток органа (Л/мин) на основе Cardiac Output и фракции органа."""
        fraction = self.blood_flow_fractions.get(organ_name, 0.0)
        return self.hemodynamics["cardiac_output"] * fraction
        
    def resolve_step(self, step_size_min):
        """
        Применить все накопленные изменения (дельты) за текущий шаг времени.
        Используется простейший метод Эйлера для численного интегрирования ОДУ.
        Значения не могут опускаться ниже нуля (max(0.0, ...)).
        """
        for substance, delta in self.deltas.items():
            current = self.concentrations.get(substance, 0.0)
            self.concentrations[substance] = max(0.0, current + delta * step_size_min)
            # Сброс буфера после применения
            self.deltas[substance] = 0.0
