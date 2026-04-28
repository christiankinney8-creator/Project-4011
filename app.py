import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="Advanced DCF Valuation Tool", layout="wide")

st.title("📊 Advanced DCF Valuation Model")

# =========================================================
# SIDEBAR INPUTS
# =========================================================
st.sidebar.header("🔧 Model Inputs")

# Core
revenue0 = st.sidebar.number_input("Starting Revenue ($M)", value=1000.0)

# Growth
st.sidebar.subheader("📈 Growth Assumptions")
growth_stage1 = st.sidebar.slider("High Growth Rate (%)", 0.0, 25.0, 8.0) / 100
growth_stage2 = st.sidebar.slider("Stable Growth Rate (%)", 0.0, 6.0, 2.5) / 100
high_growth_years = st.sidebar.slider("High Growth Period (Years)", 1, 15, 5)

# Profitability
st.sidebar.subheader("💰 Operating Assumptions")
ebit_margin = st.sidebar.slider("EBIT Margin (%)", 5.0, 60.0, 22.0) / 100
tax_rate = st.sidebar.slider("Tax Rate (%)", 0.0, 40.0, 21.0) / 100

# Reinvestment vs CapEx approach toggle
model_type = st.sidebar.selectbox(
    "Reinvestment Method",
    ["Reinvestment Rate", "CapEx + Working Capital"]
)

reinvestment_rate = st.sidebar.slider("Reinvestment Rate (% of NOPAT)", 0.0, 100.0, 50.0) / 100

capex_rate = st.sidebar.slider("CapEx (% of Revenue)", 0.0, 20.0, 6.0) / 100
wc_rate = st.sidebar.slider("Working Capital (% of Revenue)", 0.0, 10.0, 2.0) / 100

# Discount rate
st.sidebar.subheader("📉 Discounting")
wacc = st.sidebar.slider("WACC (%)", 5.0, 20.0, 9.5) / 100

# Capital structure
st.sidebar.subheader("🏦 Capital Structure")
net_debt = st.sidebar.number_input("Net Debt ($M)", value=500.0)
cash = st.sidebar.number_input("Cash ($M)", value=100.0)
shares = st.sidebar.number_input("Shares Outstanding (M)", value=100.0)

# =========================================================
# VALIDATION
# =========================================================
if wacc <= growth_stage2:
    st.error("WACC must be greater than terminal growth rate.")
    st.stop()

# =========================================================
# MODEL FUNCTIONS
# =========================================================
def project_cash_flows():
    revenue = revenue0
    revenues, fcfs = [], []

    for t in range(total_years):
        g = growth_stage1 if t < high_growth_years else growth_stage2
        revenue *= (1 + g)

        ebit = revenue * ebit_margin
        nopat = ebit * (1 - tax_rate)

        if model_type == "Reinvestment Rate":
            reinvestment = nopat * reinvestment_rate
        else:
            capex = revenue * capex_rate
            wc = revenue * wc_rate
            reinvestment = capex + wc

        fcf = nopat - reinvestment

        revenues.append(revenue)
        fcfs.append(fcf)

    return revenues, fcfs


def discount(fcfs):
    dfs = [(1 / (1 + wacc) ** (i + 1)) for i in range(len(fcfs))]
    pv = [f * d for f, d in zip(fcfs, dfs)]
    return dfs, pv


def terminal_value(last_fcf):
    return last_fcf * (1 + growth_stage2) / (wacc - growth_stage2)

# =========================================================
# PROJECTION
# =========================================================
total_years = high_growth_years + 5

revenues, fcfs = project_cash_flows()
discount_factors, pv_fcfs = discount(fcfs)

tv = terminal_value(fcfs[-1])
pv_tv = tv / ((1 + wacc) ** total_years)

enterprise_value = sum(pv_fcfs) + pv_tv
equity_value = enterprise_value - net_debt + cash
value_per_share = equity_value / shares

# =========================================================
# OUTPUT
# =========================================================
st.header("📈 Valuation Results")

c1, c2, c3 = st.columns(3)
c1.metric("Enterprise Value ($M)", f"{enterprise_value:,.1f}")
c2.metric("Equity Value ($M)", f"{equity_value:,.1f}")
c3.metric("Value / Share ($)", f"{value_per_share:,.2f}")

# =========================================================
# INSIGHT
# =========================================================
st.subheader("📊 Interpretation")

if value_per_share > 0:
    st.write(
        f"Based on inputs, intrinsic value is **${value_per_share:.2f} per share**. "
        f"This suggests the stock is {'undervalued' if value_per_share > 1 else 'potentially overvalued'} under current assumptions."
    )

st.write("""
DCF models are highly sensitive to:
- Growth assumptions  
- WACC (discount rate)  
- Terminal value assumptions  
- Reinvestment intensity  
""")

# =========================================================
# TABLE
# =========================================================
df = pd.DataFrame({
    "Year": np.arange(1, total_years + 1),
    "Revenue ($M)": revenues,
    "FCF ($M)": fcfs,
    "Discount Factor": discount_factors,
    "PV of FCF ($M)": pv_fcfs
})

st.header("📋 Projection Breakdown")
st.dataframe(df, use_container_width=True)

# =========================================================
# CHARTS
# =========================================================
st.header("📉 Cash Flow Trend")
st.line_chart(df.set_index("Year")[["FCF ($M)", "Revenue ($M)"]])

# =========================================================
# TERMINAL VALUE INSIGHT
# =========================================================
st.header("🔮 Terminal Value Breakdown")

tv_weight = pv_tv / enterprise_value

st.write(f"Terminal value contributes **{tv_weight:.1%}** of total value.")

if tv_weight > 0.7:
    st.warning("High terminal value dependence → model is highly assumption-sensitive.")
elif tv_weight < 0.5:
    st.success("More value driven by explicit forecast period → stronger near-term model integrity.")

# =========================================================
# SENSITIVITY ANALYSIS
# =========================================================
st.header("🔥 Sensitivity Analysis (Equity Value / Share)")

wacc_range = [wacc - 0.01, wacc, wacc + 0.01]
growth_range = [growth_stage2 - 0.005, growth_stage2, growth_stage2 + 0.005]

sens = pd.DataFrame(
    index=[f"{g:.2%}" for g in growth_range],
    columns=[f"{w:.2%}" for w in wacc_range]
)

for g in growth_range:
    for w in wacc_range:
        tv_s = fcfs[-1] * (1 + g) / (w - g)
        pv_tv_s = tv_s / ((1 + w) ** total_years)
        ev_s = sum([fcfs[i] / ((1 + w) ** (i + 1)) for i in range(total_years)]) + pv_tv_s
        eq_s = ev_s - net_debt + cash
        sens.loc[f"{g:.2%}", f"{w:.2%}"] = round(eq_s / shares, 2)

st.dataframe(sens)

# =========================================================
# MODEL EXPLANATION
# =========================================================
st.header("🧠 Model Logic")

st.markdown("""
This advanced DCF model uses:

### 1. Revenue Forecasting
Two-stage growth (high growth → stable growth)

### 2. Operating Conversion
EBIT → NOPAT using tax adjustments

### 3. Cash Flow Construction
Two methods:
- Reinvestment Rate (NOPAT-based)
- CapEx + Working Capital approach

### 4. Valuation
- Discount FCFF using WACC  
- Terminal value via Gordon Growth Model  

### 5. Equity Value
Enterprise Value − Net Debt + Cash  

---

### Key Idea:
> Intrinsic value = Present value of all future free cash flows
""")
