import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf

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
# TICKER INPUT
# -------------------------
ticker = st.sidebar.text_input("Stock Ticker (e.g. AAPL)", value="AAPL").upper()
use_live_data = st.sidebar.checkbox("Use Live Financial Data", value=False)

# -------------------------
# LOAD DATA
# -------------------------
if use_live_data and ticker:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        revenue0 = info.get("totalRevenue", 1e9) / 1e6
        shares = info.get("sharesOutstanding", 1e8) / 1e6
        cash = info.get("totalCash", 0) / 1e6
        net_debt = (info.get("totalDebt", 0) - info.get("totalCash", 0)) / 1e6

        price = stock.history(period="1d")["Close"].iloc[-1]

        st.sidebar.success(f"Loaded data for {ticker}")

    except:
        st.sidebar.error("Failed to fetch data. Using manual inputs.")
        use_live_data = False

# -------------------------
# MANUAL INPUTS (fallback)
# -------------------------
if not use_live_data:
    revenue0 = st.sidebar.number_input("Starting Revenue ($M)", value=1000.0, step=50.0)
    net_debt = st.sidebar.number_input("Net Debt ($M)", value=500.0, step=25.0)
    cash = st.sidebar.number_input("Cash ($M)", value=100.0, step=25.0)
    shares = st.sidebar.number_input("Shares Outstanding (M)", value=100.0, step=1.0)
else:
    st.sidebar.write(f"Revenue: {revenue0:,.0f}M")
    st.sidebar.write(f"Net Debt: {net_debt:,.0f}M")
    st.sidebar.write(f"Cash: {cash:,.0f}M")
    st.sidebar.write(f"Shares: {shares:,.0f}M")

# -------------------------
# Growth Assumptions
# -------------------------
st.sidebar.subheader("📈 Growth Assumptions")

growth_stage1 = pct(st.sidebar.number_input("High Growth Rate (%)", value=8.0, step=0.5))
growth_stage2 = pct(st.sidebar.number_input("Stable Growth Rate (%)", value=2.5, step=0.1))

high_growth_years = st.sidebar.number_input(
    "High Growth Period (Years)", min_value=1, max_value=20, value=5
)

# -------------------------
# Operating Assumptions
# -------------------------
st.sidebar.subheader("💰 Operating Assumptions")

ebit_margin = pct(st.sidebar.number_input("EBIT Margin (%)", value=22.0, step=0.5))
tax_rate = pct(st.sidebar.number_input("Tax Rate (%)", value=21.0, step=0.5))

model_type = st.sidebar.selectbox(
    "Reinvestment Method",
    ["Reinvestment Rate", "CapEx + Working Capital"]
)

reinvestment_rate = pct(st.sidebar.number_input("Reinvestment Rate (% of NOPAT)", value=50.0))
capex_rate = pct(st.sidebar.number_input("CapEx (% of Revenue)", value=6.0))
wc_rate = pct(st.sidebar.number_input("Working Capital (% of Revenue)", value=2.0))

# -------------------------
# Discount Rate
# -------------------------
st.sidebar.subheader("📉 Discount Rate")

wacc = pct(st.sidebar.number_input("WACC (%)", value=9.5, step=0.25))

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

# Show market price if available
if use_live_data:
    st.metric("Current Stock Price", f"${price:.2f}")

# =========================================================
# INTERPRETATION
# =========================================================
st.subheader("📊 Interpretation")

st.write(f"Intrinsic value estimate: **${value_per_share:.2f} per share**.")

if use_live_data:
    if value_per_share > price:
        st.success("Stock appears undervalued vs market price")
    else:
        st.warning("Stock appears overvalued vs market price")

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

# =========================================================
# SENSITIVITY
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
