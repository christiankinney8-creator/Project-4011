import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="Advanced DCF Valuation Tool", layout="wide")

st.title("📊 Advanced DCF Valuation Model")

# =========================================================
# INPUT HELPERS
# =========================================================
def pct(x): 
    return x / 100

# =========================================================
# SIDEBAR INPUTS
# =========================================================
st.sidebar.header("🔧 Model Inputs")

# -------------------------
# Core Inputs
# -------------------------
revenue0 = st.sidebar.number_input("Starting Revenue ($M)", value=1000.0, step=50.0)

# -------------------------
# Growth Assumptions
# -------------------------
st.sidebar.subheader("📈 Growth Assumptions")

growth_stage1 = pct(
    st.sidebar.number_input("High Growth Rate (%)", value=8.0, step=0.5)
)

growth_stage2 = pct(
    st.sidebar.number_input("Stable Growth Rate (%)", value=2.5, step=0.1)
)

high_growth_years = st.sidebar.number_input(
    "High Growth Period (Years)", min_value=1, max_value=20, value=5, step=1
)

# -------------------------
# Operating Assumptions
# -------------------------
st.sidebar.subheader("💰 Operating Assumptions")

ebit_margin = pct(
    st.sidebar.number_input("EBIT Margin (%)", value=22.0, step=0.5)
)

tax_rate = pct(
    st.sidebar.number_input("Tax Rate (%)", value=21.0, step=0.5)
)

model_type = st.sidebar.selectbox(
    "Reinvestment Method",
    ["Reinvestment Rate", "CapEx + Working Capital"]
)

reinvestment_rate = pct(
    st.sidebar.number_input("Reinvestment Rate (% of NOPAT)", value=50.0, step=1.0)
)

capex_rate = pct(
    st.sidebar.number_input("CapEx (% of Revenue)", value=6.0, step=0.5)
)

wc_rate = pct(
    st.sidebar.number_input("Working Capital (% of Revenue)", value=2.0, step=0.5)
)

# -------------------------
# Discount Rate
# -------------------------
st.sidebar.subheader("📉 Discount Rate")

wacc = pct(
    st.sidebar.number_input("WACC (%)", value=9.5, step=0.25)
)

# -------------------------
# Capital Structure
# -------------------------
st.sidebar.subheader("🏦 Capital Structure")

net_debt = st.sidebar.number_input("Net Debt ($M)", value=500.0, step=25.0)
cash = st.sidebar.number_input("Cash ($M)", value=100.0, step=25.0)
shares = st.sidebar.number_input("Shares Outstanding (M)", value=100.0, step=1.0)

# =========================================================
# VALIDATION
# =========================================================
if wacc <= growth_stage2:
    st.error("WACC must be greater than terminal growth rate.")
    st.stop()

# =========================================================
# MODEL SETUP
# =========================================================
total_years = int(high_growth_years + 5)

# =========================================================
# PROJECTIONS
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
            reinvestment = revenue * (capex_rate + wc_rate)

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
# RUN MODEL
# =========================================================
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
# INTERPRETATION
# =========================================================
st.subheader("📊 Interpretation")

st.write(
    f"Intrinsic value estimate: **${value_per_share:.2f} per share**."
)

if value_per_share > 1:
    st.success("Model suggests potential undervaluation (relative to $1 benchmark).")
else:
    st.warning("Model suggests limited upside under current assumptions.")

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
    st.warning("High terminal value dependence → highly sensitive model.")
elif tv_weight < 0.5:
    st.success("Strong value creation in explicit forecast period.")

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
        if w <= g:
            sens.loc[f"{g:.2%}", f"{w:.2%}"] = np.nan
            continue

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
**DCF Structure:**

1. Revenue growth (2-stage model)  
2. EBIT → NOPAT conversion  
3. Free cash flow generation  
4. Discount using WACC  
5. Terminal value (Gordon Growth Model)  
6. Equity value = EV − Net Debt + Cash  

> Intrinsic value = present value of future free cash flows
""")
