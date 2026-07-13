from core.message_bus import MessageBus

class BaseAgent:
    def __init__(self, name: str, blood_pool, message_bus: MessageBus, tick_rate: int = 1):
        self.name = name
        self.blood_pool = blood_pool
        self.message_bus = message_bus
        self.tick_rate = tick_rate 
        self.ticks_since_update = 0
        
        self.message_bus.register_mailbox(name)

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        """
        Computes the agent's impact on the system for this tick.
        Must be implemented by subclasses.
        """
        raise NotImplementedError
        
    def _tick(self, current_time, step_size, blood_state):
        self.ticks_since_update += 1
        if self.ticks_since_update >= self.tick_rate:
            messages = self.message_bus.consume(self.name)
            actual_step = step_size * self.tick_rate
            self.calculate_delta(current_time, actual_step, blood_state, messages)
            self.ticks_since_update = 0
