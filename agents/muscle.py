from .base import BaseAgent

class MuscleAgent(BaseAgent):
    def __init__(self, blood_pool, message_bus):
        super().__init__("Muscle", blood_pool, message_bus)
        # Parameters from spec
        self.S_I = 5.0e-4 # dL/pmol/min (insulin sensitivity)
        self.alpha = 0.01 
        self.exercise_factor = 0.0

    def calculate_delta(self, current_time, step_size, blood_state, messages):
        g = blood_state["glucose"]
        i = blood_state["insulin"]
        
        # U_muscle = (S_I * I * G / (1 + alpha * I)) + (exercise_factor * G)
        insulin_uptake = (self.S_I * i * g) / (1.0 + self.alpha * i)
        exercise_uptake = self.exercise_factor * g
        
        total_uptake = insulin_uptake + exercise_uptake
        
        self.blood_pool.add_glucose_delta(-total_uptake)
