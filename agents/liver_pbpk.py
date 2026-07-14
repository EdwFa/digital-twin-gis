import math
from dataclasses import dataclass
from .base import BaseAgent
from models.messages import DrugAdministrationMsg, PortalVeinInflowMsg, AdaptationMsg

@dataclass
class HepatocyteZone:
    """Субагент зоны печени (компартмент ацинуса)"""
    name: str
    cyp_distribution: dict  # Доля от общей активности ферментов печени (от 0 до 1.0)

class LiverPBPKSuperAgent(BaseAgent):
    """
    Печень: Супер-Агент уровня PBPK (Physiologically Based Pharmacokinetic).
    L2 Модель: 3 Зоны Раппапорта (Tube Model с градиентом концентрации).
    """
    def __init__(self, blood_pool, message_bus):
        super().__init__("LiverPBPK", blood_pool, message_bus)
        
        # ==========================================
        # 1. PBPK ПАРАМЕТРЫ (L2 Zonal model)
        # ==========================================
        self.liver_mass_kg = 1.5
        self.Q_H = 1.45 # Печеночный кровоток (л/мин)
        self.V_blood = 16.0 # Объем распределения (условно общий для плазмы)
        
        # Общая системная (базовая) активность ферментов
        self.cyp_activities_base = {
            "CYP3A4": 1.0,
            "CYP2D6": 1.0,
            "CYP2C19": 1.0,
            "CYP1A2": 1.0,
            "CYP2E1": 1.0,
            "UGT": 1.0      # Конъюгация
        }
        
        # 3 зоны Раппапорта с распределением ферментов по градиенту кислорода
        self.zones = [
            HepatocyteZone("Zone1", { # Высокий кислород, оксидативный метаболизм
                "CYP3A4": 0.6, "CYP2D6": 0.33, "CYP2C19": 0.6, "CYP1A2": 0.1, "CYP2E1": 0.1, "UGT": 0.33
            }),
            HepatocyteZone("Zone2", { # Переходная зона
                "CYP3A4": 0.3, "CYP2D6": 0.33, "CYP2C19": 0.3, "CYP1A2": 0.3, "CYP2E1": 0.3, "UGT": 0.33
            }),
            HepatocyteZone("Zone3", { # Низкий кислород, гипоксия
                "CYP3A4": 0.1, "CYP2D6": 0.34, "CYP2C19": 0.1, "CYP1A2": 0.6, "CYP2E1": 0.6, "UGT": 0.34
            })
        ]
        
        # База веществ для тестирования PBPK L2
        self.substance_db = {
            "propranolol": {
                "f_u": 0.13, 
                "CL_int_base": 15.0, 
                "cyp_pathways": {"CYP2D6": 0.8, "CYP1A2": 0.2}
            },
            "simvastatin": {
                "f_u": 0.05,
                "CL_int_base": 25.0,
                "cyp_pathways": {"CYP3A4": 1.0}
            },
            "paracetamol": {
                "f_u": 0.80,
                "CL_int_base": 8.0,
                "cyp_pathways": {"CYP2E1": 0.1, "UGT": 0.9} # 10% идет в токсичный NAPQI
            },
            "furanocoumarins": { # Компонент грейпфрутового сока (Ингибитор)
                "f_u": 0.10,
                "CL_int_base": 2.0,
                "cyp_pathways": {"CYP3A4": 1.0}
            }
        }
        
        # ==========================================
        # 2. ГИС ПАРАМЕТРЫ (Гомеостаз глюкозы)
        # ==========================================
        self.egp_fasting = 0.179 
        self.liver_SI = 1.0      
        self.max_glycogen = 35.0
        self.glycogen_pool = 25.0 
        self.k_uptake = 0.0001 

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        # --- ОБРАБОТКА ВХОДЯЩИХ СООБЩЕНИЙ ---
        for msg in messages:
            if isinstance(msg, AdaptationMsg):
                self.liver_SI = msg.insulin_sensitivity_multiplier

        # Динамическое ингибирование ферментов (например, DDI от грейпфрута)
        current_cyps = self.cyp_activities_base.copy()
        if blood_state.get("furanocoumarins", 0.0) > 0.01:
            # Необратимое ингибирование CYP3A4 в печени
            current_cyps["CYP3A4"] *= 0.30 

        # --- БЛОК 1: ФАРМАКОКИНЕТИКА (L2 Zonal Tube Model) ---
        for substance, props in self.substance_db.items():
            C_plasma = blood_state.get(substance, 0.0)
            if C_plasma > 1e-6:
                C_in = C_plasma
                f_u = props["f_u"]
                
                # Прогоняем кровь последовательно через 3 зоны (Tube model)
                for zone in self.zones:
                    # Считаем локальный клиренс в этой зоне
                    cl_int_local = 0.0
                    for cyp, frac in props["cyp_pathways"].items():
                        systemic_act = current_cyps.get(cyp, 1.0)
                        zonal_share = zone.cyp_distribution.get(cyp, 0.333)
                        
                        cl_int_local += props["CL_int_base"] * frac * systemic_act * zonal_share
                    
                    # Концентрация на выходе из текущей зоны
                    # C_out = C_in * exp(-CL_int_local * f_u / Q_H)
                    exponent = -(cl_int_local * f_u) / self.Q_H
                    C_out = C_in * math.exp(exponent)
                    
                    # Вход в следующую зону - это выход из предыдущей
                    C_in = C_out
                    
                # C_in после цикла - это C_hv (концентрация в печеночной вене)
                C_hv = C_in
                
                # Общая элиминация из крови (ммоль/Л/мин)
                # Сколько вещества было удалено за 1 минуту:
                # Извлеченная масса = Q_H * (C_plasma - C_hv)
                eliminated_mass = self.Q_H * (C_plasma - C_hv)
                elimination_rate = -(eliminated_mass / self.V_blood)
                
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
