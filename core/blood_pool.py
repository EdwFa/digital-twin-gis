class BloodPool:
    """
    Класс BloodPool (Кровяной Пул).
    Выступает в качестве центральной среды (плазмы крови), в которую органы выделяют 
    или из которой поглощают метаболиты и гормоны.
    """
    def __init__(self):
        # Базовые (тощаковые) концентрации веществ в крови
        self.glucose = 5.0  # Глюкоза (ммоль/Л)
        self.insulin = 60.0 # Инсулин (пмоль/Л)
        self.glucagon = 50.0 # Глюкагон (пг/мл)
        self.incretin = 10.0 # Инкретин / GLP-1 (пмоль/Л)
        self.ffa = 0.4 # Свободные жирные кислоты / FFA (ммоль/Л)
        
        # Буферы изменений (дельта) для шага численного интегрирования (Euler step)
        # Органы не меняют концентрации напрямую, они добавляют изменения в эти буферы
        self._g_delta = 0.0
        self._i_delta = 0.0
        self._glu_delta = 0.0
        self._inc_delta = 0.0
        self._ffa_delta = 0.0
        
    def add_glucose_delta(self, amount):
        """Добавить изменение концентрации глюкозы (ммоль/Л/мин)."""
        self._g_delta += amount
        
    def add_insulin_delta(self, amount):
        """Добавить изменение концентрации инсулина (пмоль/Л/мин)."""
        self._i_delta += amount
        
    def add_glucagon_delta(self, amount):
        """Добавить изменение концентрации глюкагона (пг/мл/мин)."""
        self._glu_delta += amount

    def add_incretin_delta(self, amount):
        """Добавить изменение концентрации инкретинов (пмоль/Л/мин)."""
        self._inc_delta += amount

    def add_ffa_delta(self, amount):
        """Добавить изменение концентрации свободных жирных кислот (ммоль/Л/мин)."""
        self._ffa_delta += amount
        
    def get_state(self):
        """Получить текущее состояние всех биомаркеров крови (read-only снимок)."""
        return {
            "glucose": self.glucose,
            "insulin": self.insulin,
            "glucagon": self.glucagon,
            "incretin": self.incretin,
            "ffa": self.ffa
        }
        
    def resolve_step(self, step_size_min):
        """
        Применить все накопленные изменения (дельты) за текущий шаг времени.
        Используется простейший метод Эйлера для численного интегрирования ОДУ.
        Значения не могут опускаться ниже нуля (max(0.0, ...)).
        """
        # Применение дельт (интеграция)
        self.glucose = max(0.0, self.glucose + self._g_delta * step_size_min)
        self.insulin = max(0.0, self.insulin + self._i_delta * step_size_min)
        self.glucagon = max(0.0, self.glucagon + self._glu_delta * step_size_min)
        self.incretin = max(0.0, self.incretin + self._inc_delta * step_size_min)
        self.ffa = max(0.0, self.ffa + self._ffa_delta * step_size_min)
        
        # Сброс буферов после применения для следующего шага
        self._g_delta = 0.0
        self._i_delta = 0.0
        self._glu_delta = 0.0
        self._inc_delta = 0.0
        self._ffa_delta = 0.0
