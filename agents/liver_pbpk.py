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
    L4 Метаболические функции: Альбумин, Липиды, Гормоны.
    L5 Патологии: Цирроз, Воспаление, NAFLD, Алкоголь.
    """
    def __init__(self, blood_pool, message_bus):
        super().__init__("LiverPBPK", blood_pool, message_bus)
        
        # ==========================================
        # 1. PBPK БАЗОВЫЕ ПАРАМЕТРЫ
        # ==========================================
        self.liver_mass_kg = 1.5
        self.base_Q_H = 1.45 # Базовый печеночный кровоток (л/мин)
        self.V_blood = 16.0 
        
        self.bile_pool = {}
        
        # Генотип
        self.genotype = {
            "OATP1B1": 1.0 
        }
        
        # Патологии (Уровень L5)
        self.pathologies = {
            "cirrhosis_child_pugh": None, # "A", "B", "C" или None
            "nafld": False,
            "inflammation_il6": 1.0, # > 1.0 подавляет CYP
            "alcohol_induction": 1.0 # > 1.0 усиливает CYP2E1
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
        
        self.substance_db = {
            "propranolol": {
                "f_u_base": 0.13, 
                "CL_int_base": 15.0, 
                "cyp_pathways": {"CYP2D6": 0.8, "CYP1A2": 0.2},
                "transporters": None 
            },
            "simvastatin": {
                "f_u_base": 0.05,
                "CL_int_base": 25.0,
                "cyp_pathways": {"CYP3A4": 1.0},
                "transporters": {
                    "uptake": {"OATP1B1": 50.0},
                    "efflux_blood": {"passive": 2.0},
                    "efflux_bile": {"MRP2": 5.0} 
                }
            },
            "paracetamol": {
                "f_u_base": 0.80,
                "CL_int_base": 8.0,
                "cyp_pathways": {"CYP2E1": 0.1, "UGT": 0.9},
                "transporters": None
            },
            "furanocoumarins": {
                "f_u_base": 0.10,
                "CL_int_base": 2.0,
                "cyp_pathways": {"CYP3A4": 1.0},
                "transporters": None
            }
        }
        
        self.base_normal_albumin = 40.0
        for name, props in self.substance_db.items():
            fu = props["f_u_base"]
            props["K_a"] = (1.0 - fu) / (fu * self.base_normal_albumin)
        
        # ==========================================
        # 2. БАЗОВЫЕ МЕТАБОЛИЧЕСКИЕ ПАРАМЕТРЫ
        # ==========================================
        self.egp_fasting = 0.179 
        self.liver_SI = 1.0      
        self.base_max_glycogen = 35.0
        self.glycogen_pool = 25.0 
        self.k_uptake = 0.0001 
        
        if "albumin" not in self.blood_pool.concentrations:
            self.blood_pool.concentrations["albumin"] = 40.0
        if "T4" not in self.blood_pool.concentrations:
            self.blood_pool.concentrations["T4"] = 100.0 
        if "T3" not in self.blood_pool.concentrations:
            self.blood_pool.concentrations["T3"] = 2.0   

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        for msg in messages:
            if isinstance(msg, AdaptationMsg):
                self.liver_SI = msg.insulin_sensitivity_multiplier

        # --- L5 ПАТОЛОГИИ: Модификаторы ---
        effective_Q_H = self.base_Q_H
        effective_max_glycogen = self.base_max_glycogen
        effective_normal_albumin = self.base_normal_albumin
        cyp_disease_modifier = 1.0
        
        cp_class = self.pathologies.get("cirrhosis_child_pugh")
        if cp_class == "A":
            effective_Q_H *= 0.9
            effective_normal_albumin *= 0.8
            cyp_disease_modifier = 0.8
        elif cp_class == "B":
            effective_Q_H *= 0.7
            effective_normal_albumin *= 0.6
            cyp_disease_modifier = 0.6
        elif cp_class == "C":
            effective_Q_H *= 0.5
            effective_normal_albumin *= 0.4
            cyp_disease_modifier = 0.3
            
        if self.pathologies.get("nafld"):
            effective_max_glycogen *= 0.5 # Стеатоз снижает емкость гликогена

        # --- L4 БЕЛКОВЫЙ И ЭНДОКРИННЫЙ ОБМЕН ---
        albumin = blood_state.get("albumin", effective_normal_albumin)
        T4 = blood_state.get("T4", 100.0)
        T3 = blood_state.get("T3", 2.0)
        ffa = blood_state.get("ffa", 0.5)
        
        k_alb_syn = 0.0001
        alb_delta = k_alb_syn * (effective_normal_albumin - albumin)
        self.blood_pool.add_delta("albumin", alb_delta)
        
        k_t4_to_t3 = 0.001
        k_t3_deg = 0.05
        t3_synthesis = k_t4_to_t3 * T4
        t3_degradation = k_t3_deg * T3
        self.blood_pool.add_delta("T4", -t3_synthesis)
        self.blood_pool.add_delta("T3", t3_synthesis - t3_degradation)
        
        metabolic_rate_multiplier = max(0.1, T3 / 2.0)
        
        # L4 Липидный обмен
        insulin = max(0.1, blood_state.get("insulin", 60.0))
        ffa_uptake_rate = 0.01 * ffa * (1.0 + insulin / 60.0)
        vldl_secretion_rate = ffa_uptake_rate * 0.8
        self.blood_pool.add_delta("ffa", -ffa_uptake_rate)
        self.blood_pool.add_delta("vldl", vldl_secretion_rate)

        # --- L5 Формирование активностей CYP ---
        current_cyps = self.cyp_activities_base.copy()
        
        il6 = self.pathologies.get("inflammation_il6", 1.0)
        alcohol = self.pathologies.get("alcohol_induction", 1.0)
        
        for cyp in current_cyps:
            # 1. Гормоны (T3)
            # 2. Болезнь (Цирроз)
            current_cyps[cyp] *= metabolic_rate_multiplier * cyp_disease_modifier
            
        # Воспаление специфически давит некоторые CYP (например, 3A4, 2C19)
        if il6 > 1.0:
            current_cyps["CYP3A4"] /= il6
            current_cyps["CYP2C19"] /= il6
            
        # Алкогольная индукция специфически усиливает CYP2E1
        if alcohol > 1.0:
            current_cyps["CYP2E1"] *= alcohol

        # DDI
        if blood_state.get("furanocoumarins", 0.0) > 0.01:
            current_cyps["CYP3A4"] *= 0.30 

        # --- БЛОК 1: ФАРМАКОКИНЕТИКА (L3) ---
        for substance, props in self.substance_db.items():
            C_plasma = blood_state.get(substance, 0.0)
            if C_plasma > 1e-6:
                C_in = C_plasma
                
                K_a = props["K_a"]
                f_u = 1.0 / (1.0 + K_a * albumin)
                
                total_metabolized_fraction = 0.0
                total_biliary_fraction = 0.0
                zones_count = len(self.zones)
                
                for zone in self.zones:
                    cl_met_local = 0.0
                    for cyp, frac in props["cyp_pathways"].items():
                        systemic_act = current_cyps.get(cyp, 1.0)
                        zonal_share = zone.cyp_distribution.get(cyp, 0.333)
                        cl_met_local += props["CL_int_base"] * frac * systemic_act * zonal_share
                    
                    cl_net_local = cl_met_local
                    frac_to_bile = 0.0
                    frac_to_met = 1.0
                    
                    transporters = props.get("transporters")
                    if transporters:
                        cl_uptake = 0.0
                        for transp, base_cl in transporters.get("uptake", {}).items():
                            cl_uptake += base_cl * self.genotype.get(transp, 1.0) 
                            
                        cl_efflux_blood = sum(transporters.get("efflux_blood", {}).values())
                        cl_bile = sum(transporters.get("efflux_bile", {}).values())
                        
                        denominator = cl_efflux_blood + cl_bile + cl_met_local
                        if denominator > 0:
                            cl_net_local = cl_uptake * (cl_bile + cl_met_local) / denominator
                            frac_to_bile = cl_bile / (cl_bile + cl_met_local)
                            frac_to_met = cl_met_local / (cl_bile + cl_met_local)
                    
                    total_biliary_fraction += frac_to_bile / zones_count
                    total_metabolized_fraction += frac_to_met / zones_count
                    
                    exponent = -(cl_net_local * f_u) / effective_Q_H
                    C_out = C_in * math.exp(exponent)
                    C_in = C_out
                    
                C_hv = C_in
                
                eliminated_mass = effective_Q_H * (C_plasma - C_hv)
                elimination_rate = -(eliminated_mass / self.V_blood)
                
                self.blood_pool.add_delta(substance, elimination_rate)
                
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
            
        capacity_factor = max(0.0, 1.0 - (self.glycogen_pool / effective_max_glycogen)**4)
        uptake = self.k_uptake * g * i * self.liver_SI * capacity_factor
        
        self.glycogen_pool += (uptake - GGL) * step_size
        self.glycogen_pool = max(0.0, min(effective_max_glycogen, self.glycogen_pool))
        
        net_glucose_flux = GNG + GGL - uptake
        self.blood_pool.add_delta("glucose", net_glucose_flux)
