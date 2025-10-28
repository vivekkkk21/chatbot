import streamlit as st
import math
import pandas as pd


st.set_page_config(page_title="Air Flow Calculator", page_icon="💨", layout="centered")

st.title("🤖 Smart Chiller Air Flow Assistant")
st.write("👋 Hello! How can I help you today?")



# Session state initialization
if 'step' not in st.session_state:
    st.session_state.step = "start"
if 'equipment' not in st.session_state:
    st.session_state.equipment = None
if 'shape' not in st.session_state:
    st.session_state.shape = None
if 'unit' not in st.session_state:
    st.session_state.unit = None
if 'dimensions' not in st.session_state:
    st.session_state.dimensions = {}
if 'velocities' not in st.session_state:
    st.session_state.velocities = []
if 'vel_unit' not in st.session_state:
    st.session_state.vel_unit = None
if 'vel_count' not in st.session_state:
    st.session_state.vel_count = 0
if 'result' not in st.session_state:
    st.session_state.result = None


# Helper functions
def parse_velocities(input_text):
    return [float(v) for v in input_text.replace(',', ' ').split() if v.replace('.', '', 1).isdigit()]

def convert_length(value, from_unit):
    conv = {"m": 1, "cm": 0.01, "foot": 0.3048, "inches": 0.0254}
    return value * conv[from_unit]

def convert_velocity(value, from_unit):
    conv = {
        "m/s": 1, "cm/s": 0.01, "ft/s": 0.3048, "inch/s": 0.0254,
        "m/min": 1/60, "cm/min": 0.01/60, "ft/min": 0.3048/60, "inches/min": 0.0254/60
    }
    return value * conv[from_unit]

def calc_area(shape, dims_m):
    if shape == "Square":
        return dims_m['length'] * dims_m['breadth']
    elif shape == "Round":
        return math.pi * (dims_m['diameter'] / 2) ** 2

def calc_flow(vels_m, area_m2):
    avg_vel = sum(vels_m) / len(vels_m)
    flow = avg_vel * area_m2
    return avg_vel, flow


# ---------------------- STEP FLOW ----------------------
if st.session_state.step == "start":
    if st.button("🔹 Calculate Air Flow"):
        st.session_state.step = "choose_equipment"
        st.rerun()

elif st.session_state.step == "choose_equipment":
    st.write("For which equipment would you like to calculate flow?")
    equipment = st.radio("Select Equipment", ["Cooling Tower", "Ventilation Unit"], horizontal=True)
    if st.button("Next ➡️"):
        st.session_state.equipment = equipment
        st.session_state.step = "choose_shape"
        st.rerun()
    if st.button("⬅️ Go Back"):
        st.session_state.step = "start"
        st.rerun()

elif st.session_state.step == "choose_shape":
    st.write("Specify the surface dimension of measured area")
    shape = st.radio("Select Shape", ["Square", "Round"], horizontal=True)
    if st.button("Next ➡️"):
        st.session_state.shape = shape
        st.session_state.step = "choose_unit"
        st.rerun()
    if st.button("⬅️ Go Back"):
        st.session_state.step = "choose_equipment"
        st.rerun()

elif st.session_state.step == "choose_unit":
    st.write("Select the measurement unit for surface area:")
    unit = st.radio("Measurement Unit", ["m", "cm", "foot", "inches"], horizontal=True)
    if st.button("Next ➡️"):
        st.session_state.unit = unit
        st.session_state.step = "enter_dimensions"
        st.rerun()
    if st.button("⬅️ Go Back"):
        st.session_state.step = "choose_shape"
        st.rerun()

elif st.session_state.step == "enter_dimensions":
    shape = st.session_state.shape
    unit = st.session_state.unit
    if shape == "Square":
        length = st.number_input(f"Enter Length ({unit})", min_value=0.0, step=0.1)
        breadth = st.number_input(f"Enter Breadth ({unit})", min_value=0.0, step=0.1)
        if st.button("Next ➡️"):
            st.session_state.dimensions = {"length": length, "breadth": breadth}
            st.session_state.step = "enter_velocity_count"
            st.rerun()
    else:
        diameter = st.number_input(f"Enter Diameter ({unit})", min_value=0.0, step=0.1)
        if st.button("Next ➡️"):
            st.session_state.dimensions = {"diameter": diameter}
            st.session_state.step = "enter_velocity_count"
            st.rerun()

    if st.button("⬅️ Go Back"):
        st.session_state.step = "choose_unit"
        st.rerun()

elif st.session_state.step == "enter_velocity_count":
    count = st.number_input("Enter how many velocity readings you will provide (strict limit)", min_value=1, step=1)
    if st.button("Next ➡️"):
        st.session_state.vel_count = count
        st.session_state.step = "choose_velocity_unit"
        st.rerun()
    if st.button("⬅️ Go Back"):
        st.session_state.step = "enter_dimensions"
        st.rerun()

elif st.session_state.step == "choose_velocity_unit":
    st.write("Select the velocity unit:")
    vel_unit = st.radio("Velocity Unit", ["m/s", "cm/s", "ft/s", "inch/s", "m/min", "cm/min", "ft/min", "inches/min"], horizontal=False)
    if st.button("Next ➡️"):
        st.session_state.vel_unit = vel_unit
        st.session_state.velocities = []
        st.session_state.step = "enter_velocities"
        st.rerun()
    if st.button("⬅️ Go Back"):
        st.session_state.step = "enter_velocity_count"
        st.rerun()

elif st.session_state.step == "enter_velocities":
    vel_unit = st.session_state.vel_unit
    count = st.session_state.vel_count
    st.write(f"Enter {count} velocity readings in **{vel_unit}**:")
    next_idx = len(st.session_state.velocities) + 1
    if next_idx <= count:
        val = st.number_input(f"Velocity reading #{next_idx}", min_value=0.0, step=0.1)
        if st.button("Add Reading"):
            st.session_state.velocities.append(val)
            st.rerun()
    if len(st.session_state.velocities) == count:
        if st.button("Review ➡️"):
            st.session_state.step = "review_table"
            st.rerun()

    if st.button("⬅️ Go Back"):
        st.session_state.step = "choose_velocity_unit"
        st.rerun()

elif st.session_state.step == "review_table":
    st.write("Review your entered velocity readings (editable):")
    df = pd.DataFrame(st.session_state.velocities, columns=["Velocity"])
    edited_df = st.data_editor(df, num_rows="dynamic", key="vel_edit")
    st.session_state.velocities = edited_df["Velocity"].tolist()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("➕ Add Extra Reading"):
            st.session_state.velocities.append(0.0)
            st.rerun()
    with col2:
        if st.button("🔙 Go Back"):
            st.session_state.step = "enter_velocities"
            st.rerun()
    with col3:
        if st.button("🔁 Modify"):
            st.info("You can edit values directly above.")
    with col4:
        if st.button("✅ Proceed"):
            st.session_state.step = "result"
            st.rerun()

elif st.session_state.step == "result":
    dims_m = {k: convert_length(v, st.session_state.unit) for k, v in st.session_state.dimensions.items()}
    area_m2 = calc_area(st.session_state.shape, dims_m)
    vels_m = [convert_velocity(v, st.session_state.vel_unit) for v in st.session_state.velocities]
    avg_m, flow_m3s = calc_flow(vels_m, area_m2)

    st.success(f"""
    ✅ **Calculation Complete!**

    - Equipment: {st.session_state.equipment}  
    - Shape: {st.session_state.shape}  
    - Average Velocity: {avg_m:.3f} m/s  
    - Air Flow Rate: {flow_m3s:.4f} m³/s
    """)

    if st.button("🔄 Start New Calculation"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()






