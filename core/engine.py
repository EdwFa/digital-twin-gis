from .message_bus import MessageBus

class SimulationEngine:
    def __init__(self, step_size_min=1.0):
        self.time_min = 0.0
        self.step_size_min = step_size_min
        self.agents = []
        self.blood_pool = None
        self.message_bus = MessageBus()

    def add_agent(self, agent):
        self.agents.append(agent)
    
    def set_blood_pool(self, pool):
        self.blood_pool = pool

    def run(self, duration_min):
        steps = int(duration_min / self.step_size_min)
        for _ in range(steps):
            self.tick()

    def tick(self):
        blood_state = self.blood_pool.get_state()
        for agent in self.agents:
            agent._tick(self.time_min, self.step_size_min, blood_state)
        
        self.blood_pool.resolve_step(self.step_size_min)
        self.time_min += self.step_size_min
