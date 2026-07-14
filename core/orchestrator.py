from models.events import MealEvent, DrugEvent, SleepEvent
from models.messages import PortalVeinInflowMsg, DrugAdministrationMsg, AdaptationMsg

class SimulationOrchestrator:
    """
    Стратегический Оркестратор (Уровень 0).
    Управляет Timeline пациента, рассылает события (еда, сон, таблетки) в нужную минуту
    и продвигает симуляционный движок.
    """
    def __init__(self, engine):
        self.engine = engine
        self.timeline = [] # Список событий (Event)
        self.history = [] # Запись состояния крови на каждом шаге

    def schedule_event(self, event):
        """Добавляет событие в расписание"""
        self.timeline.append(event)
        # Сортируем по времени (в будущем можно использовать PriorityQueue)
        self.timeline.sort(key=lambda x: x.time_minutes)

    def run_until(self, target_time_minutes):
        """Крутит симуляцию до указанного времени, активируя события по пути."""
        while self.engine.time_min < target_time_minutes:
            current_time = self.engine.time_min
            
            # Извлекаем все события, которые должны произойти в эту минуту
            # Так как float может иметь погрешности, берем небольшой эпсилон
            events_now = [e for e in self.timeline if abs(e.time_minutes - current_time) < (self.engine.step_size_min / 2)]
            
            for event in events_now:
                self._dispatch_event(event)
                self.timeline.remove(event)
                
            # Делаем один шаг симуляции
            self.engine.tick()
            
            # Сохраняем снимок состояния (каждые 5 минут для экономии памяти)
            if int(self.engine.time_min) % 5 == 0:
                self.history.append(self.engine.blood_pool.get_state())

    def _dispatch_event(self, event):
        """Транслирует событие из Timeline в сообщение для MessageBus"""
        print(f"[Таймлайн {self.engine.time_min:.0f} мин] Событие: {event.description}")
        
        if isinstance(event, MealEvent):
            from models.messages import MealIntakeMsg
            msg = MealIntakeMsg(
                carbs_g=event.carbs_g,
                meal_duration_min=20.0 
            )
            self.engine.message_bus.publish(msg)
            
        elif isinstance(event, DrugEvent):
            if event.is_oral:
                # Временно: оркестратор сам добавляет лекарство в системный кровоток
                # Объем распределения крови ~16.0 л. 
                concentration = event.dose_mg / 16.0
                current_conc = self.engine.blood_pool.concentrations.get(event.substance, 0.0)
                self.engine.blood_pool.concentrations[event.substance] = current_conc + concentration
            else:
                msg = DrugAdministrationMsg(
                    substance=event.substance,
                    dose_mg=event.dose_mg,
                    route="IV"
                )
                self.engine.message_bus.publish(msg)
            
        elif isinstance(event, SleepEvent):
            # Во время сна повышаем чувствительность к инсулину
            msg_sleep_start = AdaptationMsg(
                beta_mass_multiplier=1.0,
                insulin_sensitivity_multiplier=1.2
            )
            self.engine.message_bus.publish(msg_sleep_start)
            
            # Планируем пробуждение (возврат к норме)
            wake_up_time = event.time_minutes + event.duration_minutes
            # Добавим скрытое событие пробуждения
            from models.events import Event
            wake_up_event = Event(
                time_minutes=wake_up_time, 
                description="Пробуждение (Конец сна)"
            )
            
            # Патчим метод _dispatch_event для обработки этого скрытого события
            def wake_up_action(self=self):
                msg_wake = AdaptationMsg(
                    beta_mass_multiplier=1.0,
                    insulin_sensitivity_multiplier=1.0
                )
                self.engine.message_bus.publish(msg_wake)
            wake_up_event.action = wake_up_action
            self.schedule_event(wake_up_event)
            
        elif hasattr(event, 'action'):
            event.action()
