import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf

# ----------------------------------------
# PAGE SETUP
# ----------------------------------------
st.set_page_config(page_title="DCF Valuation Tool", layout="wide")
st.title("📊 Equity Valuation using DCF")

st.markdown("""
This application estimates a company's intrinsic value using a **Discounted Cash Flow (DCF)** approach.
You can compare the model value to the current stock price to evaluate potential mispricing.
""")

# ----------------------------------------
# STEP 1: TICKER + DATA
# ----------------------------------------
st.header("Step 1 — Company Selection")

ticker = st.text_input("Enter Stock Ticker", value="AAPL").upper()

@st.cache_data
def load_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        return {
            "name": info.get("longName", ticker),
            "price": info.get("currentPrice", None),
            "revenue": info.get("totalRevenue", None),
            "debt": info.get("totalDebt", 0),
            "cash": info.get("totalCash", 0),
            "shares": info.get("sharesOutstanding", None),
            "margin": info.get("operatingMargins", None),
            "tax": info.get("effectiveTaxRate", None),
            "beta": info.get("beta", None),
        }
    except:
        return None

data = load_stock_data(ticker)

if data is None:
    st.error("Error loading data.")
    st.stop()

st.success(f"Loaded data for {data['name']}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Stock Price", f"${data['price']:.2f}" if data["price"] else "N/A")
c2.metric("Revenue", f"${data['revenue']/1e9:.1f}B" if data["revenue"] else "N/A")
c3.metric("Debt", f"${data['debt']/1e9:.1f}B")
c4.metric("Cash", f"${data['cash']/1e9:.1f}B")

# ----------------------------------------
# STEP 2: CONTEXT
# ----------------------------------------
st.header("Step 2 — Context for Assumptions")

st.markdown("""
Before building the model, review the company's financial position.  
These values can help guide your assumptions in the next step.
""")

if data["beta"]:
    rf = 0.045
    premium = 0.055
    cost_equity = rf + data["beta"] * premium

    st.info(f"""
    **Beta:** {data['beta']:.2f}  
    Estimated Cost of Equity: {cost_equity*100:.1f}%  

    Higher beta implies higher risk and typically a higher discount rate.
    """)

# ----------------------------------------
# SIDEBAR INPUTS
# ----------------------------------------
st.sidebar.header("Model Inputs")

revenue = st.sidebar.number_input(
    "Starting Revenue",
    value=float(data["revenue"]) if data["revenue"] else 1e9
)

growth = st.sidebar.slider("Revenue Growth (%)", 0.0, 20.0, 8.0) / 100
margin = st.sidebar.slider(
    "EBIT Margin (%)",
    0.0, 50.0,
    float(data["margin"]*100) if data["margin"] else 20.0
) / 100

tax_rate = st.sidebar.slider(
    "Tax Rate (%)",
    0.0, 40.0,
    float(data["tax"]*100) if data["tax"] else 25.0
) / 100

reinvest = st.sidebar.slider("Reinvestment Rate (%)", 0.0, 100.0, 30.0) / 100
wacc = st.sidebar.slider("WACC (%)", 5.0, 15.0, 10.0) / 100
terminal_growth = st.sidebar.slider("Terminal Growth (%)", 0.0, 5.0, 2.5) / 100
years = st.sidebar.slider("Projection Years", 3, 10, 5)

debt = st.sidebar.number_input("Debt", value=float(data["debt"]))
cash = st.sidebar.number_input("Cash", value=float(data["cash"]))
shares = st.sidebar.number_input(
    "Shares Outstanding",
    value=float(data["shares"]) if data["shares"] else 1e6
)

# ----------------------------------------
# STEP 3: DCF CALCULATION
# ----------------------------------------
st.header("Step 3 — Cash Flow Projection")

revenues, fcfs = [], []
rev = revenue

for i in range(years):
    rev *= (1 + growth)
    ebit = rev * margin
    nopat = ebit * (1 - tax_rate)
    fcf = nopat * (1 - reinvest)

    revenues.append(rev)
    fcfs.append(fcf)

discount = [(1 / (1 + wacc) ** (i + 1)) for i in range(years)]
pv_fcfs = [f * d for f, d in zip(fcfs, discount)]

terminal_value = fcfs[-1] * (1 + terminal_growth) / (wacc - terminal_growth)
pv_terminal = terminal_value / ((1 + wacc) ** years)

enterprise_value = sum(pv_fcfs) + pv_terminal
equity_value = enterprise_value - debt + cash
value_per_share = equity_value / shares

# ----------------------------------------
# TABLE
# ----------------------------------------
df = pd.DataFrame({
    "Year": np.arange(1, years+1),
    "Revenue": revenues,
    "FCF": fcfs,
    "PV of FCF": pv_fcfs
})

st.subheader("Projection Table")
st.dataframe(df)

# ----------------------------------------
# CHART
# ----------------------------------------
st.subheader("Cash Flow Trend")
st.line_chart(df.set_index("Year")["FCF"])

# ----------------------------------------
# STEP 4: RESULTS
# ----------------------------------------
st.header("Step 4 — Valuation")

r1, r2, r3 = st.columns(3)
r1.metric("Enterprise Value", f"${enterprise_value:,.0f}")
r2.metric("Equity Value", f"${equity_value:,.0f}")
r3.metric("Value per Share", f"${value_per_share:.2f}")

if data["price"]:
    diff = (value_per_share - data["price"]) / data["price"]
    st.write(f"Market Price: ${data['price']:.2f}")
    st.write(f"Upside/Downside: {diff:.2%}")

# ----------------------------------------
# STEP 5: SENSITIVITY
# ----------------------------------------
st.header("Step 5 — Sensitivity Analysis")

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

        pv = [flows[i] / ((1 + w) ** (i+1)) for i in range(years)]
        tv = flows[-1] * (1 + terminal_growth) / (w - terminal_growth)
        ev = sum(pv) + tv / ((1 + w) ** years)

        eq = ev - debt + cash
        sens.loc[f"{g:.2%}", f"{w:.2%}"] = round(eq / shares, 2)

st.dataframe(sens)

# ----------------------------------------
# EXPLANATION
# ----------------------------------------
st.markdown("""
### How the Model Works

- Revenue grows each year based on your assumption  
- Profitability is captured through EBIT margin  
- Taxes are applied to get NOPAT  
- Reinvestment reduces free cash flow  
- Cash flows are discounted using WACC  
- Terminal value captures long-term value  

This structure allows easy replication in Excel.
""")
