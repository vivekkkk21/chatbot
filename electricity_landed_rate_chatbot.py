import streamlit as st
import pandas as pd
from typing import List, Tuple

# -----------------------------
# Default Constants (reset on reload)
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
# Month and Year dropdowns
# -----------------------------
TARIFF_KEYS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
Years = [str(y) for y in range(2020, 2047)]

# -----------------------------
# Old ToD Ratios & Old Slab Timings
# -----------------------------
OLD_TOD_RATIOS = {"A": 33.541412, "B": 34.476496, "C": 6.837052, "D": 25.14506}
OLD_SLAB_TIMINGS = {
    "A": [("22:00", "06:00")],
    "B": [("06:00", "09:00"), ("12:00", "18:00")],
    "C": [("09:00", "12:00")],
    "D": [("18:00", "22:00")],
}

# -----------------------------
# Streamlit setup
# -----------------------------
st.set_page_config(page_title="Electricity Landed Unit Rate Calculator", page_icon="⚡", layout="wide")
st.title("⚡ Electricity Landed Unit Rate Calculator")
st.markdown("### Calculate landed unit rate using new ToD slabs and overlap logic.")

# Layout: two sections
left_col, right_col = st.columns([2.2, 1])

# -----------------------------
# Constants (Right side)
# -----------------------------
with right_col:
    st.header("🔧 Constants (editable)")
    const_df = pd.DataFrame(DEFAULT_CONSTANTS)
    edited = st.data_editor(const_df, num_rows="fixed", use_container_width=True, key="constants_editor")

    DC_rate = float(edited.loc[edited["Parameter"] == "DC_rate", "Value"].values[0])
    FAC_rate = float(edited.loc[edited["Parameter"] == "FAC_rate", "Value"].values[0])
    ToS_rate = float(edited.loc[edited["Parameter"] == "ToS_rate", "Value"].values[0])
    ED_percent = float(edited.loc[edited["Parameter"] == "ED_percent", "Value"].values[0])

# -----------------------------
# Helper Functions
# -----------------------------
def parse_time(t: str) -> float:
    hh, mm = t.split(":")
    return int(hh) + int(mm) / 60.0

def split_range_if_wrap(start: float, end: float) -> List[Tuple[float, float]]:
    return [(start, end)] if start < end else [(start, 24.0), (0.0, end)]

def overlap_between_segments(seg1: Tuple[float, float], seg2: Tuple[float, float]) -> float:
    s1, e1 = seg1
    s2, e2 = seg2
    return max(0.0, min(e1, e2) - max(s1, s2))

def total_overlap_hours(old_segments: List[Tuple[float, float]], new_segments: List[Tuple[float, float]]) -> float:
    total = 0.0
    for a in old_segments:
        for b in new_segments:
            total += overlap_between_segments(a, b)
    return total

def parse_multiple_ranges(ranges_str: str) -> List[Tuple[float, float]]:
    """Handle single or multiple comma-separated time ranges."""
    ranges = []
    for r in ranges_str.split(","):
        r = r.strip()
        if not r:
            continue
        a, b = r.split("-")
        start, end = parse_time(a.strip()), parse_time(b.strip())
        ranges.extend(split_range_if_wrap(start, end))
    return ranges

# -----------------------------
# Inputs (Left side)
# -----------------------------
with left_col:
    st.header("1️⃣ Input Details")
    col1, col2 = st.columns(2)
    with col1:
        month = st.selectbox("Month", TARIFF_KEYS)
        max_demand_kva = st.number_input("Maximum demand (kVA)", min_value=0.0, step=100.0, value=13500.0)
    with col2:
        year = st.selectbox("Year", Years)
        units_kvah = st.number_input("Total energy consumption (kVAh)", min_value=0.0, step=100.0, value=500000.0)

    st.markdown("---")
    st.subheader("2️⃣ New ToD Slab Timings (Supports 1 or 2 time zones per slab)")
    st.caption("Use commas to separate multiple time ranges (e.g., `06:00-09:00, 12:00-18:00`).")

    new_A_ranges = st.text_input("New Slab A", value="22:00-06:00")
    new_B_ranges = st.text_input("New Slab B", value="06:00-09:00, 12:00-18:00")
    new_C_ranges = st.text_input("New Slab C", value="09:00-12:00")
    new_D_ranges = st.text_input("New Slab D", value="18:00-22:00")

    st.markdown("---")
    st.subheader("3️⃣ ToD Multipliers (%)")
    mcol1, mcol2 = st.columns(2)
    with mcol1:
        tod_A = st.number_input("ToD Multiplier A", value=0.0)
        tod_B = st.number_input("ToD Multiplier B", value=0.0)
    with mcol2:
        tod_C = st.number_input("ToD Multiplier C", value=-2.17)
        tod_D = st.number_input("ToD Multiplier D", value=2.17)

    st.markdown("---")
    new_energy_rate = st.number_input("Energy Rate (₹/kVAh)", min_value=0.0, value=8.68, step=0.01)
    calculate = st.button("🚀 Calculate Landed Unit Rate")

# -----------------------------
# Calculation
# -----------------------------
if calculate:
    OldUnits = {k: units_kvah * (v / 100.0) for k, v in OLD_TOD_RATIOS.items()}
    new_slab_segments = {
        "A": parse_multiple_ranges(new_A_ranges),
        "B": parse_multiple_ranges(new_B_ranges),
        "C": parse_multiple_ranges(new_C_ranges),
        "D": parse_multiple_ranges(new_D_ranges),
    }

    # Compute overlap and NewUnits
    NewUnits = {k: 0.0 for k in ["A", "B", "C", "D"]}
    for old_k, old_segments in OLD_SLAB_TIMINGS.items():
        old_duration = sum(
            (24.0 - parse_time(a) + parse_time(b)) if parse_time(a) >= parse_time(b) else (parse_time(b) - parse_time(a))
            for a, b in old_segments
        )
        for new_k, new_segments in new_slab_segments.items():
            overlap = total_overlap_hours(
                [(parse_time(a), parse_time(b)) for a, b in old_segments],
                new_segments,
            )
            if old_duration > 0:
                NewUnits[new_k] += OldUnits[old_k] * (overlap / old_duration)

    # ToD charges
    ToD_A = NewUnits["A"] * (tod_A / 100)
    ToD_B = NewUnits["B"] * (tod_B / 100)
    ToD_C = NewUnits["C"] * (tod_C / 100)
    ToD_D = NewUnits["D"] * (tod_D / 100)
    ToD_charge = ToD_A + ToD_B + ToD_C + ToD_D

    DC = max_demand_kva * DC_rate
    EC = units_kvah * new_energy_rate
    FAC = units_kvah * FAC_rate
    ED = (ED_percent / 100.0) * (DC + EC + FAC + ToD_charge)
    ToS = (units_kvah * 0.997) * ToS_rate
    kWh = units_kvah * 0.997

    ICR = ((kWh - 4044267) * (-0.75))
    def calc_BCR(units):
        if units <= 900000:
            return -(units * 0.07)
        elif units <= 5000000:
            return -((900000 * 0.07) + ((units - 900000) * 0.09))
        else:
            return -((900000 * 0.07) + (4100000 * 0.09) + ((units - 5000000) * 0.11))
    BCR = calc_BCR(units_kvah)

    Total = DC + EC + ToD_charge + FAC + ED + ToS + BCR + ICR
    promptPaymentDiscount = (DC + EC + FAC + ToD_charge) * (-0.01)
    LandedRate = (Total + promptPaymentDiscount) / kWh

    # Display
    st.success("✅ Calculation complete!")
    st.metric(label="⚡ Landed Unit Rate (₹/kWh)", value=f"{LandedRate:,.4f}")
    st.write(f"**Total Bill:** ₹ {Total:,.2f}")

    with st.expander("📋 Detailed Breakdown"):
        tod_df = pd.DataFrame({
            "Slab": ["A", "B", "C", "D"],
            "New Time Ranges": [new_A_ranges, new_B_ranges, new_C_ranges, new_D_ranges],
            "New Units (kVAh)": [NewUnits["A"], NewUnits["B"], NewUnits["C"], NewUnits["D"]],
            "Multiplier (%)": [tod_A, tod_B, tod_C, tod_D],
            "ToD Charge (₹)": [ToD_A, ToD_B, ToD_C, ToD_D],
        })

        # ✅ Safe numeric formatting (fixes your crash)
        numeric_cols = tod_df.select_dtypes(include="number").columns
        for col in numeric_cols:
            tod_df[col] = tod_df[col].round(2)

        st.dataframe(tod_df, use_container_width=True)

        breakdown_df = pd.DataFrame({
            "Component": ["Demand Charge", "Energy Charge", "ToD Charge", "FAC", "ED", "ToS", "BCR", "ICR", "Total"],
            "Value (₹)": [DC, EC, ToD_charge, FAC, ED, ToS, BCR, ICR, Total],
        })
        for col in breakdown_df.select_dtypes(include="number").columns:
            breakdown_df[col] = breakdown_df[col].round(2)

        st.dataframe(breakdown_df, use_container_width=True)
