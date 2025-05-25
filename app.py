import streamlit as st
import pandas as pd
import altair as alt
import requests
from datetime import datetime, timedelta

# ------------------ 🔗 SET YOUR GOOGLE SCRIPT WEB APP URL BELOW ------------------
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyr7nTidmbFtuWa7b412vEEMuJQaof1f8umAZkaLmBDpQAIrz1uIdlgKe6uzfhotE-Q/exec"

CSV_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSWLTFCj9XO6pItPCVy4IMRonsVHntlyUEqjE1ywTVvVibV5ezoLs3h7bYkUqWmBjj1LkYbixwVsncA/pub?gid=0&single=true&output=csv"

TARGET_GOAL = 100_000_000

st.set_page_config(page_title="FinTrack Pro", layout="wide")

# ------------------ STYLES ------------------
st.markdown("""
    <style>
        body { background-color: #0f172a; color: #f9fafb; }
        .big-card {
            background-color: #1e293b;
            padding: 20px; border-radius: 12px;
            box-shadow: 0 0 10px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        .metric-value { font-size: 28px; font-weight: bold; }
        .positive { color: #22C55E; }
        .negative { color: #ef4444; }
        .section-title { font-size: 20px; font-weight: bold; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# ------------------ FUNCTIONS ------------------
def format_rp(x): return f"Rp {x:,.0f}".replace(",", ".")

@st.cache_data(ttl=60)
def load_google_sheet_csv():
    return pd.read_csv(CSV_SHEET_URL)

def simulate_growth(monthly_topup, daily_rate, months):
    days = months * 20
    balance, history = 0, []
    for day in range(1, days + 1):
        if day % 20 == 1:
            balance += monthly_topup
        balance *= 1 + (daily_rate / 100)
        history.append(balance)
    return history

# ------------------ SIDEBAR ------------------
st.sidebar.markdown("## 📊 FinTrack Pro")
page = st.sidebar.radio("Navigate", ["Dashboard", "Earnings Simulator", "Transactions", "Goal Tracker", "Settings"])

# ------------------ DASHBOARD ------------------
if page == "Dashboard":
    st.markdown("## 🧾 Dashboard Overview")
    df = load_google_sheet_csv()
    df["Date"] = pd.to_datetime(df["Date"])
    top_up = df[df["Type"] == "topup"]["Amount"].sum()
    profit = df[df["Type"] == "profit"]["Amount"].sum()
    withdraw = df[df["Type"] == "withdraw"]["Amount"].sum()
    balance = top_up + profit + withdraw
    roi = (profit / top_up * 100) if top_up else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f"<div class='big-card'><div class='section-title'>💰 Total Top-Up</div><div class='metric-value'>{format_rp(top_up)}</div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='big-card'><div class='section-title'>📈 Total Profit</div><div class='metric-value'>{format_rp(profit)}</div><div class='positive'>+{roi:.1f}% ROI</div></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='big-card'><div class='section-title'>💼 Current Balance</div><div class='metric-value'>{format_rp(balance)}</div></div>", unsafe_allow_html=True)
    col4.markdown(f"<div class='big-card'><div class='section-title'>🎯 Target Goal</div><div class='metric-value'>{format_rp(TARGET_GOAL)}</div></div>", unsafe_allow_html=True)

    # ROI Chart
    st.markdown("### 📊 ROI Over Time")
    roi_df = df[df["Type"] == "profit"].copy()
    roi_df["Cumulative Profit"] = roi_df["Amount"].cumsum()
    roi_df["ROI (%)"] = (roi_df["Cumulative Profit"] / top_up * 100).fillna(0)
    if not roi_df.empty:
        chart = alt.Chart(roi_df).mark_line().encode(x="Date", y="ROI (%)")
        st.altair_chart(chart, use_container_width=True)

    # Profit alert
    if profit >= 5_000_000:
        st.success("🎉 You've reached over Rp 5.000.000 in profit!")

    # Loss warning
    if abs(withdraw) > top_up * 0.2:
        st.error("⚠️ Withdrawal exceeds 20% of your top-up — risk warning.")

    # Goal ETA
    daily_profits = df[df["Type"] == "profit"]
    daily_avg = profit / len(daily_profits) if not daily_profits.empty else 0
    if balance < TARGET_GOAL and daily_avg > 0:
        days_needed = (TARGET_GOAL - balance) / daily_avg
        eta = datetime.now() + timedelta(days=int(days_needed))
        st.info(f"⏱ Estimated time to reach goal: {int(days_needed)} days → {eta.strftime('%Y-%m-%d')}")

# ------------------ SIMULATOR ------------------
elif page == "Earnings Simulator":
    st.markdown("## 🧠 Earnings Simulator")
    strategy = st.radio("Choose Strategy", ["Conservative (0.5%)", "Balanced (1.0%)", "Aggressive (1.5%)"])
    
    rate_map = {
        "Conservative (0.5%)": 0.5,
        "Balanced (1.0%)": 1.0,
        "Aggressive (1.5%)": 1.5
    }
    daily_rate = rate_map[strategy]

    col1, col2 = st.columns(2)
    topup = col1.number_input("Monthly Top-Up (Rp)", value=1_000_000, step=100_000)
    duration = col2.slider("Duration (months)", 1, 60, 12)

    sim_result = simulate_growth(topup, daily_rate, duration)
    st.metric("📈 Final Balance", format_rp(sim_result[-1]))
    df_sim = pd.DataFrame({"Day": list(range(1, len(sim_result)+1)), "Balance": sim_result})
    st.altair_chart(alt.Chart(df_sim).mark_area(opacity=0.5).encode(x="Day", y="Balance"), use_container_width=True)

# ------------------ TRANSACTIONS ------------------
elif page == "Transactions":
    st.markdown("## 📑 Transaction History")
    with st.form("transaction_form"):
        col1, col2, col3 = st.columns(3)
        t_type = col1.selectbox("Type", ["topup", "profit", "withdraw"])
        amount = col2.number_input("Amount (Rp)", step=10_000)
        note = col3.text_input("Note")
        submitted = st.form_submit_button("➕ Add Transaction")
        if submitted:
            payload = {"type": t_type, "amount": amount, "note": note}
            try:
                res = requests.post(GOOGLE_SCRIPT_URL, json=payload)
                if res.status_code == 200:
                    st.success("✅ Transaction saved.")
                    load_google_sheet_csv.clear()
                else:
                    st.error("❌ Failed to save.")
            except Exception as e:
                st.error(f"⚠️ {e}")

    df = load_google_sheet_csv()
    df["Amount"] = df["Amount"].apply(format_rp)
    st.markdown("### 📋 Recent Transactions")
    st.dataframe(df[["Date", "Type", "Amount", "Note"]])
    st.download_button("📤 Export to CSV", df.to_csv(index=False), "transactions.csv")

# ------------------ GOAL TRACKER ------------------
elif page == "Goal Tracker":
    st.markdown("## 🎯 Goal Tracker")
    goal = st.number_input("Your Target (Rp)", value=TARGET_GOAL, step=1_000_000)
    df = load_google_sheet_csv()
    top_up = df[df["Type"] == "topup"]["Amount"].sum()
    profit = df[df["Type"] == "profit"]["Amount"].sum()
    withdraw = df[df["Type"] == "withdraw"]["Amount"].sum()
    balance = top_up + profit + withdraw
    progress = (balance / goal * 100) if goal else 0
    st.metric("Progress", f"{progress:.1f}%", f"Balance: {format_rp(balance)}")
    st.progress(progress / 100)

# ------------------ SETTINGS ------------------
elif page == "Settings":
    st.markdown("## ⚙️ Settings")
    st.warning("⚠️ Data is saved in Google Sheets. To reset, clear the sheet manually.")

    if st.button("🧠 Simulate Auto-Daily Profit (+1.5%)"):
        df = load_google_sheet_csv()
        current_balance = df[df["Type"] != "withdraw"]["Amount"].sum()
        gain = int(current_balance * 0.015)
        payload = {"type": "profit", "amount": gain, "note": "Simulated daily gain"}
        try:
            res = requests.post(GOOGLE_SCRIPT_URL, json=payload)
            if res.status_code == 200:
                st.success(f"📅 +{format_rp(gain)} profit added!")
                load_google_sheet_csv.clear()
            else:
                st.error("Failed to add profit.")
        except Exception as e:
            st.error(f"Error: {e}")
