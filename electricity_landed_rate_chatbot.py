import streamlit as st
import pandas as pd

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
TARIFF_KEYS = ["April 2025", "June 2025", "July 2025", "August 2025", "September 2025"]

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
# Left column: Inputs & calculation
# -----------------------------
with left_col:
    st.header("1️⃣ Inputs")

    col1, col2 = st.columns(2)
    with col1:
        month_year = st.selectbox("Select Month & Year", options=TARIFF_KEYS)
        units_kvah = st.number_input("Total energy consumption (kVAh)", min_value=0.0, step=100.0, value=500000.0, format="%.2f")
    with col2:
        max_demand_kva = st.number_input("Maximum demand (kVA)", min_value=0.0, step=1.0, value=1200.0, format="%.2f")

    st.markdown("---")
    st.header("2️⃣ Time-of-Day (ToD) Slab Ratios (percent of total kVAh)")
    rcol1, rcol2 = st.columns(2)
    with rcol1:
        slab_A = st.number_input("Slab A (%) [22:00–06:00]", min_value=0.0, max_value=100.0, value=25.0)
        slab_B = st.number_input("Slab B (%) [06:00–09:00 & 12:00–18:00]", min_value=0.0, max_value=100.0, value=25.0)
    with rcol2:
        slab_C = st.number_input("Slab C (%) [09:00–12:00]", min_value=0.0, max_value=100.0, value=25.0)
        slab_D = st.number_input("Slab D (%) [18:00–22:00]", min_value=0.0, max_value=100.0, value=25.0)

    total_ratio = slab_A + slab_B + slab_C + slab_D
    if total_ratio != 100:
        st.warning("⚠️ The slab ratios should add up to 100%. Current total: {:.2f}%".format(total_ratio))

    st.markdown("---")
    st.header("3️⃣ ToD Multipliers")
    st.markdown(
        "Enter ToD multipliers as percentage adjustments relative to the energy rate.\n"
        "Example: `-1.5` means -1.5% adjustment for that slab; `1.1` means +1.1%."
    )
    mcol1, mcol2 = st.columns(2)
    with mcol1:
        tod_A = st.number_input("ToD Multiplier A (e.g., -1.5)", value=-1.5, format="%.3f")
        tod_B = st.number_input("ToD Multiplier B (e.g., 0)", value=0.0, format="%.3f")
    with mcol2:
        tod_C = st.number_input("ToD Multiplier C (e.g., 0.8)", value=0.8, format="%.3f")
        tod_D = st.number_input("ToD Multiplier D (e.g., 1.1)", value=1.1, format="%.3f")

    st.markdown("---")
    st.header("4️⃣ Energy Rate")
    new_energy_rate = st.number_input("New Energy Rate (₹ per kVAh)", min_value=0.0, step=0.01, value=7.48, format="%.4f")

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
            DC = max_demand_kva * DC_rate

            # --- 2. Base Energy Charge (EC) ---
            EC = units_kvah * new_energy_rate

            # --- 3. ToD charge calculation ---
            A_units = units_kvah * (slab_A / 100.0)
            B_units = units_kvah * (slab_B / 100.0)
            C_units = units_kvah * (slab_C / 100.0)
            D_units = units_kvah * (slab_D / 100.0)

            # Interpreting ToD multipliers as percent adjustments relative to energy rate:
            # ToD contribution in ₹ = (units_in_slab * (multiplier_percentage / 100)) * energy_rate
            ToD_A = (A_units * (tod_A / 100.0)) * new_energy_rate
            ToD_B = (B_units * (tod_B / 100.0)) * new_energy_rate
            ToD_C = (C_units * (tod_C / 100.0)) * new_energy_rate
            ToD_D = (D_units * (tod_D / 100.0)) * new_energy_rate
            ToD_charge = ToD_A + ToD_B + ToD_C + ToD_D

            # --- 4. Other charges ---
            FAC = units_kvah * FAC_rate
            ED = (ED_percent / 100.0) * (DC + EC + FAC + ToD_charge)
            ToS = units_kvah * ToS_rate

            # --- 5. Total and landed rate ---
            Total = DC + EC + ToD_charge + FAC + ED + ToS
            LandedRate = Total / units_kvah

            # Display output (main summary)
            st.success("✅ Calculation complete")
            st.metric(label="⚡ Landed Unit Rate (₹ / kWh)", value=f"{LandedRate:,.4f}")
            st.markdown("**Total bill (₹):** {:,.2f}".format(Total))

            # Collapsible detailed breakdown
            with st.expander("Show detailed breakdown"):
                st.subheader("Detailed cost breakdown")
                st.write(f"**Month & Year:** {month_year}")
                st.write(f"**Total units (kVAh):** {units_kvah:,.2f}")
                st.write(f"**Maximum demand (kVA):** {max_demand_kva:,.2f}")
                st.write("---")
                st.write(f"**Demand Charge (DC):** ₹ {DC:,.2f}  (DC_rate = ₹{DC_rate:.2f} per kVA)")
                st.write(f"**Energy Charge (EC):** ₹ {EC:,.2f}  (Energy rate = ₹{new_energy_rate:.4f} per kVAh)")
                st.write(f"**ToD Charge (A):** ₹ {ToD_A:,.2f} (A_units = {A_units:,.2f}, A_mult = {tod_A}%)")
                st.write(f"**ToD Charge (B):** ₹ {ToD_B:,.2f} (B_units = {B_units:,.2f}, B_mult = {tod_B}%)")
                st.write(f"**ToD Charge (C):** ₹ {ToD_C:,.2f} (C_units = {C_units:,.2f}, C_mult = {tod_C}%)")
                st.write(f"**ToD Charge (D):** ₹ {ToD_D:,.2f} (D_units = {D_units:,.2f}, D_mult = {tod_D}%)")
                st.write(f"**Total ToD charge:** ₹ {ToD_charge:,.2f}")
                st.write(f"**Fuel Adjustment (FAC):** ₹ {FAC:,.2f} (FAC_rate = ₹{FAC_rate:.4f} per kVAh)")
                st.write(f"**Electricity Duty (ED):** ₹ {ED:,.2f} (ED_percent = {ED_percent}%)")
                st.write(f"**Tax on Sale (ToS):** ₹ {ToS:,.2f} (ToS_rate = ₹{ToS_rate} per kWh)")
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
st.caption("Made for MSEDCL MYT style landed unit rate calculations. ToD multipliers are interpreted as percentage adjustments to the energy rate for that slab (e.g., -1.5 → -1.5%). Constants reset to defaults on page reload.")


