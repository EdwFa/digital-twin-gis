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
        
        # За 1 минуту концентрация должна упасть примерно на 5.2%
        expected_c_final = c_initial - (0.8316 / 16.0) * c_initial
    
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

if __name__ == '__main__':
    unittest.main()
