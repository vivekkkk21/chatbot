# yearly_landed_rate.py
import streamlit as st
import pandas as pd
from io import BytesIO
from typing import List, Tuple

st.set_page_config(page_title="Yearly Landed Unit Rate Calculator", layout="wide", page_icon="⚡")
st.title("⚡ Yearly Landed Unit Rate Calculator")
st.markdown("Fill out the **Reference table** to calculate the **Landed Unit rate**. Click checkbox and select appropriate month before calculation")

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

OLD_SLAB_TIMINGS = {
    "A": [("22:00", "06:00")],
    "B": [("06:00", "09:00"), ("12:00", "18:00")],
    "C": [("09:00", "12:00")],
    "D": [("18:00", "22:00")],
}

DEFAULT_TOD_RATIOS = {"A": 33.541412, "B": 34.476496, "C": 6.837052, "D": 25.14506}

MONTHS = [
    "Jan","Feb","March","April","May","June",
    "July","Aug","Sept","Oct","Nov","Dec"
]

# -----------------------------
# Global constants (hidden defaults)
# -----------------------------
const_df = pd.DataFrame(DEFAULT_CONSTANTS)
GLOBAL_DC_rate = float(const_df.loc[const_df["Parameter"] == "DC_rate", "Value"].values[0])
GLOBAL_FAC_rate = float(const_df.loc[const_df["Parameter"] == "FAC_rate", "Value"].values[0])
GLOBAL_ToS_rate = float(const_df.loc[const_df["Parameter"] == "ToS_rate", "Value"].values[0])
GLOBAL_ED_percent = float(const_df.loc[const_df["Parameter"] == "ED_percent", "Value"].values[0])

# -----------------------------
# Helper functions for overlap (unchanged logic)
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
    if not isinstance(s, str) or not s.strip():
        return []
    for sep in [",", "|", ";"]:
        if sep in s:
            parts = [p.strip() for p in s.split(sep) if p.strip()]
            break
    else:
        parts = [s.strip()]
    parsed = []
    for p in parts:
        try:
            parsed.append(parse_range_str(p))
        except Exception:
            pass
    return parsed

# -----------------------------
# Energy Rate Settings Section (two seasonal rates)
# -----------------------------
st.markdown("### ⚙️ Energy Rate Settings")
col1, col2 = st.columns(2)
with col1:
    energy_rate_1 = st.number_input("Energy Rate (₹/kVAh) for **Jan–Mar**", value=8.68, step=0.01, key="energy_rate_1")
with col2:
    energy_rate_2 = st.number_input("Energy Rate (₹/kVAh) for **Apr–Dec**", value=8.90, step=0.01, key="energy_rate_2")

# -----------------------------
# Build Reference Table (horizontal data), then prepare vertical display
# -----------------------------
def default_row(month_name):
    energy_rate = energy_rate_1 if month_name in ["Jan", "Feb", "March"] else energy_rate_2
    return {
        "Month": month_name,
        "Calc": False,
        "MaxDemand_kVA": 13500.0,
        "Units_kVAh": 500000.0,
        "EnergyRate_₹/kVAh": energy_rate,
        "DC_rate": GLOBAL_DC_rate,
        "FAC_rate": GLOBAL_FAC_rate,
        "ToS_rate": GLOBAL_ToS_rate,
        "ED_percent": GLOBAL_ED_percent,
        # ToD ratios: kept but not shown
        "ToD_ratio_A": DEFAULT_TOD_RATIOS["A"],
        "ToD_ratio_B": DEFAULT_TOD_RATIOS["B"],
        "ToD_ratio_C": DEFAULT_TOD_RATIOS["C"],
        "ToD_ratio_D": DEFAULT_TOD_RATIOS["D"],
        # multipliers (user may edit per-month)
        "ToD_mul_A": 0.0,
        "ToD_mul_B": 0.0,
        "ToD_mul_C": -2.17,
        "ToD_mul_D": 2.17,
        # new ranges (editable)
        "NewRange_A": "00:00-06:00",
        "NewRange_B": "06:00-09:00",
        "NewRange_C": "09:00-17:00",
        "NewRange_D": "17:00-00:00",
    }

# horizontal dataframe (one row per month)
ref_df_horiz = pd.DataFrame([default_row(m) for m in MONTHS])

# columns to hide from the displayed table (ToD ratios)
hidden_cols = [f"ToD_ratio_{k}" for k in "ABCD"]

# prepare display dataframe: drop hidden columns and pivot to vertical (parameters x months)
ref_df_display = ref_df_horiz.drop(columns=hidden_cols).set_index("Month")  # index = months, columns = parameters
ref_df_vertical = ref_df_display.T  # index = parameters (rows), columns = months

# show vertical editable table
#st.markdown("## Reference Table (vertical view — parameters as rows, months as columns)")
#ref_df_vertical_edited = st.data_editor(
#    ref_df_vertical,
#    num_rows="fixed",
#    use_container_width=True,
#    key="ref_table_vertical_editor",
#)

st.markdown("## Reference Table")

# Drop Calc row before displaying
ref_df_vertical_no_calc = ref_df_vertical.drop(index="Calc")

# Reset index so that "Parameter" becomes editable column
ref_df_vertical_display = ref_df_vertical_no_calc.reset_index().rename(columns={"index": "Parameter"})

# Make the table editable
ref_df_vertical_edited = st.data_editor(
    ref_df_vertical_display,
    num_rows="fixed",
    use_container_width=True,
    key="ref_table_vertical_editor",
)

# Convert back to original format for internal use
ref_df_vertical_edited = ref_df_vertical_edited.set_index("Parameter")


# --- 3️⃣ Add Calc checkboxes as a bottom row ---
st.markdown("### Select Months for Calculation")
calc_row = ref_df_vertical.loc["Calc"].copy()
calc_values = {}

calc_cols = st.columns(len(MONTHS))
for i, month in enumerate(MONTHS):
    calc_values[month] = calc_cols[i].checkbox(
        month, 
        value=bool(calc_row[month]), 
        key=f"calc_{month}"
    )

# --- 4️⃣ Add Calc row back after checkbox edits ---
ref_df_vertical_edited.loc["Calc"] = pd.Series(calc_values)




# convert back to horizontal structure for internal use (months as rows)
# edited_vertical: index = parameters, columns = months -> transpose to months x parameters
ref_df_display_edited = ref_df_vertical_edited.T.reset_index().rename(columns={"index": "Month"})
# Ensure columns order same as original (some editors may coerce types)
# Add back hidden ToD_ratio columns unchanged from original
ref_df_edited = ref_df_display_edited.copy()
for col in hidden_cols:
    ref_df_edited[col] = ref_df_horiz[col].values

# Ensure Month order matches MONTHS
# If the data_editor allowed month-name editing, enforce original month ordering
try:
    ref_df_edited["Month"] = pd.Categorical(ref_df_edited["Month"], categories=MONTHS, ordered=True)
    ref_df_edited = ref_df_edited.sort_values("Month").reset_index(drop=True)
    ref_df_edited["Month"] = ref_df_edited["Month"].astype(str)
except Exception:
    # fallback: keep as-is
    pass

# -----------------------------
# Run calculations (same formulas and logic)
# -----------------------------
if st.button("Run Calculations for checked months"):
    billing_rows = []

    for _, row in ref_df_edited.iterrows():
        # skip months not checked
        try:
            if not bool(row.get("Calc", False)):
                continue
        except Exception:
            continue

        month_name = row["Month"]
        max_demand = float(row["MaxDemand_kVA"])
        units = float(row["Units_kVAh"])
        energy_rate = float(row["EnergyRate_₹/kVAh"])
        DC_rate = float(row["DC_rate"])
        FAC_rate = float(row["FAC_rate"])
        ToS_rate = float(row["ToS_rate"])
        ED_percent = float(row["ED_percent"])

        ratios = {k: float(row[f"ToD_ratio_{k}"]) for k in "ABCD"}
        tod_multipliers = {k: float(row[f"ToD_mul_{k}"]) for k in "ABCD"}
        new_ranges = {k: parse_multi_ranges_input(str(row[f"NewRange_{k}"])) for k in "ABCD"}

        # 1️⃣ Base Charges
        DC = max_demand * DC_rate
        EC = units * energy_rate

        # 2️⃣ Old ToD Units
        OldUnits = {k: units * (ratios[k] / 100.0) for k in "ABCD"}

        # 3️⃣ Redistribute based on overlaps
        NewUnits = {k: 0.0 for k in "ABCD"}
        for old_k, old_segments in OLD_SLAB_TIMINGS.items():
            old_dur = sum((parse_time(e) - parse_time(s)) % 24 for s, e in old_segments)
            for new_k, new_segs in new_ranges.items():
                overlap = total_overlap_hours_multi(
                    [parse_range_str(f"{s}-{e}") for s, e in old_segments], new_segs
                )
                if old_dur > 0:
                    NewUnits[new_k] += OldUnits[old_k] * (overlap / old_dur)
        # tiny numeric clean
        for k in NewUnits:
            if abs(NewUnits[k]) < 1e-9:
                NewUnits[k] = 0.0

        # 4️⃣ ToD Charges (multipliers used as ₹/kVAh as in your latest code)
        ToD_charge = sum(NewUnits[k] * tod_multipliers[k] for k in "ABCD")

        # 5️⃣ Other Charges
        FAC = units * FAC_rate
        ED = (ED_percent / 100.0) * (DC + EC + FAC + ToD_charge)
        ToS = (units * 0.997) * ToS_rate

        kWh = units * 0.997
        ICR = ((kWh - 4044267) * (-0.75))

        def BCR_fn(units_val):
            if units_val <= 900000:
                return -(units_val * 0.07)
            elif units_val <= 5000000:
                return -(900000 * 0.07 + (units_val - 900000) * 0.09)
            else:
                return -(900000 * 0.07 + 4100000 * 0.09 + (units_val - 5000000) * 0.11)

        BCR = BCR_fn(units)
        Total = DC + EC + ToD_charge + FAC + ED + ToS + BCR + ICR
        PPD = (DC + EC + FAC + ToD_charge) * (-0.01)
        LandedRate = (Total + PPD) / kWh if kWh > 0 else 0

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
            "PromptPaymentDisc": PPD,
            "Total": Total,
            "LandedRate": LandedRate
        })

    if billing_rows:
        billing_df = pd.DataFrame(billing_rows)
        # round for nicer display
        billing_df = billing_df.round(2)
        st.markdown("## Billing Components")
        st.dataframe(billing_df, use_container_width=True)

        # -----------------------------
        # Export Buttons
        # -----------------------------
        st.markdown("### 📤 Export Results")

        csv_ref = ref_df_edited.to_csv(index=False).encode('utf-8')
        csv_bill = billing_df.to_csv(index=False).encode('utf-8')

        def to_excel_bytes(ref_df_in, bill_df_in):
            output = BytesIO()
            # try xlsxwriter/openpyxl via pandas
            try:
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    ref_df_in.to_excel(writer, index=False, sheet_name='Reference Table')
                    bill_df_in.to_excel(writer, index=False, sheet_name='Billing Components')
                return output.getvalue()
            except Exception:
                # fallback: write CSVs into a zip-like approach isn't necessary; just return None
                return None

        xlsx_data = to_excel_bytes(ref_df_edited, billing_df)

        st.download_button(
            label="⬇️ Download Reference Table (CSV)",
            data=csv_ref,
            file_name="reference_table.csv",
            mime="text/csv"
        )
        st.download_button(
            label="⬇️ Download Billing Components (CSV)",
            data=csv_bill,
            file_name="billing_components.csv",
            mime="text/csv"
        )
        if xlsx_data:
            st.download_button(
                label="⬇️ Download All (Excel)",
                data=xlsx_data,
                file_name="Electricity_LandedRate_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Excel export not available in this environment (xlsx writer missing). CSVs are available.")

    else:
        st.info("No months selected. Tick the 'Calc' column before running.")

# Footer
st.markdown("---")
st.caption("Export buttons support CSV & Excel formats. Multi-range slabs and per-month constants handled automatically.")





