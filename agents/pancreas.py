from .base import BaseAgent
from models.messages import HormoneSecretionMsg

class PancreasAgent(BaseAgent):
    """
    Агент Поджелудочной железы (Pancreas Agent).
    Моделирует эндокринную функцию: Альфа-клетки (глюкагон), Бета-клетки (инсулин) и Дельта-клетки (соматостатин).
    Использует сложную 2-компонентную модель пулов инсулина.
    """
    def __init__(self, blood_pool, message_bus):
        super().__init__("Pancreas", blood_pool, message_bus)
        
        # --- Параметры Бета-клеток (Инсулин) ---
        self.beta_mass = 1.0      # Относительная масса бета-клеток (1.0 = норма)
        self.M1 = 100.0           # Readily Releasable Pool (RRP) - пул быстрого реагирования (пмоль)
        self.M2 = 1000.0          # Reserve Pool - гранулярный резервный пул (пмоль)
        self.k_release_max = 0.072 # Максимальная скорость релиза из M1 (функция Хилла)
        self.k_transfer = 0.00072  # Базовая скорость перемещения гранул из M2 в M1
        self.basal_synthesis = 3.6 # Базовый синтез нового инсулина в M2
        self.alpha_hill = 25.0     # Константа полунасыщения для функции Хилла (зависимость от глюкозы)
        self.k_I_clearance = 0.06  # Клиренс (распад) инсулина в крови (период полураспада ~10 мин)
        
        # --- Параметры Альфа-клеток (Глюкагон) ---
        self.k_Glu_clearance = 0.05 # Клиренс глюкагона
        self.basal_glu_secr = 2.5   # Базовая секреция глюкагона
        
        # --- Параметры Дельта-клеток (Соматостатин) ---
        self.k_sst = 0.2 # Коэффициент влияния соматостатина (паракринное ингибирование)
        
    def calculate_delta(self, current_time, step_size, blood_state, messages):
        from models.messages import AdaptationMsg
        
        # Проверка сообщений долгосрочной адаптации (например, отмирание бета-клеток)
        for msg in messages:
            if isinstance(msg, AdaptationMsg):
                self.beta_mass = msg.beta_mass_multiplier

        # Извлечение текущих концентраций из крови (во избежание деления на ноль)
        g = max(0.1, blood_state["glucose"]) 
        i = max(0.1, blood_state["insulin"])
        glu = max(0.1, blood_state["glucagon"])
        inc = max(1.0, blood_state["incretin"])
        
        # Фактор инкретина (GLP-1), базовый = 1.0 (при 10 пмоль/Л)
        incretin_factor = inc / 10.0
        # Каппинг эффекта инкретина до 5x, чтобы предотвратить мгновенное истощение пула M1 при сверхвысоком GLP-1
        incretin_factor = min(5.0, incretin_factor)
        
        # --- Дельта-клетки (Соматостатин) ---
        # Выделение соматостатина стимулируется Глюкозой и Инкретинами
        sst_factor = (g / 5.0) * incretin_factor
        basal_inhibition_val = 1.0 / (1.0 + self.k_sst) # Нормализация (чтобы в базе давало 1.0)
        # Паракринное ингибирование - "успокаивает" соседей (альфа и бета клетки)
        paracrine_inhibition = (1.0 / (1.0 + self.k_sst * sst_factor)) / basal_inhibition_val
        
        # --- Бета-клетки (Инсулин, 2-Pool Model) ---
        # 1. Выброс в кровь из пула M1
        # Функция Хилла определяет процент выплескиваемых гранул в зависимости от глюкозы
        k_release = self.k_release_max * (g**2) / (self.alpha_hill + g**2) * incretin_factor
        actual_release_rate = k_release * paracrine_inhibition * self.beta_mass
        secretion_i = actual_release_rate * self.M1
        
        # 2. Перемещение гранул из M2 в M1 (мобилизация)
        # GLP-1 мощно стимулирует не только релиз, но и подготовку новых гранул
        transfer_rate = self.k_transfer * self.M2 * g * incretin_factor
        
        # 3. Синтез de-novo в пул M2
        synthesis = self.basal_synthesis * (g / 5.0) * self.beta_mass
        
        # Применение изменений к внутриклеточным пулам
        self.M1 += (transfer_rate - secretion_i) * step_size
        self.M2 += (synthesis - transfer_rate) * step_size
        self.M1 = max(0.0, self.M1)
        self.M2 = max(0.0, self.M2)
        
        # Отправка чистого изменения инсулина в кровь (Секреция минус Клиренс)
        clearance_i = self.k_I_clearance * i
        self.blood_pool.add_insulin_delta(secretion_i - clearance_i)
        
        # --- Альфа-клетки (Глюкагон) ---
        # Секреция подавляется Глюкозой (g), Инсулином (i), Инкретином и Соматостатином
        glu_secretion = self.basal_glu_secr * (25.0 / (g**2)) * (60.0 / i) * (1.0 / incretin_factor) * paracrine_inhibition
        glu_secretion = min(glu_secretion, 50.0) # Защита от деления на сверхмалые числа при гипогликемии
        
        glu_clearance = self.k_Glu_clearance * glu
        self.blood_pool.add_glucagon_delta(glu_secretion - glu_clearance)
