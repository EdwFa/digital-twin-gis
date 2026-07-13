from core.message_bus import MessageBus
from models.messages import GISStateMsg

class GISSuperAgent:
    """
    Координатор для подсистемы Глюкоза-Инсулин (GIS). Уровень 1.
    Его главная задача - управлять строгим биологическим порядком 
    вызова (обновления) всех подчиненных органов (Уровень 2).
    """
    def __init__(self, blood_pool, message_bus: MessageBus):
        self.name = "GIS_SuperAgent"
        self.blood_pool = blood_pool
        self.message_bus = message_bus
        self.subagents = []
        
        # Регистрация на шине для получения внешних команд
        self.message_bus.register_mailbox(self.name)

    def add_subagent(self, agent):
        """
        Добавляет орган в систему.
        ВАЖНО: Порядок добавления имеет значение, так как определяет порядок симуляции.
        """
        self.subagents.append(agent)

    def _tick(self, current_time, step_size, blood_state):
        """Ежеминутное обновление координатора."""
        # 1. Чтение входящих внешних сообщений от Оркестратора
        messages = self.message_bus.consume(self.name)
        
        # Если есть внешние сообщения, транслируем их внутрь подсистемы
        for msg in messages:
            self.message_bus.publish(msg)
            
        # 2. Обновление дочерних агентов (органов)
        for agent in self.subagents:
            agent._tick(current_time, step_size, blood_state)
            
        # 3. Публикация агрегированного состояния крови наружу
        state_msg = GISStateMsg(
            glucose_mmol_L=blood_state["glucose"],
            insulin_pmol_L=blood_state["insulin"],
            glucagon_pmol_L=blood_state["glucagon"],
            incretin_pmol_L=blood_state["incretin"],
            ffa_mmol_L=blood_state["ffa"]
        )
        # В будущем этот Broadcast будет перехвачен Оркестратором (Уровень 0)
        # self.message_bus.publish(state_msg)

    def calibrate(self, passport):
        """
        Выполняет первоначальную настройку системы под конкретного человека.
        Проецирует физиологические метрики из Паспорта на математические коэффициенты ОДУ.
        """
        from core.calibration import calibrate_patient
        params = calibrate_patient(passport)
        
        for agent in self.subagents:
            if agent.name == "Muscle":
                agent.muscle_SI = params.muscle_SI
            elif agent.name == "Adipose":
                agent.adipose_SI = params.adipose_SI
            elif agent.name == "Liver":
                agent.liver_SI = params.liver_SI
                agent.egp_fasting = params.egp_fasting
            elif agent.name == "Gut":
                agent.V_G = params.V_G
            elif agent.name == "Pancreas":
                agent.beta_mass = params.beta_mass
