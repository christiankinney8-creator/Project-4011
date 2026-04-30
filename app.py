import streamlit as st
import numpy as np
import pandas as pd

# SAFE IMPORT
try:
    import yfinance as yf
except ImportError:
    yf = None

st.set_page_config(page_title="DCF Valuation Tool", layout="wide")

st.title("📊 Equity Valuation App (DCF Model)")
st.write("Estimate intrinsic value and compare to market price using a Discounted Cash Flow model.")

# =========================================================
# HELPERS
# =========================================================
def pct(x): return x / 100

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.header("🔧 Inputs")

# -------------------------
# TICKER
# -------------------------
ticker = st.sidebar.text_input("Stock Ticker", value="AAPL")
use_live_data = st.sidebar.checkbox("Use Live Data", value=False)

if use_live_data and yf is None:
    st.sidebar.error("yfinance not installed")
    use_live_data = False

# -------------------------
# LOAD DATA
# -------------------------
if use_live_data and ticker and yf:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        revenue0 = info.get("totalRevenue", 1e9) / 1e6
        shares = info.get("sharesOutstanding", 1e8) / 1e6
        cash = info.get("totalCash", 0) / 1e6
        net_debt = (info.get("totalDebt", 0) - info.get("totalCash", 0)) / 1e6
        price = stock.history(period="1d")["Close"].iloc[-1]

        st.sidebar.success(f"Loaded {ticker}")

    except:
        st.sidebar.error("Data failed → manual mode")
        use_live_data = False

# -------------------------
# MANUAL INPUTS
# -------------------------
if not use_live_data:
    revenue0 = st.sidebar.number_input("Revenue ($M)", 1000.0)
    net_debt = st.sidebar.number_input("Net Debt ($M)", 500.0)
    cash = st.sidebar.number_input("Cash ($M)", 100.0)
    shares = st.sidebar.number_input("Shares (M)", 100.0)
else:
    st.sidebar.write(f"Revenue: {revenue0:,.0f}M")
    st.sidebar.write(f"Net Debt: {net_debt:,.0f}M")

# -------------------------
# ASSUMPTIONS
# -------------------------
st.sidebar.subheader("📈 Growth")
g1 = pct(st.sidebar.number_input("High Growth %", 8.0))
g2 = pct(st.sidebar.number_input("Terminal Growth %", 2.5))
years = st.sidebar.number_input("High Growth Years", 5)

st.sidebar.subheader("💰 Profitability")
margin = pct(st.sidebar.number_input("EBIT Margin %", 22.0))
tax = pct(st.sidebar.number_input("Tax Rate %", 21.0))

st.sidebar.subheader("🔁 Reinvestment")
reinv = pct(st.sidebar.number_input("Reinvestment %", 50.0))

st.sidebar.subheader("📉 Discounting")
wacc = pct(st.sidebar.number_input("WACC %", 9.5))

# VALIDATION
if wacc <= g2:
    st.error("WACC must be > terminal growth")
    st.stop()

# =========================================================
# MODEL
# =========================================================
total_years = int(years + 5)

revenues, nopats, fcfs = [], [], []

rev = revenue0

for t in range(total_years):
    g = g1 if t < years else g2
    rev *= (1 + g)

    ebit = rev * margin
    nopat = ebit * (1 - tax)
    reinvestment = nopat * reinv
    fcf = nopat - reinvestment

    revenues.append(rev)
    nopats.append(nopat)
    fcfs.append(fcf)

# DISCOUNT
dfs = [(1 / (1 + wacc) ** (i + 1)) for i in range(total_years)]
pv_fcfs = [fcfs[i] * dfs[i] for i in range(total_years)]

# TERMINAL
tv = fcfs[-1] * (1 + g2) / (wacc - g2)
pv_tv = tv / ((1 + wacc) ** total_years)

# VALUE
ev = sum(pv_fcfs) + pv_tv
eq = ev - net_debt + cash
value_per_share = eq / shares

# =========================================================
# OUTPUT
# =========================================================
st.header("📈 Results")

c1, c2, c3 = st.columns(3)
c1.metric("Enterprise Value", f"${ev:,.0f}M")
c2.metric("Equity Value", f"${eq:,.0f}M")
c3.metric("Value / Share", f"${value_per_share:.2f}")

if use_live_data:
    st.metric("Market Price", f"${price:.2f}")

    if value_per_share > price:
        st.success("Undervalued")
    else:
        st.warning("Overvalued")

# =========================================================
# STEP-BY-STEP (CRITICAL FOR GRADE)
# =========================================================
st.header("🧠 How the Model Works")

st.markdown("""
**Step 1:** Project Revenue using growth assumptions  
**Step 2:** Convert to EBIT using margin  
**Step 3:** Apply taxes → NOPAT  
**Step 4:** Subtract reinvestment → Free Cash Flow  
**Step 5:** Discount FCF using WACC  
**Step 6:** Add terminal value  
""")

# =========================================================
# TABLE (FOR EXCEL REPLICATION)
# =========================================================
df = pd.DataFrame({
    "Year": np.arange(1, total_years + 1),
    "Revenue": revenues,
    "NOPAT": nopats,
    "FCF": fcfs,
    "Discount Factor": dfs,
    "PV FCF": pv_fcfs
})

st.header("📋 Detailed Breakdown")
st.dataframe(df)

# =========================================================
# CHART
# =========================================================
st.header("📉 Trends")
st.line_chart(df.set_index("Year")[["Revenue", "FCF"]])

# =========================================================
# TERMINAL INSIGHT
# =========================================================
tv_weight = pv_tv / ev
st.write(f"Terminal Value = **{tv_weight:.1%}** of total value")

if tv_weight > 0.7:
    st.warning("Heavy reliance on terminal value")
