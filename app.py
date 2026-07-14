import streamlit as st
import pandas as pd
import sys
import os

# Ensure the local modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.engine import SimulationEngine
from core.blood_pool import BloodPool
from models.messages import MealIntakeMsg
from models.passport import PatientPassport_GIS
from agents.gis_super_agent import GISSuperAgent
from agents.pancreas import PancreasAgent
from agents.liver_pbpk import LiverPBPKSuperAgent
from agents.muscle import MuscleAgent
from agents.brain import BrainAgent
from agents.gut import GutAgent
from agents.adipose import AdiposeAgent
from agents.kidney import KidneyAgent
from agents.slow_adaptation import SlowAdaptationAgent

st.set_page_config(page_title="Digital Twin: Glucose-Insulin", layout="wide")

st.title("🫀 Digital Twin: Glucose-Insulin System MVP")
st.markdown("Interactive simulation of the Level 1 super-agent for glucose homeostasis.")

st.sidebar.header("📋 Patient Passport")

# Sidebar inputs
age = st.sidebar.slider("Age", 18, 90, 30)
sex = st.sidebar.selectbox("Sex", ['M', 'F'])
weight = st.sidebar.number_input("Weight (kg)", 40.0, 150.0, 75.0)
height = st.sidebar.number_input("Height (cm)", 140.0, 220.0, 180.0)
f_gluc = st.sidebar.number_input("Fasting Glucose (mmol/L)", 3.0, 15.0, 5.0, step=0.1)
f_ins = st.sidebar.number_input("Fasting Insulin (pmol/L)", 10.0, 300.0, 60.0, step=5.0)
hba1c = st.sidebar.number_input("HbA1c (%)", 4.0, 12.0, 5.0, step=0.1)

st.sidebar.header("🍽️ Scenario Parameters")
carbs_g = st.sidebar.number_input("Carbohydrates (g) for OGTT", 0.0, 150.0, 75.0, step=5.0)
sim_time = st.sidebar.slider("Simulation Time (min)", 60, 360, 240, step=30)

passport = PatientPassport_GIS(
    age=age, sex=sex, weight_kg=weight, height_cm=height,
    fasting_glucose_mmol_L=f_gluc, fasting_insulin_pmol_L=f_ins, HbA1c_percent=hba1c
)

col1, col2, col3 = st.columns(3)
bmi = weight / ((height/100)**2)
ins_mU_L = f_ins / 6.0
homa_ir = (f_gluc * ins_mU_L) / 22.5

col1.metric("BMI", f"{bmi:.1f}")
col2.metric("HOMA-IR", f"{homa_ir:.2f}", "Normal < 2" if homa_ir < 2 else "Insulin Resistance", delta_color="inverse")
col3.metric("HbA1c Status", f"{hba1c}%", "T2D range" if hba1c >= 6.5 else "Healthy", delta_color="inverse")

if st.button("▶️ Run Simulation", use_container_width=True, type="primary"):
    with st.spinner("Simulating..."):
        engine = SimulationEngine(step_size_min=1.0)
        blood = BloodPool()
        msg_bus = engine.message_bus
        
        gis = GISSuperAgent(blood, msg_bus)
        gis.add_subagent(GutAgent(blood, msg_bus))
        gis.add_subagent(PancreasAgent(blood, msg_bus))
        gis.add_subagent(LiverPBPKSuperAgent(blood, msg_bus))
        gis.add_subagent(MuscleAgent(blood, msg_bus))
        gis.add_subagent(BrainAgent(blood, msg_bus))
        gis.add_subagent(AdiposeAgent(blood, msg_bus))
        gis.add_subagent(KidneyAgent(blood, msg_bus))
        gis.add_subagent(SlowAdaptationAgent(blood, msg_bus))
        
        gis.calibrate(passport)
        
        engine.set_blood_pool(blood)
        engine.add_agent(gis)
        
        history = []
        
        def record_state():
            history.append({
                "Time (min)": engine.time_min,
                "Glucose (mmol/L)": blood.glucose,
                "Insulin (pmol/L)": blood.insulin
            })
            
        # Fasting phase (60 min)
        for _ in range(60):
            engine.run(1.0)
            record_state()
            
        # Meal
        if carbs_g > 0:
            msg_bus.publish(MealIntakeMsg(carbs_g=carbs_g))
            
        # Postprandial phase
        for _ in range(sim_time):
            engine.run(1.0)
            record_state()
            
        df = pd.DataFrame(history)
        
        # Plot with plotly
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_trace(
            go.Scatter(x=df["Time (min)"], y=df["Glucose (mmol/L)"], name="Glucose (mmol/L)", line=dict(color='#ff4b4b', width=3)),
            secondary_y=False,
        )
        
        fig.add_trace(
            go.Scatter(x=df["Time (min)"], y=df["Insulin (pmol/L)"], name="Insulin (pmol/L)", line=dict(color='#0068c9', width=3, dash='dot')),
            secondary_y=True,
        )
        
        fig.update_layout(
            title_text="Glucose-Insulin Dynamics (OGTT Scenario)",
            hovermode="x unified"
        )
        
        fig.update_xaxes(title_text="Time (min)")
        fig.update_yaxes(title_text="Glucose (mmol/L)", secondary_y=False, color="#ff4b4b")
        fig.update_yaxes(title_text="Insulin (pmol/L)", secondary_y=True, color="#0068c9")
        
        # Add meal vertical line
        if carbs_g > 0:
            fig.add_vline(x=60, line_dash="dash", line_color="green", annotation_text=f"Meal ({carbs_g}g)")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show peak stats
        peak_g = df["Glucose (mmol/L)"].max()
        peak_time = df.loc[df["Glucose (mmol/L)"].idxmax(), "Time (min)"] - 60 # time since meal
        
        st.success(f"**Simulation Complete!** Peak Glucose: {peak_g:.2f} mmol/L at {peak_time:.0f} mins post-meal.")
