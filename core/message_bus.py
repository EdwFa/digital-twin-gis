from typing import List, Dict, Type, Any

class MessageBus:
    """In-memory typed message bus for zero-cost internal communication."""
    def __init__(self):
        self.subscribers: Dict[Type, List[str]] = {}
        self.mailboxes: Dict[str, List[Any]] = {}

    def subscribe(self, agent_name: str, msg_type: Type):
        if msg_type not in self.subscribers:
            self.subscribers[msg_type] = []
        if agent_name not in self.subscribers[msg_type]:
            self.subscribers[msg_type].append(agent_name)
            
    def register_mailbox(self, agent_name: str):
        if agent_name not in self.mailboxes:
            self.mailboxes[agent_name] = []

    def publish(self, message: Any):
        msg_type = type(message)
        if msg_type in self.subscribers:
            for agent_name in self.subscribers[msg_type]:
                self.mailboxes[agent_name].append(message)

    def consume(self, agent_name: str) -> List[Any]:
        if agent_name in self.mailboxes:
            messages = self.mailboxes[agent_name].copy()
            self.mailboxes[agent_name].clear()
            return messages
        return []
