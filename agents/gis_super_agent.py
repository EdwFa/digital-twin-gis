from core.message_bus import MessageBus
from models.messages import GISStateMsg

class GISSuperAgent:
    """
    The orchestrator for the Glucose-Insulin System.
    Manages the strict update order of its sub-agents.
    """
    def __init__(self, blood_pool, message_bus: MessageBus):
        self.name = "GIS_SuperAgent"
        self.blood_pool = blood_pool
        self.message_bus = message_bus
        self.subagents = []
        
        self.message_bus.register_mailbox(self.name)

    def add_subagent(self, agent):
        """Adds a subagent. Must be added in the correct execution order."""
        self.subagents.append(agent)

    def _tick(self, current_time, step_size, blood_state):
        # 1. Read external inputs from the Orchestrator
        messages = self.message_bus.consume(self.name)
        
        # If there are external messages (e.g., MealIntakeMsg), 
        # broadcast them to internal subagents
        for msg in messages:
            self.message_bus.publish(msg)
            
        # 2. Update subagents in strict biological order
        for agent in self.subagents:
            agent._tick(current_time, step_size, blood_state)
            
        # 3. Publish aggregated state
        state_msg = GISStateMsg(
            glucose_mmol_L=blood_state["glucose"],
            insulin_pmol_L=blood_state["insulin"],
            glucagon_pmol_L=blood_state["glucagon"]
        )
        # self.message_bus.publish(state_msg)

    def calibrate(self, passport):
        from core.calibration import calibrate_patient
        params = calibrate_patient(passport)
        
        for agent in self.subagents:
            if agent.name == "Muscle":
                agent.S_I = params.S_I
            elif agent.name == "Adipose":
                agent.adipose_SI = params.adipose_SI
            elif agent.name == "Liver":
                agent.egp_fasting = params.egp_fasting
            elif agent.name == "Gut":
                agent.V_G = params.V_G
            elif agent.name == "Pancreas":
                agent.beta_mass = params.beta_mass
