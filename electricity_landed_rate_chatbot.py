import streamlit as st
import pandas as pd
from typing import List, Tuple

# -----------------------------
# Default Constants
# -----------------------------
DEFAULT_CONSTANTS = {
    "Parameter": ["DC_rate", "FAC_rate", "ToS_rate", "ED_percent"],
    "Description": [
        "Demand charge rate (₹ per kVA)",
        "Fuel Adjustment Charge (₹ per kVAh)",
        "Tax on Sale rate (₹ per kWh)",
        "Electricity Duty (percentage %)"
    ],
    "Value": [600.0, 0.5, 0.18, 7.5],
}

# -----------------------------
# Embedded tariff keys
# -----------------------------
TARIFF_KEYS = ["January","February","March","April","May","June","July","August",
               "September","October","November","December"]
Years = [str(y) for y in range(2020, 2047)]

# -----------------------------
# Fixed Old ToD Ratios & Old slab timings
# -----------------------------
OLD_TOD_RATIOS = {"A": 33.541412, "B": 34.476496, "C": 6.837052, "D": 25.14506}
OLD_SLAB_TIMINGS = {
    "A": [("22:00", "06:00")],
    "B": [("06:00", "09:00"), ("12:00", "18:00")],
    "C": [("09:00", "12:00")],
    "D": [("18:00", "22:00")],
}

# -----------------------------
# Page config + title
# -----------------------------
st.set_page_config(page_title="Electricity Landed Unit Rate Calculator", page_icon="⚡", layout="wide")
st.title("⚡ Electricity Landed Unit Rate Calculator")
st.markdown("### 👋 Use the form to compute Landed Unit Rate. Constants on the right are editable and reset on reload.")

# -----------------------------
# Layout
# -----------------------------
left_col, right_col = st.columns([2.2, 1])

# -----------------------------
# Editable Constants
# -----------------------------
with right_col:
    st.header("🔧 Constants (editable)")
    const_df = pd.DataFrame(DEFAULT_CONSTANTS)
    edited = st.data_editor(const_df, num_rows="fixed", use_container_width=True, key="constants_editor")

    DC_rate = float(edited.loc[0, "Value"])
    FAC_rate = float(edited.loc[1, "Value"])
    ToS_rate = float(edited.loc[2, "Value"])
    ED_percent = float(edited.loc[3, "Value"])

# -----------------------------
# Helper Functions
# -----------------------------
def parse_time(t: str) -> float:
    hh, mm = t.split(":")
    return int(hh) + int(mm) / 60.0

def parse_range(r: str) -> Tuple[float, float]:
    a, b = r.split("-")
    return parse_time(a.strip()), parse_time(b.strip())

def split_range_if_wrap(start: float, end: float):
    return [(start, end)] if start < end else [(start, 24.0), (0.0, end)]

def overlap_between_segments(seg1, seg2):
    s1, e1 = seg1; s2, e2 = seg2
    start = max(s1, s2); end = min(e1, e2)
    return max(0.0, end - start)

def total_overlap_hours(range1, range2):
    segs1 = split_range_if_wrap(*range1)
    segs2 = split_range_if_wrap(*range2)
    return sum(overlap_between_segments(a, b) for a in segs1 for b in segs2)

# -----------------------------
# Left Column
# -----------------------------
with left_col:
    st.header("1️⃣ Inputs")
    col1, col2 = st.columns(2)
    with col1:
        month = st.selectbox("Select Month", TARIFF_KEYS)
        max_demand_kva = st.number_input("Maximum demand (kVA)", min_value=0.0, value=13500.0)
    with col2:
        year = st.selectbox("Select Year", Years)
        units_kvah = st.number_input("Total energy (kVAh)", min_value=0.0, value=500000.0)

    st.markdown("---")
    st.header("2️⃣ New Slab Timings")
    with st.expander("🔁 Edit New Slab Timings"):
        new_A_range = st.text_input("New Slab A", "00:00-06:00")
        new_B_range = st.text_input("New Slab B", "06:00-09:00")
        new_C_range = st.text_input("New Slab C", "09:00-17:00")
        new_D_range = st.text_input("New Slab D", "17:00-00:00")

    st.markdown("---")
    st.header("3️⃣ ToD Multipliers (%)")
    mcol1, mcol2 = st.columns(2)
    with mcol1:
        tod_A = st.number_input("Multiplier A", value=0.0)
        tod_B = st.number_input("Multiplier B", value=0.0)
    with mcol2:
        tod_C = st.number_input("Multiplier C", value=-2.17)
        tod_D = st.number_input("Multiplier D", value=2.17)

    st.markdown("---")
    new_energy_rate = st.number_input("Energy Rate (₹/kVAh)", min_value=0.0, value=8.68)
    calculate = st.button("🚀 Calculate Landed Unit Rate")

    if calculate:
        # Core Calculations
        DC = max_demand_kva * DC_rate
        EC = units_kvah * new_energy_rate
        FAC = units_kvah * FAC_rate

        # Old Units
        OldUnits = {k: units_kvah * (v / 100.0) for k, v in OLD_TOD_RATIOS.items()}
        new_ranges = {"A": parse_range(new_A_range), "B": parse_range(new_B_range),
                      "C": parse_range(new_C_range), "D": parse_range(new_D_range)}

        old_durations = {}
        for k, segs in OLD_SLAB_TIMINGS.items():
            dur = 0
            for s, e in segs:
                s, e = parse_range(f"{s}-{e}")
                dur += e - s if s < e else (24 - s) + e
            old_durations[k] = dur

        NewUnits = {k: 0 for k in new_ranges}
        for old_k, segs in OLD_SLAB_TIMINGS.items():
            old_total = old_durations[old_k]
            for s, e in segs:
                s, e = parse_range(f"{s}-{e}")
                for new_k, nrange in new_ranges.items():
                    overlap = total_overlap_hours((s, e), nrange)
                    if overlap > 0 and old_total > 0:
                        NewUnits[new_k] += OldUnits[old_k] * (overlap / old_total)

        ToD_A = NewUnits["A"] * tod_A
        ToD_B = NewUnits["B"] * tod_B
        ToD_C = NewUnits["C"] * tod_C
        ToD_D = NewUnits["D"] * tod_D
        ToD_charge = ToD_A + ToD_B + ToD_C + ToD_D

        ED = (ED_percent / 100) * (DC + EC + FAC + ToD_charge)
        ToS = (units_kvah * 0.997) * ToS_rate
        Total = DC + EC + FAC + ToD_charge + ED + ToS
        LandedRate = Total / (units_kvah * 0.997)

        st.success(f"✅ Landed Unit Rate = ₹{LandedRate:,.4f}/kWh")

        # -----------------------------
        # Tables
        # -----------------------------
        st.markdown("### 📊 ToD: New Slab Units & Charges (from Old ratios & overlaps)")
        tod_table = pd.DataFrame({
            "New Slab": ["A","B","C","D"],
            "New Range": [new_A_range,new_B_range,new_C_range,new_D_range],
            "Units (kVAh)": [NewUnits["A"],NewUnits["B"],NewUnits["C"],NewUnits["D"]],
            "Multiplier (%)": [tod_A,tod_B,tod_C,tod_D],
            "Charge (₹)": [ToD_A,ToD_B,ToD_C,ToD_D]
        })
        st.table(tod_table)

        st.markdown("### 💰 Detailed Cost Breakdown")
        breakdown_df = pd.DataFrame({
            "Component": [
                "Demand Charge (DC)","Energy Charge (EC)","ToD Charge","Fuel Adj. Charge (FAC)",
                "Electricity Duty (ED)","Tax on Sale (ToS)","Total"
            ],
            "Value (₹)": [DC, EC, ToD_charge, FAC, ED, ToS, Total]
        })
        st.table(breakdown_df)

        # -----------------------------
        # Export Button
        # -----------------------------
        export_df = pd.concat({"ToD_Table": tod_table, "Detailed_Breakdown": breakdown_df}, axis=1)
        csv_data = export_df.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Export to CSV", csv_data, file_name="ToD_and_Detailed_Breakdown.csv", mime="text/csv")
