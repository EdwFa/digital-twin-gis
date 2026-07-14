import math
from .base import BaseAgent
from models.messages import DrugAdministrationMsg, PortalVeinInflowMsg, AdaptationMsg

class LiverPBPKSuperAgent(BaseAgent):
    """
    Печень: Супер-Агент уровня PBPK (Physiologically Based Pharmacokinetic).
    L1 Модель: Well-stirred (один компартмент печени).
    Объединяет гомеостаз глюкозы (ГИС) и фармакокинетику лекарств (эффект первого прохождения).
    """
    def __init__(self, blood_pool, message_bus):
        super().__init__("LiverPBPK", blood_pool, message_bus)
        
        # ==========================================
        # 1. PBPK ПАРАМЕТРЫ (Well-stirred model)
        # ==========================================
        self.liver_mass_kg = 1.5
        self.Q_H = 1.45 # Печеночный кровоток (л/мин)
        self.V_blood = 16.0 # Объем распределения для крови (условно общий для простоты)
        
        # Активность ферментов CYP450 (1.0 = 100% нормы)
        self.cyp_activities = {
            "CYP3A4": 1.0,
            "CYP2D6": 1.0,
            "CYP2C19": 1.0,
            "CYP1A2": 1.0
        }
        
        # Встроенная база данных свойств веществ
        self.substance_db = {
            "propranolol": {
                "f_u": 0.13, # Свободная фракция в плазме (13%)
                "CL_int_base": 15.0, # Базовый внутренний клиренс (л/мин)
                "cyp_pathways": {"CYP2D6": 0.8, "CYP1A2": 0.2} # Вклад ферментов
            }
        }
        
        # ==========================================
        # 2. ГИС ПАРАМЕТРЫ (Гомеостаз глюкозы)
        # ==========================================
        self.egp_fasting = 0.179 # Базовая продукция (ммоль/Л/мин)
        self.liver_SI = 1.0      # Чувствительность к инсулину
        self.max_glycogen = 35.0
        self.glycogen_pool = 25.0 
        self.k_uptake = 0.0001 

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        # --- ОБРАБОТКА ВХОДЯЩИХ СООБЩЕНИЙ ---
        for msg in messages:
            if isinstance(msg, AdaptationMsg):
                self.liver_SI = msg.insulin_sensitivity_multiplier
            elif isinstance(msg, PortalVeinInflowMsg):
                # Всасывание из кишечника напрямую в воротную вену (first-pass)
                for sub, rate in msg.substances_mmol_L.items():
                    # rate здесь в ммоль/мин. Добавляем в общий кровоток (размазывая по V_blood)
                    # Это упрощение для L1, реальный first-pass отработает ниже.
                    # Но правильнее - ЖКТ должен пушить вещества в кровь сам, а печень их выводит.
                    pass

        # --- БЛОК 1: ФАРМАКОКИНЕТИКА (PK) ---
        for substance, props in self.substance_db.items():
            C_plasma = blood_state.get(substance, 0.0)
            if C_plasma > 0.0:
                # 1. Вычисляем суммарный CL_int на основе текущих активностей ферментов
                cl_int_total = 0.0
                for cyp, frac in props["cyp_pathways"].items():
                    act = self.cyp_activities.get(cyp, 1.0)
                    cl_int_total += props["CL_int_base"] * frac * act
                    
                f_u = props["f_u"]
                
                # 2. Расчет по модели Well-stirred
                # Extraction ratio (Доля извлечения печенью за 1 проход)
                E_H = (cl_int_total * f_u) / (self.Q_H + cl_int_total * f_u)
                
                # Печеночный клиренс (л/мин)
                CL_H = self.Q_H * E_H
                
                # 3. Скорость элиминации из крови (ммоль/Л/мин)
                # dC/dt = - (CL_H / V) * C_plasma
                elimination_rate = -(CL_H / self.V_blood) * C_plasma
                self.blood_pool.add_delta(substance, elimination_rate)


        # --- БЛОК 2: ГОМЕОСТАЗ ГЛЮКОЗЫ (ГИС) ---
        g = max(0.1, blood_state.get("glucose", 5.0))
        i = max(0.1, blood_state.get("insulin", 60.0))
        glu = max(0.1, blood_state.get("glucagon", 50.0))
        
        GNG_basal = 0.3 * self.egp_fasting
        GGL_basal = 0.7 * self.egp_fasting
        
        i_factor = max(0.1, (i / 60.0) * self.liver_SI)
        glu_factor = glu / 50.0
        hormonal_drive = glu_factor / i_factor
        
        GNG = GNG_basal * hormonal_drive
        GGL = GGL_basal * hormonal_drive
        if self.glycogen_pool < 5.0:
            GGL *= max(0.0, self.glycogen_pool / 5.0) 
            
        capacity_factor = max(0.0, 1.0 - (self.glycogen_pool / self.max_glycogen)**4)
        uptake = self.k_uptake * g * i * self.liver_SI * capacity_factor
        
        self.glycogen_pool += (uptake - GGL) * step_size
        self.glycogen_pool = max(0.0, min(self.max_glycogen, self.glycogen_pool))
        
        net_glucose_flux = GNG + GGL - uptake
        self.blood_pool.add_delta("glucose", net_glucose_flux)
