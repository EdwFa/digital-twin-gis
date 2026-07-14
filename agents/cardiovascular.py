from agents.base import BaseAgent
from core.message_bus import MessageBus

class CardiovascularAgent(BaseAgent):
    """
    Агент Сердечно-сосудистой системы (Фаза 3).
    Управляет гемодинамикой: частотой сердечных сокращений (HR), ударным объемом (SV),
    сердечным выбросом (CO) и артериальным давлением (MAP).
    Включает механизм барорефлекса для поддержания давления.
    """
    def __init__(self, blood_pool, message_bus: MessageBus):
        super().__init__("Cardiovascular", blood_pool, message_bus)
        
        # Базовые (целевые) значения
        self.target_map = 90.0 # Целевое среднее артериальное давление (mmHg)
        self.target_hr = 70.0  # Целевой пульс
        self.base_sv = 70.0    # Базовый ударный объем (мл)
        
        # Индивидуальные параметры (Патологии)
        self.pathologies = {
            "hemorrhage": False,   # Кровотечение (гиповолемия)
            "heart_failure": False # Сердечная недостаточность (сниженный SV)
        }
        
    def _tick(self, current_time, step_size, blood_state):
        # 1. Читаем текущие гемодинамические параметры
        hr = self.blood_pool.hemodynamics["heart_rate"]
        sv = self.blood_pool.hemodynamics["stroke_volume"]
        tpr = self.blood_pool.hemodynamics["total_peripheral_resistance"]
        
        # 2. Моделирование патологий
        if self.pathologies.get("hemorrhage"):
            # Кровопотеря снижает ударный объем (из-за падения венозного возврата)
            sv = max(30.0, sv - 5.0 * step_size)
            
        if self.pathologies.get("heart_failure"):
            # ХСН: слабость миокарда, SV не может быть выше 50 мл
            sv = min(50.0, sv)
            
        # 3. Расчет Cardiac Output (Л/мин)
        co = (hr * sv) / 1000.0
        
        # 4. Расчет Среднего артериального давления (MAP)
        map_pressure = co * tpr
        
        # 5. Барорецепторный рефлекс (Гомеостаз)
        # Если MAP падает ниже target_map, симпатическая система увеличивает HR и TPR
        # Простая P-D (пропорционально-дифференциальная) регуляция
        error = self.target_map - map_pressure
        
        # Коэффициенты барорефлекса
        kp_hr = 0.5   # Как сильно меняем пульс
        kp_tpr = 0.05 # Как сильно сужаем сосуды
        
        # Динамика HR (возвращается к целевому, если давление в норме, или растет при шоке)
        if error > 0:
            # Гипотензия: повышаем пульс
            delta_hr = error * kp_hr * step_size
            hr = min(180.0, hr + delta_hr)
            # Сужаем сосуды
            delta_tpr = error * kp_tpr * step_size
            tpr = min(30.0, tpr + delta_tpr)
        else:
            # Гипертензия или норма: пульс и сопротивление медленно возвращаются к базовым
            hr += (self.target_hr - hr) * 0.1 * step_size
            base_tpr = self.target_map / ((self.target_hr * self.base_sv) / 1000.0)
            tpr += (base_tpr - tpr) * 0.1 * step_size
            
        # 6. Обновляем гемодинамику в BloodPool
        # Пересчитываем CO и MAP с новыми HR и TPR для консистентности
        final_co = (hr * sv) / 1000.0
        final_map = final_co * tpr
        
        self.blood_pool.hemodynamics.update({
            "heart_rate": hr,
            "stroke_volume": sv,
            "cardiac_output": final_co,
            "mean_arterial_pressure": final_map,
            "total_peripheral_resistance": tpr
        })
