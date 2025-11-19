# yearly_landed_rate_cleaned.py
import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Yearly Landed Unit Rate Calculator", layout="wide", page_icon="⚡")
st.title("⚡ Yearly Landed Unit Rate Calculator")
st.markdown("Fill out the **Reference table** to calculate the **Landed Unit rate**.")

# -----------------------------
# Defaults (constants)
# -----------------------------
DEFAULT_CONSTANTS = {
    "Parameter": ["DC_rate", "FAC_rate", "ToS_rate", "ED_percent"],
    "Value": [600.0, 0.5, 0.18, 7.5],
}

DEFAULT_TOD_RATIOS = {"A": 18.86, "B": 7.35, "C": 27.95, "D": 45.83}

MONTHS = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

const_df = pd.DataFrame(DEFAULT_CONSTANTS)
GLOBAL_DC_rate     = float(const_df.loc[const_df["Parameter"] == "DC_rate", "Value"])
GLOBAL_FAC_rate    = float(const_df.loc[const_df["Parameter"] == "FAC_rate", "Value"])
GLOBAL_ToS_rate    = float(const_df.loc[const_df["Parameter"] == "ToS_rate", "Value"])
GLOBAL_ED_percent  = float(const_df.loc[const_df["Parameter"] == "ED_percent", "Value"])

# -----------------------------
# Energy Rate Settings
# -----------------------------
st.markdown("### ⚙️ Energy Rate Settings")
col1, col2 = st.columns(2)
with col1:
    energy_rate_1 = st.number_input("Energy Rate (₹/kVAh) for Jan–Mar", value=8.68, step=0.01)
with col2:
    energy_rate_2 = st.number_input("Energy Rate (₹/kVAh) for Apr–Dec", value=8.90, step=0.01)

# -----------------------------
# Build Reference Table
# -----------------------------
st.markdown("## Reference Table (editable)")

def default_row(month_name):
    energy_rate = energy_rate_1 if month_name in ["January", "February", "March"] else energy_rate_2
    return {
        "Month": month_name,
        "Calc": False,
        "PF": 0.997,
        "MaxDemand_kVA": 13500.0,
        "kvah": 5000000.0,
        "EnergyRate_₹/kVAh": energy_rate,
        "DC_rate": GLOBAL_DC_rate,
        "FAC_rate": GLOBAL_FAC_rate,
        "ToS_rate": GLOBAL_ToS_rate,
        "ED_percent": GLOBAL_ED_percent,

        # ToD ratios (user editable)
        "ToD_ratio_A": DEFAULT_TOD_RATIOS["A"],
        "ToD_ratio_B": DEFAULT_TOD_RATIOS["B"],
        "ToD_ratio_C": DEFAULT_TOD_RATIOS["C"],
        "ToD_ratio_D": DEFAULT_TOD_RATIOS["D"],

        # ToD multipliers
        "ToD_mul_A": 0.0,
        "ToD_mul_B": 0.0,
        "ToD_mul_C": -2.17,
        "ToD_mul_D": 2.17,
    }

ref_df = pd.DataFrame([default_row(m) for m in MONTHS])

# Show editable table
ref_df_edited = st.data_editor(
    ref_df,
    num_rows="fixed",
    use_container_width=True,
    key="ref_table_editor",
)

# -----------------------------
# Run Calculations
# -----------------------------
if st.button("Run Calculations for checked months"):
    billing_rows = []

    for _, row in ref_df_edited.iterrows():

        if not bool(row["Calc"]):
            continue

        month = row["Month"]
        PF = float(row["PF"])
        max_demand = float(row["MaxDemand_kVA"])
        kvah = float(row["kvah"])
        kwh = kvah * PF  # Option A PF logic

        energy_rate = float(row["EnergyRate_₹/kVAh"])
        DC_rate = float(row["DC_rate"])
        FAC_rate = float(row["FAC_rate"])
        ToS_rate = float(row["ToS_rate"])
        ED_percent = float(row["ED_percent"])

        # ------------------------
        # Base Charges
        # ------------------------
        DC = max_demand * DC_rate
        EC = kvah * energy_rate
        FAC = kvah * FAC_rate

        # ------------------------
        # ToD Charges
        # ------------------------
        ratios = {
            "A": float(row["ToD_ratio_A"]) / 100.0,
            "B": float(row["ToD_ratio_B"]) / 100.0,
            "C": float(row["ToD_ratio_C"]) / 100.0,
            "D": float(row["ToD_ratio_D"]) / 100.0,
        }

        multipliers = {
            "A": float(row["ToD_mul_A"]),
            "B": float(row["ToD_mul_B"]),
            "C": float(row["ToD_mul_C"]),
            "D": float(row["ToD_mul_D"]),
        }

        ToD_charge = 0
        for k in ["A", "B", "C", "D"]:
            slab_units = kvah * ratios[k]
            ToD_charge += slab_units * multipliers[k]

        # ------------------------
        # ED, ToS, BCR, ICR
        # ------------------------
        ED = (ED_percent / 100.0) * (DC + EC + FAC + ToD_charge)
        ToS = (kvah * PF) * ToS_rate

        if kwh > 4044267:
            ICR = (kwh - 4405453) * (-0.75)
        else:
            ICR = 0

        def BCR_fn(units):
            if units <= 900000:
                return -(units * 0.07)
            elif units <= 5000000:
                return -(900000 * 0.07 + (units - 900000) * 0.09)
            else:
                return -(900000 * 0.07 + 4100000 * 0.09 + (units - 5000000) * 0.11)

        BCR = BCR_fn(kwh)

        
        PPD = (DC + EC + FAC + ToD_charge) * (-0.01)
        Total = DC + EC + ToD_charge + FAC + ED + ToS + BCR + ICR + PPD
        LandedRate = Total / (kvah * PF)

        billing_rows.append({
            "Month": month,
            "kwh(kWh)": kwh,
            "DC": DC,
            "EC": EC,
            "ToD_charge": ToD_charge,
            "FAC": FAC,
            "ED": ED,
            "ToS": ToS,
            "BCR": BCR,
            "ICR": ICR,
            "PPD": PPD,
            "Total": Total,
            "LandedRate": LandedRate
        })

    if billing_rows:
        billing_df = pd.DataFrame(billing_rows).round(2)
        st.markdown("## Billing Components")
        st.dataframe(billing_df, use_container_width=True)

        # ------------------------
        # Export Buttons
        # ------------------------
        csv_ref = ref_df_edited.to_csv(index=False).encode("utf-8")
        csv_bill = billing_df.to_csv(index=False).encode("utf-8")

        def to_excel(ref_df, bill_df):
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                ref_df.to_excel(writer, index=False, sheet_name="Reference Table")
                bill_df.to_excel(writer, index=False, sheet_name="Billing Components")
            return buffer.getvalue()

        xlsx = to_excel(ref_df_edited, billing_df)

        st.download_button("Download Reference Table (CSV)", csv_ref, "reference.csv")
        st.download_button("Download Billing Components (CSV)", csv_bill, "billing.csv")
        st.download_button("Download Full Report (Excel)", xlsx, "Electricity_Report.xlsx")

    else:
        st.info("No months selected. Tick the 'Calc' column.")

# Footer
st.markdown("---")










