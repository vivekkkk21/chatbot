import streamlit as st
import math

# ---------------------------------------------------------------------
# 💡 Compatibility fix for Streamlit rerun (new/old versions)
if not hasattr(st, "rerun"):
    st.rerun = st.experimental_rerun
# ---------------------------------------------------------------------

st.set_page_config(page_title="Chiller Air Flow Assistant", page_icon="💨", layout="centered")

# Initialize session state
if "step" not in st.session_state:
    st.session_state.step = "greeting"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "data" not in st.session_state:
    st.session_state.data = {
        "dia_unit": None,
        "velocity_unit": None,
        "diameter": None,
        "num_readings": None,
        "velocities": [],
    }

# ---------------------------------------------------------------------
# 💬 Helper function for chat bubble styling
def chat_message(role, text):
    if role == "user":
        st.markdown(
            f"""
            <div style='text-align:right; margin:8px 0;'>
                <div style='display:inline-block; background:#DCF8C6; padding:10px 14px;
                border-radius:15px; max-width:80%; word-wrap:break-word; font-size:16px;'>
                    👷‍♂️ {text}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style='text-align:left; margin:8px 0;'>
                <div style='display:inline-block; background:#F1F0F0; padding:10px 14px;
                border-radius:15px; max-width:80%; word-wrap:break-word; font-size:16px;'>
                    🤖 {text}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

def bot(msg):
    st.session_state.messages.append(("assistant", msg))
    chat_message("assistant", msg)

def user(msg):
    st.session_state.messages.append(("user", msg))
    chat_message("user", msg)
# ---------------------------------------------------------------------

# Display chat history
for sender, msg in st.session_state.messages:
    chat_message(sender, msg)

# ---------------------------------------------------------------------
# Step 1: Greeting
if st.session_state.step == "greeting":
    msg = "Hello 👋, how can I help you today?"
    bot(msg)
    if st.button("🧮 Calculate Air Flow"):
        st.session_state.step = "dia_unit"
        st.session_state.messages.append(("assistant", msg))
        st.rerun()

# ---------------------------------------------------------------------
# Step 2: Select diameter unit
elif st.session_state.step == "dia_unit":
    bot("Please select the **fan diameter unit**:")
    cols = st.columns(4)
    dia_units = ["m", "cm", "ft", "inches"]
    for i, u in enumerate(dia_units):
        if cols[i].button(u):
            st.session_state.data["dia_unit"] = u
            st.session_state.step = "enter_diameter"
            st.rerun()

# ---------------------------------------------------------------------
# Step 3: Enter diameter
elif st.session_state.step == "enter_diameter":
    bot(f"Enter the fan diameter in {st.session_state.data['dia_unit']}:")
    diameter = st.text_input("Fan Diameter:")
    if diameter:
        try:
            st.session_state.data["diameter"] = float(diameter)
            st.session_state.step = "vel_unit"
            st.rerun()
        except:
            bot("⚠️ Please enter a valid numeric value.")

# ---------------------------------------------------------------------
# Step 4: Select velocity unit
elif st.session_state.step == "vel_unit":
    bot("Please select the **velocity measurement unit**:")
    cols = st.columns(4)
    vel_units = ["m/s", "cm/s", "ft/s", "inches/s", "m/min", "cm/min", "ft/min", "inches/min"]
    for i, u in enumerate(vel_units[:4]):
        if cols[i].button(u):
            st.session_state.data["velocity_unit"] = u
            st.session_state.step = "num_readings"
            st.rerun()
    cols2 = st.columns(4)
    for i, u in enumerate(vel_units[4:]):
        if cols2[i].button(u):
            st.session_state.data["velocity_unit"] = u
            st.session_state.step = "num_readings"
            st.rerun()

# ---------------------------------------------------------------------
# Step 5: Number of readings
elif st.session_state.step == "num_readings":
    bot("How many velocity readings will you enter?")
    num = st.text_input("Enter number of readings:")
    if num:
        try:
            val = int(num)
            if val > 0:
                st.session_state.data["num_readings"] = val
                st.session_state.data["velocities"] = []
                st.session_state.step = "enter_velocities"
                st.rerun()
            else:
                bot("⚠️ Please enter a positive number.")
        except:
            bot("⚠️ Please enter an integer value.")

# ---------------------------------------------------------------------
# Step 6: Enter velocities one by one
elif st.session_state.step == "enter_velocities":
    entered = len(st.session_state.data["velocities"])
    total = st.session_state.data["num_readings"]
    bot(f"Enter velocity reading {entered + 1} of {total} ({st.session_state.data['velocity_unit']}):")
    vel = st.text_input("Velocity Value:")
    col1, col2 = st.columns(2)
    if col1.button("Submit Velocity"):
        if vel:
            try:
                val = float(vel)
                st.session_state.data["velocities"].append(val)
                if len(st.session_state.data["velocities"]) == total:
                    st.session_state.step = "review"
                st.rerun()
            except:
                bot("⚠️ Please enter a valid numeric value.")
    if col2.button("🔙 Go Back"):
        if entered > 0:
            st.session_state.data["velocities"].pop()
            st.rerun()

# ---------------------------------------------------------------------
# Step 7: Review & Modify
elif st.session_state.step == "review":
    bot("Here are your entered velocity readings:")
    velocities = st.session_state.data["velocities"]
    st.table({"Reading No.": list(range(1, len(velocities)+1)), "Velocity": velocities})

    col1, col2, col3 = st.columns(3)
    if col1.button("✅ Proceed"):
        st.session_state.step = "calculate"
        st.rerun()
    if col2.button("✏️ Modify Readings"):
        st.session_state.step = "enter_velocities"
        st.rerun()
    if col3.button("🔙 Go Back"):
        st.session_state.step = "num_readings"
        st.rerun()

# ---------------------------------------------------------------------
# Step 8: Calculate & Show Results
elif st.session_state.step == "calculate":
    data = st.session_state.data
    avg_velocity = sum(data["velocities"]) / len(data["velocities"])
    dia = data["diameter"]

    # Convert diameter to meters
    unit_conv = {"m": 1, "cm": 0.01, "ft": 0.3048, "inches": 0.0254}
    dia_m = dia * unit_conv[data["dia_unit"]]
    area = math.pi * (dia_m / 2) ** 2

    # Convert velocity to m/s
    vel_conv = {
        "m/s": 1, "cm/s": 0.01, "ft/s": 0.3048, "inches/s": 0.0254,
        "m/min": 1 / 60, "cm/min": 0.01 / 60, "ft/min": 0.3048 / 60, "inches/min": 0.0254 / 60,
    }
    avg_vel_m_s = avg_velocity * vel_conv[data["velocity_unit"]]
    flow_m3_s = avg_vel_m_s * area

    bot(f"**Average Velocity:** {avg_velocity:.2f} {data['velocity_unit']}")
    bot(f"**Fan Area:** {area:.2f} m²")
    bot(f"**Calculated Air Flow:** {flow_m3_s:.2f} m³/s")

    # Convert back to user's original velocity unit (if possible)
    flow_in_original_unit = flow_m3_s / vel_conv[data["velocity_unit"]]
    bot(f"**Equivalent Air Flow:** {flow_in_original_unit:.2f} (based on {data['velocity_unit']})")

    if st.button("🔁 Start Over"):
        for key in ["step", "messages", "data"]:
            del st.session_state[key]
        st.rerun()
