# yearly_landed_rate.py
import streamlit as st
import pandas as pd
from io import BytesIO
from typing import List, Tuple

st.set_page_config(page_title="Yearly Landed Unit Rate Calculator2", layout="wide", page_icon="⚡")
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
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
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
# Helper functions for overlap
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
# Energy Rate Settings Section
# -----------------------------
st.markdown("### ⚙️ Energy Rate Settings")
col1, col2 = st.columns(2)
with col1:
    energy_rate_1 = st.number_input("Energy Rate (₹/kVAh) for **Jan–Mar**", value=8.68, step=0.01)
with col2:
    energy_rate_2 = st.number_input("Energy Rate (₹/kVAh) for **Apr–Dec**", value=8.90, step=0.01)


# -----------------------------
# Reference Table
# -----------------------------
st.markdown("## Reference Table")
def default_row(month_name):
    # pick which energy rate to use automatically
    energy_rate = energy_rate_1 if month_name in ["January", "February", "March"] else energy_rate_2
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
        "ToD_ratio_A": DEFAULT_TOD_RATIOS["A"],
        "ToD_ratio_B": DEFAULT_TOD_RATIOS["B"],
        "ToD_ratio_C": DEFAULT_TOD_RATIOS["C"],
        "ToD_ratio_D": DEFAULT_TOD_RATIOS["D"],
        "ToD_mul_A": 0.0,
        "ToD_mul_B": 0.0,
        "ToD_mul_C": -2.17,
        "ToD_mul_D": 2.17,
        "NewRange_A": "00:00-06:00",
        "NewRange_B": "06:00-09:00",
        "NewRange_C": "09:00-17:00",
        "NewRange_D": "17:00-00:00",
    }

ref_df = pd.DataFrame([default_row(m) for m in MONTHS])

# Columns to hide from user
hidden_cols = [f"ToD_ratio_{k}" for k in "ABCD"]
ref_df_display = ref_df.drop(columns=hidden_cols)

# Show editable version (horizontal layout)
ref_df_display_edited = st.data_editor(
    ref_df_display,
    num_rows="fixed",
    use_container_width=True,
    key="ref_table_editor",
)

# Restore hidden columns (unchanged)
ref_df_edited = ref_df_display_edited.copy()
for col in hidden_cols:
    ref_df_edited[col] = ref_df[col]


# -----------------------------
# Run calculations
# -----------------------------
if st.button("Run Calculations for checked months"):
    billing_rows = []

    for _, row in ref_df_edited.iterrows():
        if not bool(row["Calc"]):
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
        new_ranges = {k: parse_multi_ranges_input(row[f"NewRange_{k}"]) for k in "ABCD"}

        # 1️⃣ Base Charges
        DC = max_demand * DC_rate
        EC = units * energy_rate

        # 2️⃣ Old ToD Units
        OldUnits = {k: units * (ratios[k] / 100.0) for k in "ABCD"}

        # 3️⃣ Redistribute based on overlaps
        NewUnits = {k: 0.0 for k in "ABCD"}
        for old_k, old_segments in OLD_SLAB_TIMINGS.items():
            old_dur = sum(
                (parse_time(e) - parse_time(s)) % 24 for s, e in old_segments
            )
            for new_k, new_segs in new_ranges.items():
                overlap = total_overlap_hours_multi(
                    [parse_range_str(f"{s}-{e}") for s, e in old_segments], new_segs
                )
                NewUnits[new_k] += OldUnits[old_k] * (overlap / old_dur if old_dur > 0 else 0)

        # 4️⃣ ToD Charges
        ToD_charge = sum(NewUnits[k] * tod_multipliers[k] for k in "ABCD")

        # 5️⃣ Other Charges
        FAC = units * FAC_rate
        ED = (ED_percent / 100.0) * (DC + EC + FAC + ToD_charge)
        ToS = (units * 0.997) * ToS_rate

        kWh = units * 0.997
        ICR = ((kWh - 4044267) * (-0.75))

        def BCR_fn(units):
            if units <= 900000:
                return -(units * 0.07)
            elif units <= 5000000:
                return -(900000 * 0.07 + (units - 900000) * 0.09)
            else:
                return -(900000 * 0.07 + 4100000 * 0.09 + (units - 5000000) * 0.11)

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
        billing_df = billing_df.round(2)
        st.markdown("## Billing Components")
        st.dataframe(billing_df, use_container_width=True)

        # -----------------------------
        # Export Buttons
        # -----------------------------
        st.markdown("### 📤 Export Results")

        csv_ref = ref_df_edited.to_csv(index=False).encode('utf-8')
        csv_bill = billing_df.to_csv(index=False).encode('utf-8')

        def to_excel(ref_df, bill_df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                ref_df.to_excel(writer, index=False, sheet_name='Reference Table')
                bill_df.to_excel(writer, index=False, sheet_name='Billing Components')
            return output.getvalue()

        xlsx_data = to_excel(ref_df_edited, billing_df)

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
        st.download_button(
            label="⬇️ Download All (Excel)",
            data=xlsx_data,
            file_name="Electricity_LandedRate_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.info("No months selected. Tick the 'Calc' column before running.")

# Footer
st.markdown("---")
st.caption("Export buttons support CSV & Excel formats.")






