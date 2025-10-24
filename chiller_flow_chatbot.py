import streamlit as st
import math

st.set_page_config(page_title="Chiller Air Flow Chatbot", page_icon="💨", layout="centered")

st.title("💬 Smart Chiller Flow Assistant")
st.write("👋 Hello! How can I help you today?")

# Session state
if 'step' not in st.session_state:
    st.session_state.step = "start"
if 'velocities' not in st.session_state:
    st.session_state.velocities = []
if 'vel_unit' not in st.session_state:
    st.session_state.vel_unit = None
if 'diameter' not in st.session_state:
    st.session_state.diameter = None
if 'dia_unit' not in st.session_state:
    st.session_state.dia_unit = None

# Helper functions
def parse_velocities(input_text):
    return [float(v) for v in input_text.replace(',', ' ').split() if v.replace('.', '', 1).isdigit()]

def calc_flow(vels, dia):
    avg = sum(vels) / len(vels)
    area = math.pi * (dia / 2) ** 2
    flow = avg * area
    return avg, flow

def convert_unit(value, from_unit):
    conv = {"m/s": 1, "ft/s": 0.3048, "inch/s": 0.0254, "m": 1, "ft": 0.3048, "inch": 0.0254}
    return value * conv[from_unit]

# Chat logic
if st.session_state.step == "start":
    if st.button("🔹 Calculate Air Flow"):
        st.session_state.step = "choose_vel_unit"
        st.rerun()

elif st.session_state.step == "choose_vel_unit":
    st.write("Please select the **velocity unit**:")
    unit = st.radio("Velocity Unit", ["m/s", "ft/s", "inch/s"], horizontal=True)
    if st.button("Next ➡️"):
        st.session_state.vel_unit = unit
        st.session_state.step = "enter_velocities"
        st.rerun()

elif st.session_state.step == "enter_velocities":
    st.write(f"Enter velocity readings in **{st.session_state.vel_unit}**. Type one per line or all separated by commas.")
    vel_input = st.text_area("Velocity Input")
    if st.button("Add Values"):
        vels = parse_velocities(vel_input)
        if vels:
            st.session_state.velocities.extend(vels)
            st.success(f"✅ Recorded {len(vels)} velocities. Total: {len(st.session_state.velocities)}")
        else:
            st.warning("⚠️ No valid numeric values found.")
    if st.button("DONE ✅"):
        if len(st.session_state.velocities) == 0:
            st.warning("Please enter at least one velocity before proceeding.")
        else:
            st.session_state.step = "enter_diameter"
            st.rerun()

elif st.session_state.step == "enter_diameter":
    st.write("Now enter the **fan diameter** value:")
    dia = st.number_input("Fan Diameter", min_value=0.0, step=0.1)
    dia_unit = st.radio("Select Diameter Unit", ["m", "ft", "inch"], horizontal=True)
    if st.button("Calculate Flow 💨"):
        st.session_state.diameter = dia
        st.session_state.dia_unit = dia_unit

        # Conversion
        vel_m = [convert_unit(v, st.session_state.vel_unit) for v in st.session_state.velocities]
        dia_m = convert_unit(dia, dia_unit)
        avg, flow = calc_flow(vel_m, dia_m)

        st.session_state.step = "result"
        st.session_state.result = (avg, dia_m, flow)
        st.rerun()

elif st.session_state.step == "result":
    avg, dia_m, flow = st.session_state.result
    st.success(f"""
    ✅ **Calculation Complete!**

    - Average Velocity: {avg:.3f} m/s  
    - Fan Diameter: {dia_m:.3f} m  
    - Air Flow Rate: {flow:.4f} m³/s
    """)
    if st.button("🔄 Start New Calculation"):
        for key in ['step','velocities','vel_unit','diameter','dia_unit','result']:
            if key in st.session_state: del st.session_state[key]
        st.rerun()
