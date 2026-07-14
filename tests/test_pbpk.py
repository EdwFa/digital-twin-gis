import unittest
from core.blood_pool import BloodPool
from core.message_bus import MessageBus
from agents.liver_pbpk import LiverPBPKSuperAgent
from models.messages import PortalVeinInflowMsg

class TestLiverPBPK(unittest.TestCase):
    def test_liver_pbpk_first_pass(self):
        """
        Проверка L1 Well-Stirred модели печени: First-pass метаболизм пропранолола.
        Убеждаемся, что печень корректно извлекает (очищает) кровь от лекарства.
        """
        blood = BloodPool()
        msg_bus = MessageBus()
        
        liver = LiverPBPKSuperAgent(blood, msg_bus)
        
        # Вливаем пропранолол в кровь (имитируем всасывание)
        blood.concentrations["propranolol"] = 10.0
        
        c_initial = blood.get_concentration("propranolol")
        
        # Делаем один шаг симуляции
        liver._tick(0, 1.0, blood.get_state())
        blood.resolve_step(1.0)
        
        c_final = blood.get_concentration("propranolol")
        
        # За 1 минуту концентрация должна упасть в соответствии с Tube Model:
        # C_hv = C_in * exp(-CL_int_total * f_u / Q_H) = 10 * exp(-15*0.13 / 1.45) = 2.6058
        # Eliminated mass = Q_H * (10 - 2.6058) = 10.72159
        # ΔC = -10.72159 / 16.0 = -0.670099
        expected_c_final = c_initial - 0.670099
    
        self.assertTrue(abs(c_final - expected_c_final) < 0.01, f"Expected {expected_c_final}, got {c_final}")
        self.assertTrue(c_final < c_initial, "Концентрация должна уменьшиться из-за печеночного клиренса")

    def test_liver_gis_backward_compatibility(self):
        """
        Проверяем, что LiverPBPKSuperAgent не сломал старую логику выработки глюкозы.
        """
        blood = BloodPool()
        msg_bus = MessageBus()
        liver = LiverPBPKSuperAgent(blood, msg_bus)
        
        # Состояние натощак (инсулин низкий, глюкагон высокий)
        blood.concentrations["glucose"] = 4.5
        blood.concentrations["insulin"] = 20.0
        blood.concentrations["glucagon"] = 80.0
        
        liver._tick(0, 1.0, blood.get_state())
        blood.resolve_step(1.0)
        
        self.assertTrue(blood.concentrations["glucose"] > 4.5)

    def test_ddi_simvastatin_furanocoumarin(self):
        """
        Проверка лекарственного взаимодействия (DDI):
        Грейпфрутовый сок (фуранокумарины) подавляет CYP3A4, замедляя элиминацию симвастатина.
        """
        blood_normal = BloodPool()
        liver_normal = LiverPBPKSuperAgent(blood_normal, MessageBus())
        blood_normal.concentrations["simvastatin"] = 10.0
        
        blood_ddi = BloodPool()
        liver_ddi = LiverPBPKSuperAgent(blood_ddi, MessageBus())
        blood_ddi.concentrations["simvastatin"] = 10.0
        blood_ddi.concentrations["furanocoumarins"] = 1.0 # Ингибитор присутствует
        
        liver_normal._tick(0, 1.0, blood_normal.get_state())
        blood_normal.resolve_step(1.0)
        
        liver_ddi._tick(0, 1.0, blood_ddi.get_state())
        blood_ddi.resolve_step(1.0)
        
        c_final_normal = blood_normal.get_concentration("simvastatin")
        c_final_ddi = blood_ddi.get_concentration("simvastatin")
        
        # С ингибитором концентрация должна быть ВЫШЕ (элиминация медленнее)
        self.assertTrue(c_final_ddi > c_final_normal)
        self.assertTrue(c_final_ddi < 10.0) # Но элиминация все равно происходит

    def test_oatp_polymorphism_and_biliary_excretion(self):
        """
        Проверка L3: Клеточные транспортеры и полиморфизм.
        1. Сравниваем нормальный генотип OATP1B1 с мутацией *5 (сниженный захват).
        2. Проверяем, что симвастатин накапливается в желчи (bile_pool).
        """
        blood_wt = BloodPool()
        liver_wt = LiverPBPKSuperAgent(blood_wt, MessageBus())
        blood_wt.concentrations["simvastatin"] = 10.0
        
        blood_mut = BloodPool()
        liver_mut = LiverPBPKSuperAgent(blood_mut, MessageBus())
        blood_mut.concentrations["simvastatin"] = 10.0
        # Пациент с полиморфизмом OATP1B1*5 (сниженная активность в 2.5 раза)
        liver_mut.genotype["OATP1B1"] = 0.4 
        
        liver_wt._tick(0, 1.0, blood_wt.get_state())
        blood_wt.resolve_step(1.0)
        
        liver_mut._tick(0, 1.0, blood_mut.get_state())
        blood_mut.resolve_step(1.0)
        
        c_final_wt = blood_wt.get_concentration("simvastatin")
        c_final_mut = blood_mut.get_concentration("simvastatin")
        
        # У мутанта захват хуже, поэтому в крови должно остаться БОЛЬШЕ статина
        self.assertTrue(c_final_mut > c_final_wt)
        
        # Проверяем экскрецию в желчь у дикого типа
        bile_simva = liver_wt.bile_pool.get("simvastatin", 0.0)
        self.assertTrue(bile_simva > 0.0, "Симвастатин должен экскретироваться в желчь")
        
        # У мутанта в желчь должно попасть МЕНЬШЕ статина (т.к. он хуже захватывается из крови)
        bile_simva_mut = liver_mut.bile_pool.get("simvastatin", 0.0)
        self.assertTrue(bile_simva_mut < bile_simva)

    def test_hypoalbuminemia_increases_clearance(self):
        """
        Проверка L4: Динамический расчет свободной фракции (f_u) от уровня альбумина.
        Если альбумина мало, f_u возрастает, что ведет к ускорению элиминации пропранолола.
        """
        blood_norm = BloodPool()
        liver_norm = LiverPBPKSuperAgent(blood_norm, MessageBus())
        blood_norm.concentrations["propranolol"] = 10.0
        blood_norm.concentrations["albumin"] = 40.0 # Норма
        
        blood_hypo = BloodPool()
        liver_hypo = LiverPBPKSuperAgent(blood_hypo, MessageBus())
        blood_hypo.concentrations["propranolol"] = 10.0
        blood_hypo.concentrations["albumin"] = 20.0 # Низкий альбумин (свободной фракции в 2 раза больше)
        
        liver_norm._tick(0, 1.0, blood_norm.get_state())
        blood_norm.resolve_step(1.0)
        
        liver_hypo._tick(0, 1.0, blood_hypo.get_state())
        blood_hypo.resolve_step(1.0)
        
        c_final_norm = blood_norm.get_concentration("propranolol")
        c_final_hypo = blood_hypo.get_concentration("propranolol")
        
        # При низком альбумине клиренс выше, концентрация должна упасть сильнее
        self.assertTrue(c_final_hypo < c_final_norm)

    def test_hypothyroidism_decreases_clearance(self):
        """
        Проверка L4: Влияние гормонов на метаболизм.
        Пониженный T3 (гипотиреоз) замедляет работу ферментов (CYP), замедляя элиминацию.
        """
        blood_norm = BloodPool()
        liver_norm = LiverPBPKSuperAgent(blood_norm, MessageBus())
        blood_norm.concentrations["propranolol"] = 10.0
        blood_norm.concentrations["T3"] = 2.0 # Норма
        
        blood_hypo = BloodPool()
        liver_hypo = LiverPBPKSuperAgent(blood_hypo, MessageBus())
        blood_hypo.concentrations["propranolol"] = 10.0
        blood_hypo.concentrations["T3"] = 1.0 # Гипотиреоз (метаболизм замедлен)
        
        liver_norm._tick(0, 1.0, blood_norm.get_state())
        blood_norm.resolve_step(1.0)
        
        liver_hypo._tick(0, 1.0, blood_hypo.get_state())
        blood_hypo.resolve_step(1.0)
        
        c_final_norm = blood_norm.get_concentration("propranolol")
        c_final_hypo = blood_hypo.get_concentration("propranolol")
        
        # При гипотиреозе элиминация замедлена, в крови остается БОЛЬШЕ пропранолола
        self.assertTrue(c_final_hypo > c_final_norm)

    def test_cirrhosis_child_pugh_c(self):
        """
        Проверка L5: Цирроз (Child-Pugh C).
        Одновременно падают: Q_H (кровоток), Albumin (свободная фракция растет), CYP_activities (клиренс падает).
        """
        blood_norm = BloodPool()
        liver_norm = LiverPBPKSuperAgent(blood_norm, MessageBus())
        blood_norm.concentrations["propranolol"] = 10.0
        
        blood_cirrhosis = BloodPool()
        liver_cirrhosis = LiverPBPKSuperAgent(blood_cirrhosis, MessageBus())
        blood_cirrhosis.concentrations["propranolol"] = 10.0
        liver_cirrhosis.pathologies["cirrhosis_child_pugh"] = "C"
        
        liver_norm._tick(0, 1.0, blood_norm.get_state())
        blood_norm.resolve_step(1.0)
        
        liver_cirrhosis._tick(0, 1.0, blood_cirrhosis.get_state())
        blood_cirrhosis.resolve_step(1.0)
        
        c_final_norm = blood_norm.get_concentration("propranolol")
        c_final_cirrhosis = blood_cirrhosis.get_concentration("propranolol")
        
        # Из-за критического падения CYP и Q_H, элиминация при циррозе сильно замедлена, несмотря на рост f_u
        self.assertTrue(c_final_cirrhosis > c_final_norm)

    def test_alcohol_cyp2e1_induction(self):
        """
        Проверка L5: Индукция алкоголем фермента CYP2E1.
        Ускоряет метаболизм парацетамола.
        """
        blood_norm = BloodPool()
        liver_norm = LiverPBPKSuperAgent(blood_norm, MessageBus())
        blood_norm.concentrations["paracetamol"] = 20.0
        
        blood_alcohol = BloodPool()
        liver_alcohol = LiverPBPKSuperAgent(blood_alcohol, MessageBus())
        blood_alcohol.concentrations["paracetamol"] = 20.0
        liver_alcohol.pathologies["alcohol_induction"] = 3.0 # Хронический алкоголизм (CYP2E1 x3)
        
        liver_norm._tick(0, 1.0, blood_norm.get_state())
        blood_norm.resolve_step(1.0)
        
        liver_alcohol._tick(0, 1.0, blood_alcohol.get_state())
        blood_alcohol.resolve_step(1.0)
        
        c_final_norm = blood_norm.get_concentration("paracetamol")
        c_final_alcohol = blood_alcohol.get_concentration("paracetamol")
        
        # У алкоголика CYP2E1 работает в 3 раза активнее, концентрация парацетамола падает быстрее
        self.assertTrue(c_final_alcohol < c_final_norm)

if __name__ == '__main__':
    unittest.main()
