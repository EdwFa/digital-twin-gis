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
    L3 Транспортеры: Учет захвата (OATP) и билиарной экскреции (MRP2).
    """
    def __init__(self, blood_pool, message_bus):
        super().__init__("LiverPBPK", blood_pool, message_bus)
        
        # ==========================================
        # 1. PBPK ПАРАМЕТРЫ (L2 Zonal model)
        # ==========================================
        self.liver_mass_kg = 1.5
        self.Q_H = 1.45 # Печеночный кровоток (л/мин)
        self.V_blood = 16.0 # Объем распределения 
        
        # Резервуар желчи (накопление экскретированных веществ)
        self.bile_pool = {}
        
        # Генотип пациента (по умолчанию нормальный)
        self.genotype = {
            "OATP1B1": 1.0  # У носителей *5 аллеля будет 0.4
        }
        
        self.cyp_activities_base = {
            "CYP3A4": 1.0,
            "CYP2D6": 1.0,
            "CYP2C19": 1.0,
            "CYP1A2": 1.0,
            "CYP2E1": 1.0,
            "UGT": 1.0
        }
        
        self.zones = [
            HepatocyteZone("Zone1", {"CYP3A4": 0.6, "CYP2D6": 0.33, "CYP2C19": 0.6, "CYP1A2": 0.1, "CYP2E1": 0.1, "UGT": 0.33}),
            HepatocyteZone("Zone2", {"CYP3A4": 0.3, "CYP2D6": 0.33, "CYP2C19": 0.3, "CYP1A2": 0.3, "CYP2E1": 0.3, "UGT": 0.33}),
            HepatocyteZone("Zone3", {"CYP3A4": 0.1, "CYP2D6": 0.34, "CYP2C19": 0.1, "CYP1A2": 0.6, "CYP2E1": 0.6, "UGT": 0.34})
        ]
        
        # База веществ (добавлены транспортеры)
        self.substance_db = {
            "propranolol": {
                "f_u": 0.13, 
                "CL_int_base": 15.0, 
                "cyp_pathways": {"CYP2D6": 0.8, "CYP1A2": 0.2},
                "transporters": None # Высоко липофильное, проникает пассивно, CL_net ~ CL_met
            },
            "simvastatin": {
                "f_u": 0.05,
                "CL_int_base": 25.0,
                "cyp_pathways": {"CYP3A4": 1.0},
                "transporters": {
                    "uptake": {"OATP1B1": 50.0}, # Мощный активный захват
                    "efflux_blood": {"passive": 2.0},
                    "efflux_bile": {"MRP2": 5.0} # Частично выводится в желчь
                }
            },
            "paracetamol": {
                "f_u": 0.80,
                "CL_int_base": 8.0,
                "cyp_pathways": {"CYP2E1": 0.1, "UGT": 0.9},
                "transporters": None
            },
            "furanocoumarins": {
                "f_u": 0.10,
                "CL_int_base": 2.0,
                "cyp_pathways": {"CYP3A4": 1.0},
                "transporters": None
            }
        }
        
        # ГИС Параметры
        self.egp_fasting = 0.179 
        self.liver_SI = 1.0      
        self.max_glycogen = 35.0
        self.glycogen_pool = 25.0 
        self.k_uptake = 0.0001 

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        # Обработка сообщений
        for msg in messages:
            if isinstance(msg, AdaptationMsg):
                self.liver_SI = msg.insulin_sensitivity_multiplier

        # Динамическое ингибирование DDI
        current_cyps = self.cyp_activities_base.copy()
        if blood_state.get("furanocoumarins", 0.0) > 0.01:
            current_cyps["CYP3A4"] *= 0.30 

        # --- БЛОК 1: ФАРМАКОКИНЕТИКА (L3 Transporters & Zonal Tube Model) ---
        for substance, props in self.substance_db.items():
            C_plasma = blood_state.get(substance, 0.0)
            if C_plasma > 1e-6:
                C_in = C_plasma
                f_u = props["f_u"]
                
                # Инициализируем переменные для сбора статистики элиминации
                total_metabolized_fraction = 0.0
                total_biliary_fraction = 0.0
                zones_count = len(self.zones)
                
                # Прогоняем кровь через зоны
                for zone in self.zones:
                    # 1. Считаем локальный метаболический клиренс (CYP)
                    cl_met_local = 0.0
                    for cyp, frac in props["cyp_pathways"].items():
                        systemic_act = current_cyps.get(cyp, 1.0)
                        zonal_share = zone.cyp_distribution.get(cyp, 0.333)
                        cl_met_local += props["CL_int_base"] * frac * systemic_act * zonal_share
                    
                    # 2. Учет транспортеров (Extended Clearance Concept)
                    cl_net_local = cl_met_local
                    frac_to_bile = 0.0
                    frac_to_met = 1.0
                    
                    transporters = props.get("transporters")
                    if transporters:
                        # Активный захват из крови
                        cl_uptake = 0.0
                        for transp, base_cl in transporters.get("uptake", {}).items():
                            cl_uptake += base_cl * self.genotype.get(transp, 1.0) # Учет генотипа (e.g. OATP1B1)
                            
                        # Отток обратно в кровь
                        cl_efflux_blood = sum(transporters.get("efflux_blood", {}).values())
                        
                        # Экскреция в желчь
                        cl_bile = sum(transporters.get("efflux_bile", {}).values())
                        
                        # Если захват есть, применяем псевдостационарную формулу:
                        # CL_net = CL_uptake * (CL_bile + CL_met) / (CL_efflux_blood + CL_bile + CL_met)
                        denominator = cl_efflux_blood + cl_bile + cl_met_local
                        if denominator > 0:
                            cl_net_local = cl_uptake * (cl_bile + cl_met_local) / denominator
                            frac_to_bile = cl_bile / (cl_bile + cl_met_local)
                            frac_to_met = cl_met_local / (cl_bile + cl_met_local)
                    
                    total_biliary_fraction += frac_to_bile / zones_count
                    total_metabolized_fraction += frac_to_met / zones_count
                    
                    # 3. Экспоненциальное падение концентрации в зоне (Tube Model)
                    exponent = -(cl_net_local * f_u) / self.Q_H
                    C_out = C_in * math.exp(exponent)
                    C_in = C_out
                    
                C_hv = C_in
                
                # Масса, извлеченная печенью за 1 минуту
                eliminated_mass = self.Q_H * (C_plasma - C_hv)
                elimination_rate = -(eliminated_mass / self.V_blood)
                
                self.blood_pool.add_delta(substance, elimination_rate)
                
                # Физическое накопление в желчи
                mass_to_bile = eliminated_mass * total_biliary_fraction
                if mass_to_bile > 0:
                    self.bile_pool[substance] = self.bile_pool.get(substance, 0.0) + mass_to_bile

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
