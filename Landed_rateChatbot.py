# yearly_landed_rate.py
import streamlit as st
import pandas as pd
from typing import List, Tuple

st.set_page_config(page_title="Yearly Landed Unit Rate Calculator", layout="wide", page_icon="⚡")
st.title("⚡ Yearly Landed Unit Rate Calculator")
st.markdown("Two-table layout: **Reference Table** (top) — editable, and **Billing Components** (bottom) — auto-filled for checked months.")

# -----------------------------
# Defaults and old slab timings
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

# OLD_SLAB_TIMINGS preserved (used for overlap mapping). Do not change.
OLD_SLAB_TIMINGS = {
    "A": [("22:00", "06:00")],
    "B": [("06:00", "09:00"), ("12:00", "18:00")],
    "C": [("09:00", "12:00")],
    "D": [("18:00", "22:00")],
}

# Default ToD ratios to prefill reference table (same defaults as requested)
DEFAULT_TOD_RATIOS = {"A": 33.541412, "B": 34.476496, "C": 6.837052, "D": 25.14506}

MONTHS = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

# -----------------------------
# Right column: global constants (editable but per-month values will be used in calculations)
# -----------------------------
left_col, right_col = st.columns([2.2, 1])
with right_col:
    st.header("🔧 Global Defaults (editable)")
    const_df = pd.DataFrame(DEFAULT_CONSTANTS)
    try:
        edited_constants = st.data_editor(const_df, num_rows="fixed", use_container_width=True, key="const_editor_yearly")
        GLOBAL_DC_rate = float(edited_constants.loc[edited_constants["Parameter"] == "DC_rate", "Value"].values[0])
        GLOBAL_FAC_rate = float(edited_constants.loc[edited_constants["Parameter"] == "FAC_rate", "Value"].values[0])
        GLOBAL_ToS_rate = float(edited_constants.loc[edited_constants["Parameter"] == "ToS_rate", "Value"].values[0])
        GLOBAL_ED_percent = float(edited_constants.loc[edited_constants["Parameter"] == "ED_percent", "Value"].values[0])
    except Exception:
        st.warning("Interactive constants editor not available — using internal defaults.")
        GLOBAL_DC_rate, GLOBAL_FAC_rate, GLOBAL_ToS_rate, GLOBAL_ED_percent = DEFAULT_CONSTANTS["Value"]

    st.markdown("---")
    st.write(pd.DataFrame({
        "Parameter": ["DC_rate (₹/kVA)", "FAC_rate (₹/kVAh)", "ToS_rate (₹/kWh)", "ED_percent (%)"],
        "Value": [f"{GLOBAL_DC_rate}", f"{GLOBAL_FAC_rate}", f"{GLOBAL_ToS_rate}", f"{GLOBAL_ED_percent}"]
    }))

# -----------------------------
# Helper functions for times & overlap
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
# Reference Table (editable) — includes DC/FAC/ToS/ED and ToD ratios
# -----------------------------
st.markdown("## Reference Table (editable)")
def default_row(month_name):
    return {
        "Month": month_name,
        "Calc": False,  # whether to calculate this month
        "MaxDemand_kVA": 13500.0,
        "Units_kVAh": 500000.0,
        "EnergyRate_₹/kVAh": 8.68,

        # Per-month editable constants (these will be used in calculation for that month)
        "DC_rate": float(GLOBAL_DC_rate),
        "FAC_rate": float(GLOBAL_FAC_rate),
        "ToS_rate": float(GLOBAL_ToS_rate),
        "ED_percent": float(GLOBAL_ED_percent),

        # ToD ratios per month (these determine how OldUnits are computed)
        "ToD_ratio_A": float(DEFAULT_TOD_RATIOS["A"]),
        "ToD_ratio_B": float(DEFAULT_TOD_RATIOS["B"]),
        "ToD_ratio_C": float(DEFAULT_TOD_RATIOS["C"]),
        "ToD_ratio_D": float(DEFAULT_TOD_RATIOS["D"]),

        # ToD multipliers (used for ToD charge calculation)
        "ToD_mul_A": 0.0,
        "ToD_mul_B": 0.0,
        "ToD_mul_C": -2.17,
        "ToD_mul_D": 2.17,

        # New slab ranges (can be single or multiple ranges separated by comma/|/;)
        "NewRange_A": "00:00-06:00",
        "NewRange_B": "06:00-09:00",
        "NewRange_C": "09:00-17:00",
        "NewRange_D": "17:00-00:00",
    }

ref_rows = [default_row(m) for m in MONTHS]
ref_df = pd.DataFrame(ref_rows)

# Display editable reference table
try:
    ref_df_edited = st.data_editor(ref_df, num_rows="fixed", use_container_width=True, key="ref_table_editor")
except Exception:
    st.warning("Interactive table editor not supported — falling back to manual inputs.")
    ref_df_edited = ref_df.copy()
    for i, row in ref_df_edited.iterrows():
        st.write(f"### {row['Month']}")
        ref_df_edited.at[i, "Calc"] = st.checkbox(f"Calculate {row['Month']}", key=f"cb_{i}", value=row["Calc"])
        ref_df_edited.at[i, "MaxDemand_kVA"] = st.number_input(f"MaxDemand_kVA_{i}", value=row["MaxDemand_kVA"])
        ref_df_edited.at[i, "Units_kVAh"] = st.number_input(f"Units_kVAh_{i}", value=row["Units_kVAh"])
        ref_df_edited.at[i, "EnergyRate_₹/kVAh"] = st.number_input(f"EnergyRate_{i}", value=row["EnergyRate_₹/kVAh"])
        ref_df_edited.at[i, "DC_rate"] = st.number_input(f"DC_rate_{i}", value=row["DC_rate"])
        ref_df_edited.at[i, "FAC_rate"] = st.number_input(f"FAC_rate_{i}", value=row["FAC_rate"])
        ref_df_edited.at[i, "ToS_rate"] = st.number_input(f"ToS_rate_{i}", value=row["ToS_rate"])
        ref_df_edited.at[i, "ED_percent"] = st.number_input(f"ED_percent_{i}", value=row["ED_percent"])
        ref_df_edited.at[i, "ToD_ratio_A"] = st.number_input(f"ToD_ratio_A_{i}", value=row["ToD_ratio_A"])
        ref_df_edited.at[i, "ToD_ratio_B"] = st.number_input(f"ToD_ratio_B_{i}", value=row["ToD_ratio_B"])
        ref_df_edited.at[i, "ToD_ratio_C"] = st.number_input(f"ToD_ratio_C_{i}", value=row["ToD_ratio_C"])
        ref_df_edited.at[i, "ToD_ratio_D"] = st.number_input(f"ToD_ratio_D_{i}", value=row["ToD_ratio_D"])
        ref_df_edited.at[i, "ToD_mul_A"] = st.number_input(f"ToD_mul_A_{i}", value=row["ToD_mul_A"])
        ref_df_edited.at[i, "ToD_mul_B"] = st.number_input(f"ToD_mul_B_{i}", value=row["ToD_mul_B"])
        ref_df_edited.at[i, "ToD_mul_C"] = st.number_input(f"ToD_mul_C_{i}", value=row["ToD_mul_C"])
        ref_df_edited.at[i, "ToD_mul_D"] = st.number_input(f"ToD_mul_D_{i}", value=row["ToD_mul_D"])
        ref_df_edited.at[i, "NewRange_A"] = st.text_input(f"NewRange_A_{i}", value=row["NewRange_A"])
        ref_df_edited.at[i, "NewRange_B"] = st.text_input(f"NewRange_B_{i}", value=row["NewRange_B"])
        ref_df_edited.at[i, "NewRange_C"] = st.text_input(f"NewRange_C_{i}", value=row["NewRange_C"])
        ref_df_edited.at[i, "NewRange_D"] = st.text_input(f"NewRange_D_{i}", value=row["NewRange_D"])

# -----------------------------
# Run calculations for checked months
# -----------------------------
if st.button("Run Calculations for checked months"):
    billing_rows = []

    for _, row in ref_df_edited.iterrows():
        try:
            calc_flag = bool(row.get("Calc", False))
        except Exception:
            calc_flag = False
        if not calc_flag:
            continue

        # read per-month inputs (with safe fallbacks)
        month_name = row.get("Month", "Unknown")
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

        # per-month constants (use per-month edited values)
        try:
            DC_rate = float(row.get("DC_rate", GLOBAL_DC_rate))
        except Exception:
            DC_rate = GLOBAL_DC_rate
        try:
            FAC_rate = float(row.get("FAC_rate", GLOBAL_FAC_rate))
        except Exception:
            FAC_rate = GLOBAL_FAC_rate
        try:
            ToS_rate = float(row.get("ToS_rate", GLOBAL_ToS_rate))
        except Exception:
            ToS_rate = GLOBAL_ToS_rate
        try:
            ED_percent = float(row.get("ED_percent", GLOBAL_ED_percent))
        except Exception:
            ED_percent = GLOBAL_ED_percent

        # per-month ToD ratios (these will be used to compute OldUnits distribution)
        try:
            ratio_A = float(row.get("ToD_ratio_A", DEFAULT_TOD_RATIOS["A"]))
            ratio_B = float(row.get("ToD_ratio_B", DEFAULT_TOD_RATIOS["B"]))
            ratio_C = float(row.get("ToD_ratio_C", DEFAULT_TOD_RATIOS["C"]))
            ratio_D = float(row.get("ToD_ratio_D", DEFAULT_TOD_RATIOS["D"]))
        except Exception:
            ratio_A, ratio_B, ratio_C, ratio_D = (DEFAULT_TOD_RATIOS["A"], DEFAULT_TOD_RATIOS["B"], DEFAULT_TOD_RATIOS["C"], DEFAULT_TOD_RATIOS["D"])

        # ToD multipliers (used later to compute ToD charge)
        try:
            tod_A = float(row.get("ToD_mul_A", 0.0))
            tod_B = float(row.get("ToD_mul_B", 0.0))
            tod_C = float(row.get("ToD_mul_C", 0.0))
            tod_D = float(row.get("ToD_mul_D", 0.0))
        except Exception:
            tod_A, tod_B, tod_C, tod_D = 0.0, 0.0, -2.17, 2.17

        # parse new ranges per slab (allow multiple ranges)
        new_ranges_input = {
            "A": row.get("NewRange_A", ""),
            "B": row.get("NewRange_B", ""),
            "C": row.get("NewRange_C", ""),
            "D": row.get("NewRange_D", ""),
        }
        new_ranges_parsed = {}
        for k, text in new_ranges_input.items():
            parsed = parse_multi_ranges_input(str(text))
            if not parsed:
                parsed = [(0.0, 0.0)]
            new_ranges_parsed[k] = parsed

        # --- 1. Demand Charge ---
        DC = max_demand_kva * DC_rate

        # --- 2. Base Energy Charge (EC) ---
        EC = units_kvah * new_energy_rate

        # --- 3. ToD charge calculation using per-month ToD ratios mapped via overlaps ---
        OldUnits = {
            "A": units_kvah * (ratio_A / 100.0),
            "B": units_kvah * (ratio_B / 100.0),
            "C": units_kvah * (ratio_C / 100.0),
            "D": units_kvah * (ratio_D / 100.0),
        }

        # compute old durations (hours)
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

        # distribute OldUnits into NewUnits based on overlaps
        NewUnits = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0}
        for old_k, old_segs in OLD_SLAB_TIMINGS.items():
            old_total_duration = old_durations[old_k]
            old_numeric_segs = []
            for s, e in old_segs:
                try:
                    old_numeric_segs.append(parse_range_str(f"{s}-{e}"))
                except Exception:
                    pass
            for old_seg in old_numeric_segs:
                for new_k, new_segs in new_ranges_parsed.items():
                    overlap = total_overlap_hours_multi([old_seg], new_segs)
                    if overlap > 0 and old_total_duration > 0:
                        NewUnits[new_k] += OldUnits[old_k] * (overlap / old_total_duration)

        # small numerical cleanup
        for k in NewUnits:
            if abs(NewUnits[k]) < 1e-9:
                NewUnits[k] = 0.0

        # ToD charges: multipliers are applied directly (consistent with your prior code)
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

        # Incremental Consumption Rebate (kept same)
        ICR = ((kWh - 4044267) * (-0.75))

        # Bulk Consumption Rebate (same logic)
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

    # assemble & display billing dataframe
    if billing_rows:
        billing_df = pd.DataFrame(billing_rows)
        cols = ["Month","DC","EC","ToD_charge","FAC","ED","ToS","BCR","ICR","PromptPaymentDisc","Total","LandedRate"]
        billing_df = billing_df[cols]
        # Safer formatting: round numeric cols
        numeric_cols = billing_df.select_dtypes(include="number").columns
        for col in numeric_cols:
            billing_df[col] = billing_df[col].round(2)

        st.markdown("## Billing Components (calculated for checked months)")
        st.dataframe(billing_df, use_container_width=True)
    else:
        st.info("No months were checked for calculation. Tick the 'Calc' column for months you want to compute and press the button.")

# Footer
st.markdown("---")
st.caption("Notes: New slab ranges may contain 1 or more ranges (comma/| separated). Overlap logic maps per-month ToD ratio-based old slab units into new slabs (preserving calculation logic).")
