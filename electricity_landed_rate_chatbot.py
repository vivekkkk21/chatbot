# yearly_landed_rate.py
import streamlit as st
import pandas as pd
from typing import List, Tuple

st.set_page_config(page_title="Yearly Landed Unit Rate Calculator", layout="wide", page_icon="⚡")
st.title("⚡ Yearly Landed Unit Rate Calculator")
st.markdown("Two-table layout: **Reference Table** (top) — editable, and **Billing Components** (bottom) — auto-filled for checked months.")

# -----------------------------
# Constants (same as your single-month app)
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

# Old ToD ratios & timings (kept from your last code)
OLD_TOD_RATIOS = {"A": 33.541412, "B": 34.476496, "C": 6.837052, "D": 25.14506}
OLD_SLAB_TIMINGS = {
    "A": [("22:00", "06:00")],
    "B": [("06:00", "09:00"), ("12:00", "18:00")],
    "C": [("09:00", "12:00")],
    "D": [("18:00", "22:00")],
}

MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]

# -----------------------------
# Right column: constants editor (same pattern)
# -----------------------------
left, right = st.columns([2.2, 1])
with right:
    st.header("🔧 Constants (editable)")
    const_df = pd.DataFrame(DEFAULT_CONSTANTS)
    try:
        edited_constants = st.data_editor(const_df, num_rows="fixed", use_container_width=True, key="const_editor_yearly")
        DC_rate = float(edited_constants.loc[edited_constants["Parameter"] == "DC_rate", "Value"].values[0])
        FAC_rate = float(edited_constants.loc[edited_constants["Parameter"] == "FAC_rate", "Value"].values[0])
        ToS_rate = float(edited_constants.loc[edited_constants["Parameter"] == "ToS_rate", "Value"].values[0])
        ED_percent = float(edited_constants.loc[edited_constants["Parameter"] == "ED_percent", "Value"].values[0])
    except Exception:
        st.warning("Interactive constants editor not available — falling back to defaults.")
        DC_rate, FAC_rate, ToS_rate, ED_percent = DEFAULT_CONSTANTS["Value"]

    st.markdown("---")
    st.write(pd.DataFrame({
        "Parameter": ["DC_rate (₹/kVA)", "FAC_rate (₹/kVAh)", "ToS_rate (₹/kWh)", "ED_percent (%)"],
        "Value": [f"{DC_rate}", f"{FAC_rate}", f"{ToS_rate}", f"{ED_percent}"]
    }))

# -----------------------------
# Helpers: time parsing & overlap (supports lists of ranges)
# -----------------------------
def parse_time(t: str) -> float:
    hh, mm = t.split(":")
    return int(hh) + int(mm) / 60.0

def parse_range_str(r: str) -> Tuple[float, float]:
    a, b = r.split("-")
    return parse_time(a.strip()), parse_time(b.strip())

def split_range_if_wrap(start: float, end: float) -> List[Tuple[float, float]]:
    if start < end:
        return [(start, end)]
    else:
        return [(start, 24.0), (0.0, end)]

def overlap_between_segments(seg1: Tuple[float, float], seg2: Tuple[float, float]) -> float:
    s1, e1 = seg1; s2, e2 = seg2
    start = max(s1, s2); end = min(e1, e2)
    return max(0.0, end - start)

def total_overlap_hours_multi(old_segments: List[Tuple[float, float]], new_segments: List[Tuple[float, float]]) -> float:
    total_overlap = 0.0
    for old_seg in old_segments:
        for new_seg in new_segments:
            for osub in split_range_if_wrap(*old_seg):
                for nsub in split_range_if_wrap(*new_seg):
                    total_overlap += overlap_between_segments(osub, nsub)
    return total_overlap

def parse_multi_ranges_input(s: str) -> List[Tuple[float,float]]:
    """
    Accepts a string like:
      "06:00-09:00, 12:00-18:00" or "06:00-09:00|12:00-18:00"
    Returns list of (start_h, end_h) tuples.
    """
    if not isinstance(s, str) or not s.strip():
        return []
    parts = []
    for sep in [",", "|", ";"]:
        if sep in s:
            parts = [p.strip() for p in s.split(sep) if p.strip()]
            break
    if not parts:
        parts = [s.strip()]
    parsed = []
    for p in parts:
        try:
            parsed.append(parse_range_str(p))
        except Exception:
            # ignore invalid formats
            pass
    return parsed

# -----------------------------
# Build Reference Table (12 months) — editable
# -----------------------------
st.markdown("## Reference Table (editable)")
# Default row template
def default_row(month_name):
    return {
        "Month": month_name,
        "Calc": False,  # checkbox - when true we will calculate for that month
        "MaxDemand_kVA": 13500.0,
        "Units_kVAh": 500000.0,
        "EnergyRate_₹/kVAh": 8.68,
        # multipliers interpreted as ₹/kVAh or as code currently does (user maintains consistency)
        "ToD_mul_A": 0.0,
        "ToD_mul_B": 0.0,
        "ToD_mul_C": -2.17,
        "ToD_mul_D": 2.17,
        # new slab ranges allow multiple ranges per slab (comma/| separated)
        "NewRange_A": "00:00-06:00",
        "NewRange_B": "06:00-09:00",   # user can enter "06:00-09:00,12:00-18:00" for two
        "NewRange_C": "09:00-17:00",
        "NewRange_D": "17:00-00:00",
    }

ref_rows = [default_row(m) for m in MONTHS]
ref_df = pd.DataFrame(ref_rows)

# Display editable reference table using data_editor
try:
    ref_df_edited = st.data_editor(ref_df, num_rows="fixed", use_container_width=True, key="ref_table_editor")
except Exception:
    st.warning("Interactive table editor not supported in this environment. Falling back to row-by-row inputs.")
    # fallback simple editor (rare)
    ref_df_edited = ref_df.copy()
    for i, row in ref_df_edited.iterrows():
        st.write(f"### {row['Month']}")
        ref_df_edited.at[i, "Calc"] = st.checkbox(f"Calculate {row['Month']}", key=f"cb_{i}")
        ref_df_edited.at[i, "MaxDemand_kVA"] = st.number_input(f"MaxDemand_kVA_{i}", value=row["MaxDemand_kVA"])
        ref_df_edited.at[i, "Units_kVAh"] = st.number_input(f"Units_kVAh_{i}", value=row["Units_kVAh"])
        ref_df_edited.at[i, "EnergyRate_₹/kVAh"] = st.number_input(f"EnergyRate_{i}", value=row["EnergyRate_₹/kVAh"])
        ref_df_edited.at[i, "ToD_mul_A"] = st.number_input(f"ToD_mul_A_{i}", value=row["ToD_mul_A"])
        ref_df_edited.at[i, "ToD_mul_B"] = st.number_input(f"ToD_mul_B_{i}", value=row["ToD_mul_B"])
        ref_df_edited.at[i, "ToD_mul_C"] = st.number_input(f"ToD_mul_C_{i}", value=row["ToD_mul_C"])
        ref_df_edited.at[i, "ToD_mul_D"] = st.number_input(f"ToD_mul_D_{i}", value=row["ToD_mul_D"])
        ref_df_edited.at[i, "NewRange_A"] = st.text_input(f"NewRange_A_{i}", value=row["NewRange_A"])
        ref_df_edited.at[i, "NewRange_B"] = st.text_input(f"NewRange_B_{i}", value=row["NewRange_B"])
        ref_df_edited.at[i, "NewRange_C"] = st.text_input(f"NewRange_C_{i}", value=row["NewRange_C"])
        ref_df_edited.at[i, "NewRange_D"] = st.text_input(f"NewRange_D_{i}", value=row["NewRange_D"])

# -----------------------------
# Button to run calculations for checked months
# -----------------------------
if st.button("Run Calculations for checked months"):
    # Prepare billing results dataframe
    billing_cols = [
        "Month", "DC", "EC", "ToD_charge", "FAC", "ED", "ToS", "BCR", "ICR", "PromptPaymentDisc", "Total", "LandedRate"
    ]
    billing_rows = []

    # iterate rows that are checked
    for _, row in ref_df_edited.iterrows():
        try:
            calc_flag = bool(row.get("Calc", False))
        except Exception:
            calc_flag = False
        if not calc_flag:
            continue

        # fetch inputs for the month (coerce numerics)
        month_name = row.get("Month")
        try:
            max_demand_kva = float(row.get("MaxDemand_kVA", 0.0))
        except Exception:
            max_demand_kva = 0.0
        try:
            units_kvah = float(row.get("Units_kVAh", 0.0))
        except Exception:
            units_kvah = 0.0
        try:
            new_energy_rate = float(row.get("EnergyRate_₹/kVAh", 0.0))
        except Exception:
            new_energy_rate = 0.0

        # multipliers (in your last code they were used directly as ₹/kVAh)
        tod_A = float(row.get("ToD_mul_A", 0.0))
        tod_B = float(row.get("ToD_mul_B", 0.0))
        tod_C = float(row.get("ToD_mul_C", 0.0))
        tod_D = float(row.get("ToD_mul_D", 0.0))

        # parse new ranges (allow multiple ranges per slab)
        new_ranges_input = {
            "A": row.get("NewRange_A", ""),
            "B": row.get("NewRange_B", ""),
            "C": row.get("NewRange_C", ""),
            "D": row.get("NewRange_D", ""),
        }
        new_ranges_parsed = {}
        for k, text in new_ranges_input.items():
            parsed_list = parse_multi_ranges_input(str(text))
            # if empty, keep a default 0-0 to not crash
            if not parsed_list:
                parsed_list = [(0.0, 0.0)]
            new_ranges_parsed[k] = parsed_list

        # --- 1. Demand Charge ---
        DC = max_demand_kva * DC_rate

        # --- 2. Base Energy Charge (EC) ---
        EC = units_kvah * new_energy_rate

        # --- 3. ToD calculation using OLD ratios and overlap distribution ---
        OldUnits = {
            "A": units_kvah * (OLD_TOD_RATIOS["A"] / 100.0),
            "B": units_kvah * (OLD_TOD_RATIOS["B"] / 100.0),
            "C": units_kvah * (OLD_TOD_RATIOS["C"] / 100.0),
            "D": units_kvah * (OLD_TOD_RATIOS["D"] / 100.0),
        }

        # prepare old durations sum (in hours)
        old_durations = {}
        for k, segs in OLD_SLAB_TIMINGS.items():
            dur = 0.0
            for seg in segs:
                try:
                    s, e = parse_range_str(f"{seg[0]}-{seg[1]}")
                except Exception:
                    s, e = 0.0, 0.0
                if s < e:
                    seg_len = e - s
                else:
                    seg_len = (24.0 - s) + e
                dur += seg_len
            old_durations[k] = dur if dur > 0 else 1.0

        # compute NewUnits by distributing OldUnits via overlaps
        NewUnits = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0}
        for old_k, old_segs in OLD_SLAB_TIMINGS.items():
            old_total_duration = old_durations[old_k]
            # convert old_segs to numeric tuples
            old_numeric_segs = []
            for s,e in old_segs:
                try:
                    old_numeric_segs.append(parse_range_str(f"{s}-{e}"))
                except Exception:
                    pass
            for old_seg in old_numeric_segs:
                for new_k, new_segs in new_ranges_parsed.items():
                    overlap = total_overlap_hours_multi([old_seg], new_segs)
                    if overlap > 0 and old_total_duration > 0:
                        NewUnits[new_k] += OldUnits[old_k] * (overlap / old_total_duration)

        # small numeric cleaning
        for k in NewUnits:
            if abs(NewUnits[k]) < 1e-9:
                NewUnits[k] = 0.0

        # ToD charges — note: in this code we use multipliers directly (₹/kVAh)
        ToD_A = NewUnits["A"] * tod_A
        ToD_B = NewUnits["B"] * tod_B
        ToD_C = NewUnits["C"] * tod_C
        ToD_D = NewUnits["D"] * tod_D
        ToD_charge = ToD_A + ToD_B + ToD_C + ToD_D

        # --- 4. Other charges ---
        FAC = units_kvah * FAC_rate
        ED = (ED_percent / 100.0) * (DC + EC + FAC + ToD_charge)
        ToS = (units_kvah * 0.997) * ToS_rate

        kWh = units_kvah * 0.997

        # Incremental Consumption Rebate (kept same as prior code)
        ICR = ((kWh - 4044267) * (-0.75))

        # Bulk Consumption Rebate (kept same logic, returns positive then we subtract)
        def calculate_bulk_consumption_rebate(units: float) -> float:
            rebate = 0.0
            if units <= 900000:
                rebate = units * 0.07
            elif units <= 5000000:
                rebate = (900000 * 0.07) + ((units - 900000) * 0.09)
            else:
                rebate = (900000 * 0.07) + (4100000 * 0.09) + ((units - 5000000) * 0.11)
            return rebate

        BCR = -calculate_bulk_consumption_rebate(units_kvah)

        # Total and discounts
        Total = DC + EC + ToD_charge + FAC + ED + ToS + BCR + ICR
        promptPaymentDiscount = (DC + EC + FAC + ToD_charge) * (-0.01)
        # apply promptPaymentDiscount in landed rate as your prior code did
        LandedRate = (Total + promptPaymentDiscount) / kWh if kWh > 0 else 0.0

        billing_rows.append({
            "Month": month_name,
            "DC": DC,
            "EC": EC,
            "ToD_charge": ToD_charge,
            "FAC": FAC,
            "ED": ED,
            "ToS": ToS,
            "BCR": BCR,
            "ICR": ICR,
            "PromptPaymentDisc": promptPaymentDiscount,
            "Total": Total,
            "LandedRate": LandedRate
        })

    # assemble billing dataframe and display
    if billing_rows:
        billing_df = pd.DataFrame(billing_rows)
        # order columns nicely
        cols = ["Month","DC","EC","ToD_charge","FAC","ED","ToS","BCR","ICR","PromptPaymentDisc","Total","LandedRate"]
        billing_df = billing_df[cols]
        st.markdown("## Billing Components (calculated for checked months)")
        st.dataframe(billing_df.style.format("{:,.2f}"), use_container_width=True)
    else:
        st.info("No months were checked for calculation. Tick the 'Calc' column for months you want to compute and press the button.")

# Footer note
st.markdown("---")
st.caption("Notes: New slab ranges may contain 1 or more ranges (comma/| separated). Overlap logic maps old slab units into new slabs exactly as in the single-month calculator. Calculations preserve original formulas.")
