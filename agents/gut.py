from .base import BaseAgent
from models.messages import MealIntakeMsg

class GutAgent(BaseAgent):
    """
    Агент Желудочно-Кишечного Тракта (Gut Agent).
    Моделирует опорожнение желудка, всасывание углеводов в кровь
    и выделение инкретинов (GLP-1) клетками кишечника (L/K-клетки).
    """
    def __init__(self, blood_pool, message_bus):
        super().__init__("Gut", blood_pool, message_bus)
        
        self.stomach_glucose_load = 0.0 # Оставшаяся масса углеводов в желудке (ммоль)
        self.V_G = 16.0 # Объем распределения глюкозы (Литры)
        
        # Параметры Инкретинового эффекта (GLP-1/GIP)
        # DPP-4 фермент быстро разрушает GLP-1 (период полураспада ~2 минуты)
        self.k_incretin_clearance = 0.35 # Клиренс в минуту
        self.incretin_basal_secretion = 3.5 # Базовая секреция для поддержания 10.0 пмоль/Л (10 * 0.35)
        self.incretin_secretion_factor = 2.0 # Множитель: сколько GLP-1 секретируется на каждый всосавшийся ммоль глюкозы
        
        # Подписка на сообщения о приеме пищи
        from models.messages import MealIntakeMsg
        self.message_bus.subscribe(self.name, MealIntakeMsg)

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        inc = blood_state["incretin"]
        
        # 1. Обработка входящей пищи
        for msg in messages:
            if isinstance(msg, MealIntakeMsg):
                # Грубая конвертация граммов углеводов в миллимоли молекул глюкозы (1г ≈ 5.55 ммоль)
                self.stomach_glucose_load += msg.carbs_g * 5.55 

        absorption_rate = 0.0
        # 2. Опорожнение желудка и всасывание (Gastric Emptying & Absorption)
        if self.stomach_glucose_load > 0:
            # Упрощенная модель экспоненциального распада (в реальности зависит от белков/жиров/клетчатки)
            absorption_rate = self.stomach_glucose_load * 0.05 
            
            # Перевод ммоль в концентрацию ммоль/Л с учетом объема крови
            concentration_delta = absorption_rate / self.V_G 
            
            # Отправляем всосавшуюся глюкозу в системный кровоток
            self.blood_pool.add_glucose_delta(concentration_delta)
            self.stomach_glucose_load -= absorption_rate * step_size
            
        # 3. L/K-клетки: Секреция инкретинов (Incretin Effect)
        # Секреция пропорциональна скорости всасывания глюкозы стенками кишечника
        secretion_inc = self.incretin_basal_secretion + (absorption_rate * self.incretin_secretion_factor)
        clearance_inc = self.k_incretin_clearance * inc
        
        # Отправляем инкретин в кровь (он достигнет Поджелудочной железы на следующем тике)
        self.blood_pool.add_incretin_delta(secretion_inc - clearance_inc)
