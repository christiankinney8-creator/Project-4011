import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Equity Valuation Tool", layout="wide")

st.title("📊 Equity Valuation Dashboard (DCF Model)")
st.write(
    "This tool estimates a company’s intrinsic value by forecasting cash flows "
    "and discounting them back to present value using an appropriate risk-adjusted rate."
)

# -----------------------------
# INPUT PANEL
# -----------------------------
st.sidebar.header("📌 Model Inputs")

# Core assumptions
base_revenue = st.sidebar.number_input("Starting Revenue ($M)", value=1200.0)
growth_stage1 = st.sidebar.slider("Initial Growth Rate (%)", 0.0, 20.0, 7.0) / 100
growth_stage2 = st.sidebar.slider("Long-Term Growth Rate (%)", 0.0, 5.0, 2.5) / 100
transition_years = st.sidebar.slider("High-Growth Period (Years)", 1, 10, 5)

# Operating assumptions
operating_margin = st.sidebar.slider("Operating Margin (%)", 5.0, 60.0, 22.0) / 100
tax = st.sidebar.slider("Effective Tax Rate (%)", 0.0, 40.0, 21.0) / 100

# Cash flow adjustments
capex_rate = st.sidebar.slider("CapEx (% of Revenue)", 0.0, 15.0, 6.0) / 100
wc_rate = st.sidebar.slider("Working Capital (% of Revenue)", 0.0, 10.0, 2.0) / 100

# Discounting
discount_rate = st.sidebar.slider("Discount Rate (WACC %)", 5.0, 15.0, 9.5) / 100

# Capital structure
net_debt = st.sidebar.number_input("Net Debt ($M)", value=600.0)
shares_out = st.sidebar.number_input("Shares Outstanding (M)", value=150.0)

# -----------------------------
# MODEL OVERVIEW
# -----------------------------
st.header("🧠 Model Logic Overview")

st.markdown("""
This valuation model follows a **multi-stage Discounted Cash Flow (DCF)** approach:

1. Forecast revenue using a two-stage growth model  
2. Convert revenue into operating profit  
3. Adjust for taxes and reinvestment needs  
4. Discount projected cash flows using WACC  
5. Estimate terminal value beyond explicit forecast period  
6. Derive enterprise and equity value  

DCF reflects the principle that **a company is worth the present value of its future cash flows**.
""")

# -----------------------------
# PROJECTION ENGINE
# -----------------------------
years = transition_years + 5

revenue_list = []
fcf_list = []

rev = base_revenue

for t in range(years):
    g = growth_stage1 if t < transition_years else growth_stage2
    rev = rev * (1 + g)

    ebit = rev * operating_margin
    nopat = ebit * (1 - tax)

    capex = rev * capex_rate
    wc_invest = rev * wc_rate

    fcf = nopat - capex - wc_invest

    revenue_list.append(rev)
    fcf_list.append(fcf)

# -----------------------------
# DISCOUNTING
# -----------------------------
discount_factors = [(1 / (1 + discount_rate) ** (i + 1)) for i in range(years)]
pv_fcf = [f * d for f, d in zip(fcf_list, discount_factors)]

terminal_fcf = fcf_list[-1]
terminal_value = terminal_fcf * (1 + growth_stage2) / (discount_rate - growth_stage2)
pv_terminal = terminal_value / ((1 + discount_rate) ** years)

enterprise_value = sum(pv_fcf) + pv_terminal
equity_value = enterprise_value - net_debt
intrinsic_value = equity_value / shares_out

# -----------------------------
# OUTPUT SECTION
# -----------------------------
st.header("📈 Valuation Summary")

c1, c2, c3 = st.columns(3)

c1.metric("Enterprise Value ($M)", f"{enterprise_value:,.1f}")
c2.metric("Equity Value ($M)", f"{equity_value:,.1f}")
c3.metric("Intrinsic Value / Share", f"${intrinsic_value:,.2f}")

# -----------------------------
# INTERPRETATION
# -----------------------------
st.subheader("📊 Investment Insight")

st.write(
    f"The model estimates a fair value of **${intrinsic_value:.2f} per share** based on current assumptions."
)

st.write("""
DCF outputs are highly sensitive to:
- Growth assumptions  
- Discount rate (risk perception)  
- Long-term terminal assumptions  
""")

# -----------------------------
# TABLE OUTPUT
# -----------------------------
df = pd.DataFrame({
    "Year": np.arange(1, years + 1),
    "Revenue ($M)": revenue_list,
    "FCF ($M)": fcf_list,
    "Discount Factor": discount_factors,
    "PV of FCF ($M)": pv_fcf
})

st.header("📋 Forecast Breakdown")
st.dataframe(df, use_container_width=True)

# -----------------------------
# VISUALIZATION
# -----------------------------
st.header("📉 Cash Flow Trend")

st.line_chart(df.set_index("Year")[["FCF ($M)", "Revenue ($M)"]])

# -----------------------------
# TERMINAL VALUE INSIGHT
# -----------------------------
st.header("🔮 Terminal Value Importance")

tv_share = pv_terminal / enterprise_value

st.write(
    f"Terminal value represents approximately **{tv_share:.1%}** of total firm value."
)

if tv_share > 0.7:
    st.warning("High reliance on terminal value → results are more assumption-sensitive.")
elif tv_share < 0.5:
    st.success("More value comes from explicit forecasts → model is more grounded in near-term cash flows.")

# -----------------------------
# FINAL SUMMARY
# -----------------------------
st.header("🎯 Key Takeaways")

st.write(f"""
- Intrinsic value estimate: **${intrinsic_value:.2f} per share**  
- Model uses a **two-stage growth DCF framework**  
- Output is highly sensitive to WACC ({discount_rate:.1%}) and terminal growth ({growth_stage2:.1%})  
- Always interpret DCF as a **range of outcomes, not a single precise value**  
""")
