import streamlit as st
import numpy as np
import pandas as pd

# ----------------------------------------
# PAGE SETUP
# ----------------------------------------
st.set_page_config(page_title="DCF Valuation Tool", layout="wide")
st.title("📊 DCF Valuation App")

st.markdown("""
Estimate a company's intrinsic value using a **Discounted Cash Flow (DCF)** model.
All inputs are user-defined to ensure transparency and full control.
""")

# ----------------------------------------
# STEP 1: BASIC INPUTS
# ----------------------------------------
st.header("Step 1 — Company Inputs")

col1, col2, col3 = st.columns(3)

price = col1.number_input("Current Stock Price ($)", value=100.0)
revenue = col2.number_input("Current Revenue ($)", value=1_000_000_000.0)
shares = col3.number_input("Shares Outstanding", value=1_000_000.0)

debt = col1.number_input("Total Debt ($)", value=100_000_000.0)
cash = col2.number_input("Cash ($)", value=50_000_000.0)

# ----------------------------------------
# SIDEBAR ASSUMPTIONS
# ----------------------------------------
st.sidebar.header("Model Assumptions")

growth = st.sidebar.slider("Revenue Growth (%)", 0.0, 20.0, 8.0) / 100
margin = st.sidebar.slider("EBIT Margin (%)", 0.0, 50.0, 20.0) / 100
tax_rate = st.sidebar.slider("Tax Rate (%)", 0.0, 40.0, 25.0) / 100
reinvest = st.sidebar.slider("Reinvestment Rate (%)", 0.0, 100.0, 30.0) / 100

wacc = st.sidebar.slider("WACC (%)", 5.0, 15.0, 10.0) / 100
terminal_growth = st.sidebar.slider("Terminal Growth (%)", 0.0, 5.0, 2.5) / 100
years = st.sidebar.slider("Projection Years", 3, 10, 5)

# Validation
if wacc <= terminal_growth:
    st.error("WACC must be greater than terminal growth.")
    st.stop()

# ----------------------------------------
# STEP 2: DCF CALCULATION
# ----------------------------------------
st.header("Step 2 — Cash Flow Projection")

revenues, ebit_list, nopat_list, fcf_list = [], [], [], []
rev = revenue

for i in range(years):
    rev *= (1 + growth)
    ebit = rev * margin
    nopat = ebit * (1 - tax_rate)
    fcf = nopat * (1 - reinvest)

    revenues.append(rev)
    ebit_list.append(ebit)
    nopat_list.append(nopat)
    fcf_list.append(fcf)

discount_factors = [(1 / (1 + wacc) ** (i + 1)) for i in range(years)]
pv_fcfs = [f * d for f, d in zip(fcf_list, discount_factors)]

terminal_value = fcf_list[-1] * (1 + terminal_growth) / (wacc - terminal_growth)
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
    "EBIT": ebit_list,
    "NOPAT": nopat_list,
    "FCF": fcf_list,
    "Discount Factor": discount_factors,
    "PV of FCF": pv_fcfs
})

st.subheader("Projection Table")
st.dataframe(df)

# ----------------------------------------
# CHART
# ----------------------------------------
st.subheader("Free Cash Flow Projection")
st.line_chart(df.set_index("Year")["FCF"])

# ----------------------------------------
# STEP 3: RESULTS
# ----------------------------------------
st.header("Step 3 — Valuation Results")

c1, c2, c3 = st.columns(3)
c1.metric("Enterprise Value", f"${enterprise_value:,.0f}")
c2.metric("Equity Value", f"${equity_value:,.0f}")
c3.metric("Intrinsic Value / Share", f"${value_per_share:.2f}")

st.write(f"Current Price: ${price:.2f}")
st.write(f"Upside / Downside: {(value_per_share / price - 1):.2%}")

# ----------------------------------------
# TERMINAL VALUE BREAKDOWN
# ----------------------------------------
st.subheader("Terminal Value Explanation")

st.markdown(f"""
- Final Year FCF: ${fcf_list[-1]:,.0f}  
- Terminal Growth Rate: {terminal_growth*100:.2f}%  
- WACC: {wacc*100:.2f}%  

Terminal Value = FCF × (1 + g) ÷ (WACC − g)

Present Value of Terminal Value: ${pv_terminal:,.0f}
""")

# ----------------------------------------
# STEP 4: SENSITIVITY
# ----------------------------------------
st.header("Step 4 — Sensitivity Analysis")

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
### Model Explanation

1. Revenue grows based on your assumption  
2. EBIT = Revenue × Margin  
3. NOPAT = EBIT × (1 − Tax Rate)  
4. FCF = NOPAT × (1 − Reinvestment Rate)  
5. Cash flows are discounted using WACC  
6. Terminal value captures long-term value  
7. Equity value = Enterprise value − Debt + Cash  

This model is fully transparent and can be replicated in Excel.
""")
