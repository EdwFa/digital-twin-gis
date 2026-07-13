from .base import BaseAgent
from models.messages import AdaptationMsg
import math

class SlowAdaptationAgent(BaseAgent):
    """
    Агент Долгосрочной Адаптации (Slow Adaptation Agent).
    Моделирует хронические изменения в организме (старение, диабет, ожирение).
    Работает в фоновом режиме, собирает статистику и медленно меняет базовые параметры органов.
    """
    def __init__(self, blood_pool, message_bus):
        super().__init__("SlowAdaptation", blood_pool, message_bus)
        
        # Фактор сглаживания для HbA1c (период полувыведения эритроцитов около 30-60 дней)
        self.k_hba1c = 1.0 / 43200.0
        self.hba1c_estimate = 5.0 # Безопасное стартовое предположение (%)
        
        # Отслеживание липотоксичности (средний уровень FFA за ~7 дней)
        self.k_ffa_avg = 1.0 / 10000.0 
        self.ffa_avg = 0.4 
        
        # Множители, которые этот агент транслирует органам
        self.beta_mass_multiplier = 1.0
        self.si_multiplier = 1.0
        
        # Константы скорости деградации организма
        self.k_apoptosis = 1.0e-6 # Скорость гибели бета-клеток при гипергликемии
        self.k_lipotoxicity = 1.0e-6 # Скорость падения чувствительности к инсулину при высоком жире

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        g = blood_state["glucose"]
        ffa = max(0.0, blood_state["ffa"])
        
        # 1. Глюкотоксичность (влияние сахара на HbA1c)
        # Конвертация мгновенной концентрации глюкозы (ммоль/Л) во вклад в HbA1c (%)
        instant_hba1c = (g + 2.59) / 1.59
        self.hba1c_estimate += (instant_hba1c - self.hba1c_estimate) * self.k_hba1c * step_size
        
        if self.hba1c_estimate > 6.5:
            # Апоптоз (программируемая гибель) бета-клеток поджелудочной железы
            # при хронически высоком сахаре
            degradation = self.k_apoptosis * (self.hba1c_estimate - 6.5) * step_size
            self.beta_mass_multiplier = max(0.1, self.beta_mass_multiplier - degradation)
            
        # 2. Липотоксичность (Системная Инсулинорезистентность)
        self.ffa_avg += (ffa - self.ffa_avg) * self.k_ffa_avg * step_size
        if self.ffa_avg > 0.6:
            # При хронически высоком уровне жирных кислот чувствительность к инсулину падает во всем теле
            degradation_si = self.k_lipotoxicity * (self.ffa_avg - 0.6) * step_size
            self.si_multiplier = max(0.1, self.si_multiplier - degradation_si)
            
        # 3. Публикация сообщения адаптации для целевых органов
        # Органы слушают эти сообщения и применяют множители к своим параметрам
        msg = AdaptationMsg(
            beta_mass_multiplier=self.beta_mass_multiplier,
            insulin_sensitivity_multiplier=self.si_multiplier
        )
        self.message_bus.publish(msg)
