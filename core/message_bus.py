from typing import List, Dict, Type, Any

class MessageBus:
    """
    In-memory типизированная шина сообщений (Message Bus) для общения агентов.
    Обеспечивает "zero-cost" коммуникацию без прямых ссылок агентов друг на друга.
    Использует паттерн Publish-Subscribe (Издатель-Подписчик).
    """
    def __init__(self):
        # Словарь подписок: Тип сообщения -> Список имен агентов-подписчиков
        self.subscribers: Dict[Type, List[str]] = {}
        # Почтовые ящики (очереди) для каждого агента: Имя агента -> Список сообщений
        self.mailboxes: Dict[str, List[Any]] = {}

    def subscribe(self, agent_name: str, msg_type: Type):
        """Подписывает агента на определенный класс сообщений."""
        if msg_type not in self.subscribers:
            self.subscribers[msg_type] = []
        if agent_name not in self.subscribers[msg_type]:
            self.subscribers[msg_type].append(agent_name)
            
    def register_mailbox(self, agent_name: str):
        """Создает пустой почтовый ящик для агента (если его еще нет)."""
        if agent_name not in self.mailboxes:
            self.mailboxes[agent_name] = []

    def publish(self, message: Any):
        """
        Публикует сообщение. Все агенты, подписанные на этот тип сообщения,
        получат его копию в свой почтовый ящик.
        """
        msg_type = type(message)
        if msg_type in self.subscribers:
            for agent_name in self.subscribers[msg_type]:
                self.mailboxes[agent_name].append(message)

    def consume(self, agent_name: str) -> List[Any]:
        """
        Извлекает все сообщения из почтового ящика агента и очищает его.
        Возвращает список полученных сообщений.
        """
        if agent_name in self.mailboxes:
            messages = self.mailboxes[agent_name].copy()
            self.mailboxes[agent_name].clear()
            return messages
        return []
