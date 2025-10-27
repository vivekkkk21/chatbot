# app.py
import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Air Flow Chatbot", page_icon="💨", layout="centered")

# Conversion constants
LENGTH_TO_M = {"m": 1.0, "cm": 0.01, "ft": 0.3048, "inch": 0.0254}
VEL_UNITS = {
    "m/s": ("m", "s", 1.0),
    "cm/s": ("cm", "s", 0.01),
    "ft/s": ("ft", "s", 0.3048),
    "inch/s": ("inch", "s", 0.0254),
    "m/min": ("m", "min", 1.0 / 60.0),
    "cm/min": ("cm", "min", 0.01 / 60.0),
    "ft/min": ("ft", "min", 0.3048 / 60.0),
    "inch/min": ("inch", "min", 0.0254 / 60.0),
}
SEC_PER_TIME = {"s": 1.0, "min": 60.0}

# Session initialization
if "step" not in st.session_state:
    st.session_state.step = "greet"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "data" not in st.session_state:
    st.session_state.data = {
        "dia_unit": None,
        "diameter": None,
        "vel_unit": None,
        "expected_count": 0,
        "velocities": []
    }

# Utility functions
def to_meters(val, unit): return val * LENGTH_TO_M[unit]
def vel_to_mps(val, vel_unit): return val * VEL_UNITS[vel_unit][2]
def fmt(x): return f"{x:.2f}"
def flow_m3s(avg_vel_mps, dia_m): return math.pi * (dia_m / 2) ** 2 * avg_vel_mps
def flow_in_user_units(flow_m3s, l_unit, t_unit):
    return flow_m3s * SEC_PER_TIME[t_unit] / (LENGTH_TO_M[l_unit] ** 3)

def bot(msg):
    with st.chat_message("assistant"):
        st.markdown(msg)
def user(msg):
    with st.chat_message("user"):
        st.markdown(msg)

# Display previous chat history
for role, content in st.session_state.messages:
    with st.chat_message(role):
        st.markdown(content)

# Main flow
if st.session_state.step == "greet":
    msg = "👋 Hello! I’m your Air Flow Assistant. How can I help you today?"
    bot(msg)
    if st.button("🧮 Calculate Air Flow"):
        st.session_state.step = "dia_unit"
        st.session_state.messages.append(("assistant", msg))
        st.experimental_rerun()

elif st.session_state.step == "dia_unit":
    bot("Please select the **fan diameter unit**:")
    unit = st.radio("Choose unit:", ["m", "cm", "ft", "inch"], horizontal=True)
    if st.button("Next ➤"):
        st.session_state.data["dia_unit"] = unit
        st.session_state.messages.append(("assistant", f"Diameter unit selected: {unit}"))
        st.session_state.step = "enter_dia"
        st.experimental_rerun()
    if st.button("🔙 Back"):
        st.session_state.step = "greet"
        st.experimental_rerun()

elif st.session_state.step == "enter_dia":
    bot(f"Enter the fan diameter in **{st.session_state.data['dia_unit']}**.")
    dia = st.text_input("Fan Diameter:")
    if st.button("Next ➤"):
        try:
            st.session_state.data["diameter"] = float(dia)
            st.session_state.step = "vel_unit"
            st.experimental_rerun()
        except:
            st.warning("Enter a valid number.")
    if st.button("🔙 Back"):
        st.session_state.step = "dia_unit"
        st.experimental_rerun()

elif st.session_state.step == "vel_unit":
    bot("Select the **velocity unit**:")
    vunit = st.radio("Choose velocity unit:", list(VEL_UNITS.keys()))
    if st.button("Next ➤"):
        st.session_state.data["vel_unit"] = vunit
        st.session_state.step = "num_readings"
        st.experimental_rerun()
    if st.button("🔙 Back"):
        st.session_state.step = "enter_dia"
        st.experimental_rerun()

elif st.session_state.step == "num_readings":
    bot("How many velocity readings will you enter?")
    num = st.number_input("Enter number of readings:", min_value=1, step=1)
    if st.button("Confirm ➤"):
        st.session_state.data["expected_count"] = int(num)
        st.session_state.data["velocities"] = []
        st.session_state.step = "vel_entries"
        st.experimental_rerun()
    if st.button("🔙 Back"):
        st.session_state.step = "vel_unit"
        st.experimental_rerun()

elif st.session_state.step == "vel_entries":
    count = len(st.session_state.data["velocities"])
    total = st.session_state.data["expected_count"]
    bot(f"Enter reading {count+1} of {total} in {st.session_state.data['vel_unit']}.")
    val = st.text_input(f"Velocity {count+1}:", key=f"v_{count}")
    if st.button("Add ➕"):
        try:
            st.session_state.data["velocities"].append(float(val))
            if len(st.session_state.data["velocities"]) == total:
                st.session_state.step = "review"
            st.experimental_rerun()
        except:
            st.warning("Invalid number.")
    if st.button("🔙 Back"):
        st.session_state.step = "num_readings"
        st.experimental_rerun()

elif st.session_state.step == "review":
    bot("Here are your velocity readings:")
    df = pd.DataFrame({
        "Index": list(range(1, len(st.session_state.data["velocities"]) + 1)),
        "Velocity": [fmt(v) for v in st.session_state.data["velocities"]],
        "Unit": [st.session_state.data["vel_unit"]] * len(st.session_state.data["velocities"])
    })
    st.table(df)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ Proceed"):
            st.session_state.step = "result"
            st.experimental_rerun()
    with col2:
        if st.button("✏️ Modify"):
            st.session_state.step = "vel_entries"
            st.experimental_rerun()
    with col3:
        if st.button("🔙 Back"):
            st.session_state.step = "vel_entries"
            st.experimental_rerun()

elif st.session_state.step == "result":
    d = st.session_state.data
    dia_m = to_meters(d["diameter"], d["dia_unit"])
    vel_mps = [vel_to_mps(v, d["vel_unit"]) for v in d["velocities"]]
    avg_v = sum(vel_mps) / len(vel_mps)
    flow_m3 = flow_m3s(avg_v, dia_m)
    l_unit, t_unit = VEL_UNITS[d["vel_unit"]][:2]
    flow_user = flow_in_user_units(flow_m3, l_unit, t_unit)

    bot(f"📊 **Results:**\n\n"
        f"- Average Velocity: **{fmt(avg_v)} m/s**\n"
        f"- Air Flow: **{fmt(flow_m3)} m³/s**\n"
        f"- Air Flow (in your unit): **{fmt(flow_user)} {l_unit}³/{t_unit}**")
    if st.button("🔁 New Calculation"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.experimental_rerun()
