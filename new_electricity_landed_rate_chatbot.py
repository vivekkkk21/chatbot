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
# Embedded tariff keys (for dropdown)
# -----------------------------
TARIFF_KEYS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
Years = ["2020", "2021","2022","2023","2024", "2025","2026", "2027", "2028", "2029", "2030", "2031", "2032", "2033", "2034", "2035", "2036", "2037", "2038", "2039", "2040", "2041", "2042", "2043", "2044", "2045", "2046"]
# -----------------------------
# Fixed Old ToD Ratios & Old slab timings (from Excel)
# -----------------------------
OLD_TOD_RATIOS = {"A": 33.541412, "B": 34.476496, "C": 6.837052, "D": 25.14506}
# Old slab timings - note B has two ranges
OLD_SLAB_TIMINGS = {
    "A": [("22:00", "06:00")],                # wrap-around
    "B": [("06:00", "09:00"), ("12:00", "18:00")],  # two ranges
    "C": [("09:00", "12:00")],
    "D": [("18:00", "22:00")],
}

# -----------------------------
# Page config + title
# -----------------------------
st.set_page_config(
    page_title="Electricity Landed Unit Rate Calculator",
    page_icon="⚡",
    layout="wide",
)
st.title("⚡ Electricity Landed Unit Rate Calculator")
st.markdown("### 👋 Hello! Use the form to compute the Landed Unit Rate. Constants on the right are editable and reset on reload.")

# -----------------------------
# Layout: two columns
# -----------------------------
left_col, right_col = st.columns([2.2, 1])

# -----------------------------
# Right column: editable constants table (resets on reload)
# -----------------------------
with right_col:
    st.header("🔧 Constants (editable)")
    st.markdown(
        "Edit values here for the calculation. These reset to defaults if you reload the page.\n\n"
        "- **DC_rate** = Demand charge (₹ per kVA)\n"
        "- **FAC_rate** = Fuel Adjustment Charge (₹ per kVAh)\n"
        "- **ToS_rate** = Tax on Sale (₹ per kWh)\n"
        "- **ED_percent** = Electricity Duty (in %)"
    )

    const_df = pd.DataFrame(DEFAULT_CONSTANTS)
    # Use data_editor for in-place editing if available, otherwise fallback to simple inputs
    try:
        edited = st.data_editor(
            const_df,
            num_rows="fixed",
            use_container_width=True,
            key="constants_editor",
        )
    except Exception:
        # fallback: show inputs individually
        st.warning("Interactive table not supported; using individual inputs.")
        edited = const_df.copy()
        edited.loc[0, "Value"] = st.number_input("DC_rate (₹/kVA)", value=edited.loc[0, "Value"])
        edited.loc[1, "Value"] = st.number_input("FAC_rate (₹/kVAh)", value=edited.loc[1, "Value"])
        edited.loc[2, "Value"] = st.number_input("ToS_rate (₹/kWh)", value=edited.loc[2, "Value"])
        edited.loc[3, "Value"] = st.number_input("ED_percent (%)", value=edited.loc[3, "Value"])

    # Extract constants safely
    try:
        DC_rate = float(edited.loc[edited["Parameter"] == "DC_rate", "Value"].values[0])
        FAC_rate = float(edited.loc[edited["Parameter"] == "FAC_rate", "Value"].values[0])
        ToS_rate = float(edited.loc[edited["Parameter"] == "ToS_rate", "Value"].values[0])
        ED_percent = float(edited.loc[edited["Parameter"] == "ED_percent", "Value"].values[0])
    except Exception:
        st.error("Error reading constants table — reverting to defaults.")
        DC_rate, FAC_rate, ToS_rate, ED_percent = DEFAULT_CONSTANTS["Value"]

    st.markdown("---")
    st.markdown("**Current constants (used in calculations):**")
    st.write(
        pd.DataFrame({
            "Parameter": ["DC_rate (₹/kVA)", "FAC_rate (₹/kVAh)", "ToS_rate (₹/kWh)", "ED_percent (%)"],
            "Value": [f"{DC_rate}", f"{FAC_rate}", f"{ToS_rate}", f"{ED_percent}"]
        })
    )

# -----------------------------
# Helper functions for time parsing and overlap
# -----------------------------
def parse_time(t: str) -> float:
    """Parse 'HH:MM' -> hour float (0-24)."""
    hh, mm = t.split(":")
    return int(hh) + int(mm) / 60.0

def parse_range(r: str) -> Tuple[float, float]:
    """Parse 'HH:MM-HH:MM' -> (start_hour, end_hour)."""
    a, b = r.split("-")
    return parse_time(a.strip()), parse_time(b.strip())

def split_range_if_wrap(start: float, end: float) -> List[Tuple[float, float]]:
    """
    If range wraps (start >= end), split into two segments: [start,24) and [0,end).
    Otherwise return single segment list.
    """
    if start < end:
        return [(start, end)]
    else:
        # wrap-around
        return [(start, 24.0), (0.0, end)]

def overlap_between_segments(seg1: Tuple[float, float], seg2: Tuple[float, float]) -> float:
    """Return overlap hours between two non-wrapping segments (start,end)."""
    s1, e1 = seg1
    s2, e2 = seg2
    start = max(s1, s2)
    end = min(e1, e2)
    return max(0.0, end - start)

def total_overlap_hours(range1: Tuple[float, float], range2: Tuple[float, float]) -> float:
    """Handle wrap-around by splitting ranges and summing overlap."""
    segs1 = split_range_if_wrap(*range1)
    segs2 = split_range_if_wrap(*range2)
    total = 0.0
    for a in segs1:
        for b in segs2:
            total += overlap_between_segments(a, b)
    return total

# -----------------------------
# Left column: Inputs & calculation
# -----------------------------
with left_col:
    st.header("1️⃣ Inputs")

    col1, col2 = st.columns(2)
    with col1:
        month = st.selectbox("Select Month", options=TARIFF_KEYS)
        max_demand_kva = st.number_input("Maximum demand (kVA)", min_value=0.0, step=100.0, value=13500.0, format="%.2f")
        
    with col2:
        year = st.selectbox("Select Year", options=Years)
        units_kvah = st.number_input("Total energy consumption (kVAh)", min_value=0.0, step=100.0, value=500000.0, format="%.2f")
        

    st.markdown("---")
    st.header("2️⃣ Time-of-Day (ToD) Slab Ratios (percent of total kVAh)")
    rcol1, rcol2 = st.columns(2)
    with rcol1:
        # These fields exist in your UI; keep them but they will NOT be used in the new-time-slab-based ToD logic.
        slab_A = st.number_input("Slab A (%) [22:00–06:00] (UI field retained)", min_value=0.0, max_value=100.0, value=18.86)
        slab_B = st.number_input("Slab B (%) [06:00–09:00 & 12:00–18:00] (UI field retained)", min_value=0.0, max_value=100.0, value=7.35)
    with rcol2:
        slab_C = st.number_input("Slab C (%) [09:00–12:00] (UI field retained)", min_value=0.0, max_value=100.0, value=27.95)
        slab_D = st.number_input("Slab D (%) [18:00–22:00] (UI field retained)", min_value=0.0, max_value=100.0, value=45.83)

    total_ratio = slab_A + slab_B + slab_C + slab_D
    if total_ratio != 1:
        st.warning("⚠️ The slab ratios should add up to 100%. Current total: {:.2f}%".format(total_ratio))

    st.markdown("---")
    # New: editable New Slab Timings (these determine the new distribution)
    with st.expander("🔁 Edit New Slab Timings (affects ToD calculation) — default editable"):
        st.markdown("Enter time ranges in `HH:MM-HH:MM` 24-hour format. Examples: `00:00-06:00`, `06:00-09:00`.")
        new_A_range = st.text_input("New Slab A time range", value="00:00-06:00", help="e.g., 00:00-06:00")
        new_B_range = st.text_input("New Slab B time range", value="06:00-09:00", help="e.g., 06:00-09:00")
        new_C_range = st.text_input("New Slab C time range", value="09:00-17:00", help="e.g., 09:00-18:00")
        new_D_range = st.text_input("New Slab D time range", value="17:00-00:00", help="e.g., 18:00-22:00")

    st.markdown("---")
    st.header("3️⃣ ToD Multipliers")
    st.markdown(
        "Enter ToD multipliers as percentage adjustments relative to the energy rate.\n"
        "Example: `-1.5` means -1.5% adjustment for that slab; `1.1` means +1.1%."
    )
    mcol1, mcol2 = st.columns(2)
    with mcol1:
        tod_A = st.number_input("ToD Multiplier A (e.g., -1.5)", value=0.0, format="%.2f")
        tod_B = st.number_input("ToD Multiplier B (e.g., 0)", value=0.0, format="%.2f")
    with mcol2:
        tod_C = st.number_input("ToD Multiplier C (e.g., 0.8)", value=-2.17, format="%.2f")
        tod_D = st.number_input("ToD Multiplier D (e.g., 1.1)", value=2.17, format="%.2f")

    st.markdown("---")
    st.header("4️⃣ Energy Rate")
    new_energy_rate = st.number_input("New Energy Rate (₹ per kVAh)", min_value=0.0, step=0.01, value=8.68, format="%.4f")

    st.markdown("---")
    st.info("When ready, click **Calculate Landed Unit Rate** below.")

    # -----------------------------
    # Calculation trigger
    # -----------------------------
    calculate = st.button("🚀 Calculate Landed Unit Rate")

    if calculate:
        # Validate
        if units_kvah <= 0:
            st.error("Please enter a positive total energy (kVAh).")
        elif max_demand_kva <= 0:
            st.error("Please enter a positive maximum demand (kVA).")
        elif abs(total_ratio - 100.0) > 1e-6:
            st.error("Slab ratios must add up to 100%. Adjust the percentages and try again.")
        else:
            # --- Use constants from right column (editable) ---
            # DC_rate, FAC_rate, ToS_rate, ED_percent already extracted

            # --- 1. Demand Charge ---
            DC = max_demand_kva * DC_rate                   #Correct

            # --- 2. Base Energy Charge (EC) ---
            EC = units_kvah * new_energy_rate               #Correct

            # --- 3. ToD charge calculation USING TIME-OVERLAP LOGIC ---
            # Step 1: Old ToD Units (fixed old ratios)
            OldUnits = {
                "A": units_kvah * (OLD_TOD_RATIOS["A"] / 100.0),
                "B": units_kvah * (OLD_TOD_RATIOS["B"] / 100.0),
                "C": units_kvah * (OLD_TOD_RATIOS["C"] / 100.0),
                "D": units_kvah * (OLD_TOD_RATIOS["D"] / 100.0),
            }

            # Parse new slab ranges safely
            try:
                new_ranges = {
                    "A": parse_range(new_A_range),
                    "B": parse_range(new_B_range),
                    "C": parse_range(new_C_range),
                    "D": parse_range(new_D_range),
                }
            except Exception as e:
                st.error(f"Error parsing new slab time ranges: {e}")
                new_ranges = {
                    "A": (0.0, 6.0),
                    "B": (6.0, 9.0),
                    "C": (9.0, 17.0),
                    "D": (17.0, 0.0),
                }

            # Prepare old slab durations (sum durations if multiple segments)
            old_durations = {}
            for k, segments in OLD_SLAB_TIMINGS.items():
                dur = 0.0
                for seg in segments:
                    s, e = parse_range(f"{seg[0]}-{seg[1]}")
                    # compute length respecting wrap
                    seg_len = 0.0
                    if s < e:
                        seg_len = e - s
                    else:
                        seg_len = (24.0 - s) + e
                    dur += seg_len
                old_durations[k] = dur

            # For each new slab, compute NewUnits by summing contributions from each old slab,
            # proportional to the overlap hours / old_slab_duration
            NewUnits = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0}

            # Iterate old slabs and their segments
            for old_k, segments in OLD_SLAB_TIMINGS.items():
                # total old slab duration
                old_total_duration = old_durations[old_k]
                # For each segment in old slab (e.g., B has two segments)
                for seg in segments:
                    seg_start, seg_end = parse_range(f"{seg[0]}-{seg[1]}")
                    # For each new slab, compute overlap hours with this old segment
                    for new_k, new_range in new_ranges.items():
                        overlap = total_overlap_hours((seg_start, seg_end), new_range)
                        if old_total_duration > 0 and overlap > 0:
                            # fraction of this old-segment that overlaps the new slab
                            frac = overlap / old_total_duration
                            # contribution to new slab units comes from entire old slab units,
                            # distributed proportionally across segments (by fraction of overlap / old_total_duration)
                            # We need to scale by segment's part in old_total_duration:
                            # But here we already using overlap / old_total_duration which sums appropriately across segments.
                            NewUnits[new_k] += OldUnits[old_k] * (overlap / old_total_duration)

            # rounding tiny numerical noise
            for k in NewUnits:
                if abs(NewUnits[k]) < 1e-9:
                    NewUnits[k] = 0.0

            # Now compute ToD charges using multipliers and energy rate
            ToD_A = NewUnits["A"] * (tod_A )             
            ToD_B = NewUnits["B"] * (tod_B )             
            ToD_C = NewUnits["C"] * (tod_C )             
            ToD_D = NewUnits["D"] * (tod_D )            
            ToD_charge = ToD_A + ToD_B + ToD_C + ToD_D

            # --- 4. Other charges ---
            FAC = units_kvah * FAC_rate
            ED = (ED_percent / 100.0) * (DC + EC + FAC + ToD_charge)
            ToS = (units_kvah*0.997) * ToS_rate

            kWh = units_kvah*0.997
            
            #Incremental Consumption Rebate
            ICR = ((kWh - 4044267) * (-0.75))

            #BCR Bulk Consumption Rebate
            def calculate_bulk_consumption_rebate(units: float) -> float:
                """
                Bulk Consumption Rebate (BCR) logic:
                - ₹0.07 for first 9,00,000 units
                - ₹0.09 for next 40,00,000 units (from 9,00,001 to 49,99,999)
                - ₹0.11 for units beyond 50,00,000
                """
                rebate = 0.0
                if units_kvah <= 900000:
                    rebate = units_kvah * 0.07
                elif units_kvah <= 5000000:
                    rebate = (900000 * 0.07) + ((units_kvah - 1000000) * 0.09)
                else:
                    rebate = (900000 * 0.07) + (4100000 * 0.09) + ((units_kvah - 5000000) * 0.11)
                return rebate
            
            BCR = -calculate_bulk_consumption_rebate(units_kvah)


            # --- 5. Total and landed rate ---
            Total = DC + EC + ToD_charge + FAC + ED + ToS + BCR + ICR

            promptPaymentDiscount = (DC + EC + FAC + ToD_charge) * (-0.01) 

            LandedRate = (Total + promptPaymentDiscount) /  kWh

            # Display output (main summary)
            st.success("✅ Calculation complete")
            st.metric(label="⚡ Landed Unit Rate (₹ / kWh)", value=f"{LandedRate:,.4f}")
            st.markdown("**Total bill (₹):** {:,.2f}".format(Total))

            # Collapsible detailed breakdown
            with st.expander("Show detailed breakdown"):
                st.subheader("Detailed cost breakdown")
                st.write(f"**Month & Year:** {month}, {year}")
                st.write(f"**Total units (kVAh):** {units_kvah:,.2f}")
                st.write(f"**Maximum demand (kVA):** {max_demand_kva:,.2f}")
                st.write("---")
                st.write(f"**Demand Charge (DC):** ₹ {DC:,.2f}  (DC_rate = ₹{DC_rate:.2f} per kVA)")
                st.write(f"**Energy Charge (EC):** ₹ {EC:,.2f}  (Energy rate = ₹{new_energy_rate:.4f} per kVAh)")
                st.write("---")
                st.subheader("ToD: New slab units & charges (computed from Old ratios & time overlaps)")
                tod_table = pd.DataFrame({
                    "New Slab": ["A", "B", "C", "D"],
                    "New Time Range": [new_A_range, new_B_range, new_C_range, new_D_range],
                    "New Units (kVAh)": [NewUnits["A"], NewUnits["B"], NewUnits["C"], NewUnits["D"]],
                    "Multiplier (%)": [tod_A, tod_B, tod_C, tod_D],
                    "ToD Charge (₹)": [ToD_A, ToD_B, ToD_C, ToD_D],
                })
                tod_table["New Units (kVAh)"] = tod_table["New Units (kVAh)"].map(lambda x: f"{x:,.2f}")
                tod_table["ToD Charge (₹)"] = tod_table["ToD Charge (₹)"].map(lambda x: f"{x:,.2f}")
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

                st.write(f"**Total ToD charge:** ₹ {ToD_charge:,.2f}")
                st.write(f"**Fuel Adjustment (FAC):** ₹ {FAC:,.2f} (FAC_rate = ₹{FAC_rate:.4f} per kVAh)")
                st.write(f"**Electricity Duty (ED):** ₹ {ED:,.2f} (ED_percent = {ED_percent}%)")
                st.write(f"**Tax on Sale (ToS):** ₹ {ToS:,.2f} (ToS_rate = ₹{ToS_rate} per kWh)")
                st.write(f"**Bulk Consumption Rebate (BCR):** ₹ {BCR:,.2f}")
                st.write(f"**(Excluding first 1Lac, 7% for 9Lac Units; 9% for other 40Lac units; 11% for units exclusing beyond 50Lac)**")
                st.write(f"**Incremental Consumption rebate (ICR):** ₹ {ICR:,.2f} **INR 7.5%/kWAh for units above average **")
                st.write(f"**Prompt Payment Discount:** ₹ {promptPaymentDiscount:,.2f} ")
                st.write("---")
                st.write(f"**Total bill (₹):** {Total:,.2f}")
                st.write(f"**Landed Unit Rate (₹ / kWh):** {LandedRate:,.4f}")

            st.markdown("---")
            if st.button("🔁 Start New Calculation"):
                # Simple page reload by using streamlit.experimental_rerun if available.
                try:
                    st.experimental_rerun()
                except Exception:
                    st.info("Reload the page to reset values.")

# Footer / help
st.markdown("---")
st.caption(
    "Made for MSEDCL MYT style landed unit rate calculations. ToD multipliers are interpreted "
    "as percentage adjustments to the energy rate for that slab (e.g., -1.5 → -1.5%). "
    "Old ToD ratios are fixed (34,34,7,25). New slab timings are editable; any changes "
    "update the ToD distribution using time overlap logic. Constants reset to defaults on page reload."
)













