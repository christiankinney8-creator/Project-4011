import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf

st.set_page_config(layout="wide")
st.title("📊 Advanced DCF Valuation App")

# -----------------------------
# Sidebar Inputs
# -----------------------------
st.sidebar.header("🔧 Assumptions")

ticker = st.sidebar.text_input("Stock Ticker", value="AAPL")

# Pull market data
stock = yf.Ticker(ticker)
price = stock.history(period="1d")["Close"].iloc[-1]

st.sidebar.markdown(f"**Current Price:** ${price:.2f}")

# Financial assumptions
revenue = st.sidebar.number_input("Base Revenue ($M)", value=100000.0)

growth_high = st.sidebar.slider("High Growth (%)", 0.0, 20.0, 8.0) / 100
growth_stable = st.sidebar.slider("Terminal Growth (%)", 0.0, 5.0, 2.5) / 100

years_high = st.sidebar.slider("High Growth Years", 1, 10, 5)

margin = st.sidebar.slider("EBIT Margin (%)", 0.0, 50.0, 25.0) / 100
tax_rate = st.sidebar.slider("Tax Rate (%)", 0.0, 40.0, 21.0) / 100
reinvest = st.sidebar.slider("Reinvestment Rate (%)", 0.0, 100.0, 40.0) / 100

# WACC (CAPM)
risk_free = st.sidebar.slider("Risk-Free Rate (%)", 0.0, 10.0, 4.0) / 100
market_return = st.sidebar.slider("Market Return (%)", 5.0, 15.0, 10.0) / 100
beta = st.sidebar.slider("Beta", 0.5, 2.0, 1.1)

cost_of_equity = risk_free + beta * (market_return - risk_free)
wacc = st.sidebar.slider("Override WACC (%)", 0.0, 20.0, cost_of_equity * 100) / 100

st.sidebar.markdown(f"**CAPM Cost of Equity:** {cost_of_equity:.2%}")

# Capital structure
debt = st.sidebar.number_input("Debt ($M)", value=50000.0)
cash = st.sidebar.number_input("Cash ($M)", value=20000.0)
shares = st.sidebar.number_input("Shares Outstanding (M)", value=16000.0)

# -----------------------------
# Projection Logic
# -----------------------------
years = years_high + 5

revenues = []
fcfs = []
ebits = []
nopats = []

rev = revenue

for t in range(years):
    if t < years_high:
        growth = growth_high
    else:
        growth = growth_stable

    rev = rev * (1 + growth)
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
# Results
# -----------------------------
st.header("📈 Valuation Output")

col1, col2, col3 = st.columns(3)
col1.metric("Enterprise Value ($M)", f"{enterprise_value:,.0f}")
col2.metric("Equity Value ($M)", f"{equity_value:,.0f}")
col3.metric("Intrinsic Value / Share", f"${value_per_share:.2f}")

st.subheader("📊 Market Comparison")
st.write(f"**Current Price:** ${price:.2f}")
st.write(f"**Upside/Downside:** {(value_per_share/price - 1):.2%}")

# -----------------------------
# Projection Table
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

st.subheader("📋 Detailed Projection")
st.dataframe(df)

# -----------------------------
# Chart
# -----------------------------
st.subheader("📉 Free Cash Flow Projection")
st.line_chart(df.set_index("Year")["FCF"])

# -----------------------------
# Sensitivity Analysis
# -----------------------------
st.subheader("🔥 Sensitivity Analysis (WACC vs Growth)")

wacc_range = np.linspace(wacc - 0.02, wacc + 0.02, 5)
growth_range = np.linspace(growth_stable - 0.01, growth_stable + 0.01, 5)

sensitivity = pd.DataFrame(index=[f"{g:.2%}" for g in growth_range],
                           columns=[f"{w:.2%}" for w in wacc_range])

for g in growth_range:
    for w in wacc_range:
        tv = fcfs[-1] * (1 + g) / (w - g)
        pv_tv = tv / ((1 + w) ** years)
        ev = sum([fcfs[i] / ((1 + w) ** (i+1)) for i in range(years)]) + pv_tv
        eq = ev - debt + cash
        val = eq / shares
        sensitivity.loc[f"{g:.2%}", f"{w:.2%}"] = round(val, 2)

st.dataframe(sensitivity)

# -----------------------------
# Explanation Section
# -----------------------------
st.subheader("📘 How the Model Works")

st.markdown("""
1. **Revenue Projection:** grows based on high-growth and terminal phases  
2. **EBIT:** Revenue × Margin  
3. **NOPAT:** EBIT × (1 - Tax Rate)  
4. **FCF:** NOPAT - Reinvestment  
5. **Discounting:** Future cash flows discounted using WACC  
6. **Terminal Value:** Gordon Growth Model  
7. **Equity Value:** EV - Debt + Cash  
8. **Intrinsic Value per Share:** Equity / Shares  
""")
