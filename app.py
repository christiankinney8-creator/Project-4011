import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf

# ----------------------------------------
# PAGE SETUP
# ----------------------------------------
st.set_page_config(page_title="DCF Valuation Tool", layout="wide")
st.title("📊 DCF Valuation App")

st.markdown("""
Estimate intrinsic value using a Discounted Cash Flow model and compare it to market price.
""")

# ----------------------------------------
# STEP 1: TICKER INPUT
# ----------------------------------------
st.header("Step 1 — Select Company")

ticker = st.text_input("Stock Ticker", value="AAPL").upper()

@st.cache_data
def get_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        return {
            "price": info.get("currentPrice", None),
            "revenue": info.get("totalRevenue", None),
            "debt": info.get("totalDebt", 0) or 0,
            "cash": info.get("totalCash", 0) or 0,
            "shares": info.get("sharesOutstanding", None),
        }
    except:
        return None

data = get_data(ticker)

if data is None:
    st.error("Unable to load ticker data.")
    st.stop()

# Safe defaults
price = data["price"] if data["price"] else 100.0
revenue_default = data["revenue"] if data["revenue"] else 1e9
shares_default = data["shares"] if data["shares"] else 1e6

col1, col2, col3 = st.columns(3)
col1.metric("Price", f"${price:.2f}")
col2.metric("Revenue", f"${revenue_default:,.0f}")
col3.metric("Shares", f"{shares_default:,.0f}")

# ----------------------------------------
# SIDEBAR INPUTS
# ----------------------------------------
st.sidebar.header("Model Assumptions")

revenue = st.sidebar.number_input("Revenue ($)", value=float(revenue_default))
growth = st.sidebar.slider("Growth Rate (%)", 0.0, 20.0, 8.0) / 100
margin = st.sidebar.slider("EBIT Margin (%)", 0.0, 50.0, 20.0) / 100
tax_rate = st.sidebar.slider("Tax Rate (%)", 0.0, 40.0, 25.0) / 100
reinvest = st.sidebar.slider("Reinvestment (%)", 0.0, 100.0, 30.0) / 100

wacc = st.sidebar.slider("WACC (%)", 5.0, 15.0, 10.0) / 100
terminal_growth = st.sidebar.slider("Terminal Growth (%)", 0.0, 5.0, 2.5) / 100
years = st.sidebar.slider("Projection Years", 3, 10, 5)

debt = st.sidebar.number_input("Debt ($)", value=float(data["debt"]))
cash = st.sidebar.number_input("Cash ($)", value=float(data["cash"]))
shares = st.sidebar.number_input("Shares", value=float(shares_default))

# Validation
if wacc <= terminal_growth:
    st.error("WACC must be greater than terminal growth.")
    st.stop()

# ----------------------------------------
# STEP 2: DCF CALCULATION
# ----------------------------------------
st.header("Step 2 — Projection")

revenues, fcfs = [], []
rev = revenue

for i in range(years):
    rev *= (1 + growth)
    ebit = rev * margin
    nopat = ebit * (1 - tax_rate)
    fcf = nopat * (1 - reinvest)

    revenues.append(rev)
    fcfs.append(fcf)

discount_factors = [(1 / (1 + wacc) ** (i + 1)) for i in range(years)]
pv_fcfs = [f * d for f, d in zip(fcfs, discount_factors)]

terminal_value = fcfs[-1] * (1 + terminal_growth) / (wacc - terminal_growth)
pv_terminal = terminal_value / ((1 + wacc) ** years)

enterprise_value = sum(pv_fcfs) + pv_terminal
equity_value = enterprise_value - debt + cash
value_per_share = equity_value / shares

# ----------------------------------------
# TABLE
# ----------------------------------------
df = pd.DataFrame({
    "Year": np.arange(1, years + 1),
    "Revenue": revenues,
    "FCF": fcfs,
    "PV of FCF": pv_fcfs
})

st.subheader("Projection Table")
st.dataframe(df)

# ----------------------------------------
# CHART
# ----------------------------------------
st.subheader("FCF Projection")
st.line_chart(df.set_index("Year")["FCF"])

# ----------------------------------------
# RESULTS
# ----------------------------------------
st.header("Step 3 — Results")

c1, c2, c3 = st.columns(3)
c1.metric("Enterprise Value", f"${enterprise_value:,.0f}")
c2.metric("Equity Value", f"${equity_value:,.0f}")
c3.metric("Value per Share", f"${value_per_share:.2f}")

st.write(f"Market Price: ${price:.2f}")
st.write(f"Upside / Downside: {(value_per_share / price - 1):.2%}")

# ----------------------------------------
# SENSITIVITY
# ----------------------------------------
st.header("Step 4 — Sensitivity")

w_range = np.linspace(wacc - 0.02, wacc + 0.02, 5)
g_range = np.linspace(growth - 0.02, growth + 0.02, 5)

sens = pd.DataFrame(index=[f"{g:.2%}" for g in g_range],
                    columns=[f"{w:.2%}" for w in w_range])

for g in g_range:
    for w in w_range:
        if w <= terminal_growth:
            sens.loc[f"{g:.2%}", f"{w:.2%}"] = np.nan
            continue

        r = revenue
        flows = []

        for _ in range(years):
            r *= (1 + g)
            nop = r * margin * (1 - tax_rate)
            flows.append(nop * (1 - reinvest))

        pv = [flows[i] / ((1 + w) ** (i + 1)) for i in range(years)]
        tv = flows[-1] * (1 + terminal_growth) / (w - terminal_growth)
        ev = sum(pv) + tv / ((1 + w) ** years)

        eq = ev - debt + cash
        sens.loc[f"{g:.2%}", f"{w:.2%}"] = round(eq / shares, 2)

st.dataframe(sens)

# ----------------------------------------
# EXPLANATION
# ----------------------------------------
st.markdown("""
### Model Overview

- Revenue grows based on your assumption  
- EBIT margin determines operating profit  
- Taxes convert EBIT to NOPAT  
- Reinvestment reduces free cash flow  
- Cash flows are discounted using WACC  
- Terminal value captures long-term value  

All steps are visible and can be replicated in Excel.
""")
