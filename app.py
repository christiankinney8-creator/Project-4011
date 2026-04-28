import streamlit as st
import numpy as np
import pandas as pd

st.title("📊 DCF Valuation App")

# -----------------------------
# Sidebar Inputs
# -----------------------------
st.sidebar.header("🔧 Inputs")

# Basic Inputs
revenue = st.sidebar.number_input("Current Revenue ($)", value=1000.0)

st.sidebar.subheader("Growth Assumptions")
growth_high = st.sidebar.number_input("High Growth Rate (%)", value=6.0) / 100
growth_stable = st.sidebar.number_input("Terminal Growth Rate (%)", value=2.5) / 100
high_growth_years = st.sidebar.slider("High Growth Period (Years)", 1, 10, 5)

st.sidebar.subheader("Operating Assumptions")
margin = st.sidebar.number_input("EBIT Margin (%)", value=20.0) / 100
tax_rate = st.sidebar.number_input("Tax Rate (%)", value=25.0) / 100
reinvest = st.sidebar.number_input("Reinvestment Rate (%)", value=50.0) / 100

st.sidebar.subheader("Discounting")
wacc = st.sidebar.number_input("WACC (%)", value=10.0) / 100

st.sidebar.subheader("Balance Sheet")
debt = st.sidebar.number_input("Debt ($)", value=500.0)
cash = st.sidebar.number_input("Cash ($)", value=100.0)
shares = st.sidebar.number_input("Shares Outstanding", value=100.0)

# Validation
if wacc <= growth_stable:
    st.error("WACC must be greater than terminal growth rate.")
    st.stop()

# -----------------------------
# Projection
# -----------------------------
years = high_growth_years + 5

revenues, ebits, nopats, fcfs = [], [], [], []
rev = revenue

for t in range(years):
    growth = growth_high if t < high_growth_years else growth_stable
    rev *= (1 + growth)

    ebit = rev * margin
    nopat = ebit * (1 - tax_rate)
    reinvestment = nopat * reinvest
    fcf = nopat - reinvestment

    revenues.append(rev)
    ebits.append(ebit)
    nopats.append(nopat)
    fcfs.append(fcf)

# -----------------------------
# Discounting
# -----------------------------
discount_factors = [(1 / (1 + wacc) ** (t + 1)) for t in range(years)]
pv_fcfs = [fcf * df for fcf, df in zip(fcfs, discount_factors)]

terminal_value = fcfs[-1] * (1 + growth_stable) / (wacc - growth_stable)
pv_terminal = terminal_value / ((1 + wacc) ** years)

enterprise_value = sum(pv_fcfs) + pv_terminal
equity_value = enterprise_value - debt + cash
value_per_share = equity_value / shares

# -----------------------------
# Output
# -----------------------------
st.header("📈 Valuation Results")

col1, col2, col3 = st.columns(3)
col1.metric("Enterprise Value", f"${enterprise_value:,.2f}")
col2.metric("Equity Value", f"${equity_value:,.2f}")
col3.metric("Value per Share", f"${value_per_share:,.2f}")

# Interpretation
st.subheader("📊 Interpretation")
if value_per_share > 0:
    st.write(f"Estimated intrinsic value suggests the stock is **{'undervalued' if value_per_share > 1 else 'overvalued'}** based on your assumptions.")

# -----------------------------
# Data Table
# -----------------------------
df = pd.DataFrame({
    "Year": np.arange(1, years + 1),
    "Revenue": revenues,
    "EBIT": ebits,
    "NOPAT": nopats,
    "FCF": fcfs,
    "Discount Factor": discount_factors,
    "PV of FCF": pv_fcfs
})

st.subheader("📋 Projection Table")
st.dataframe(df)

# -----------------------------
# Chart
# -----------------------------
st.subheader("📉 FCF Projection")
st.line_chart(df.set_index("Year")["FCF"])

# -----------------------------
# Sensitivity Analysis (Simple)
# -----------------------------
st.subheader("🔥 Sensitivity Analysis")

wacc_range = [wacc - 0.01, wacc, wacc + 0.01]
growth_range = [growth_stable - 0.005, growth_stable, growth_stable + 0.005]

sens = pd.DataFrame(index=[f"{g:.2%}" for g in growth_range],
                    columns=[f"{w:.2%}" for w in wacc_range])

for g in growth_range:
    for w in wacc_range:
        tv = fcfs[-1] * (1 + g) / (w - g)
        pv_tv = tv / ((1 + w) ** years)
        ev = sum([fcfs[i] / ((1 + w) ** (i+1)) for i in range(years)]) + pv_tv
        eq = ev - debt + cash
        sens.loc[f"{g:.2%}", f"{w:.2%}"] = round(eq / shares, 2)

st.dataframe(sens)

# -----------------------------
# Explanation
# -----------------------------
st.subheader("📘 Model Explanation")

st.markdown("""
- Revenue grows in two stages: high growth → stable growth  
- EBIT = Revenue × Margin  
- NOPAT = EBIT × (1 - Tax Rate)  
- FCF = NOPAT - Reinvestment  
- Terminal Value uses Gordon Growth Model  
- All cash flows are discounted using WACC  

This structure is fully replicable in Excel.
""")
