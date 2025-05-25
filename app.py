import streamlit as st
import pandas as pd
import altair as alt
import requests  # ✅ Needed to send data to Google Sheets

# ------------------ 🔗 SET YOUR GOOGLE SCRIPT WEB APP URL BELOW ------------------
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyr7nTidmbFtuWa7b412vEEMuJQaof1f8umAZkaLmBDpQAIrz1uIdlgKe6uzfhotE-Q/exec"

CSV_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSWLTFCj9XO6pItPCVy4IMRonsVHntlyUEqjE1ywTVvVibV5ezoLs3h7bYkUqWmBjj1LkYbixwVsncA/pub?gid=0&single=true&output=csv"

# ------------------ STYLE & CONFIG ------------------
st.set_page_config(page_title="FinTrack Pro", layout="wide")
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
def format_rp(x):
    return f"Rp {x:,.0f}".replace(",", ".")

def simulate_growth(monthly_topup, daily_rate, months):
    days = months * 20
    balance = 0
    history = []
    for day in range(1, days + 1):
        if day % 20 == 1:
            balance += monthly_topup
        balance *= 1 + (daily_rate / 100)
        history.append(balance)
    return history

@st.cache_data(ttl=60)
def load_google_sheet_csv():
    return pd.read_csv(CSV_SHEET_URL)

# ------------------ SIDEBAR ------------------
st.sidebar.markdown("## 📊 FinTrack Pro")
page = st.sidebar.radio("Navigate", [
    "Dashboard", "Earnings Simulator", "Transactions", "Goal Tracker", "Settings"
])

# ------------------ DASHBOARD ------------------
if page == "Dashboard":
    st.markdown("## 🧾 Dashboard Overview")
    df = load_google_sheet_csv()
    top_up = df[df["Type"] == "topup"]["Amount"].sum()
    profit = df[df["Type"] == "profit"]["Amount"].sum()
    balance = top_up + profit
    roi = (profit / top_up * 100) if top_up else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class='big-card'>
            <div class='section-title'>💰 Total Top-Up</div>
            <div class='metric-value'>{format_rp(top_up)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class='big-card'>
            <div class='section-title'>📈 Total Profit</div>
            <div class='metric-value'>{format_rp(profit)}</div>
            <div class='positive'>+{roi:.1f}% ROI</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class='big-card'>
            <div class='section-title'>💼 Current Balance</div>
            <div class='metric-value'>{format_rp(balance)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class='big-card'>
            <div class='section-title'>🎯 Target Goal</div>
            <div class='metric-value'>{format_rp(100_000_000)}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 📊 Simulated Daily Growth")
    chart_data = simulate_growth(1_000_000, 1.0, 1)
    sim_df = pd.DataFrame({
        "Day": list(range(1, len(chart_data)+1)),
        "Balance": chart_data
    })
    chart = alt.Chart(sim_df).mark_line(color="#22C55E").encode(x="Day", y="Balance")
    st.altair_chart(chart, use_container_width=True)

# ------------------ SIMULATOR ------------------
elif page == "Earnings Simulator":
    st.markdown("## 🧠 Earnings Simulator")
    col1, col2, col3 = st.columns(3)
    topup = col1.number_input("Monthly Top-Up (Rp)", value=1000000, step=100000)
    rate = col2.slider("Daily Profit (%)", 0.1, 3.0, 1.0, 0.1)
    duration = col3.slider("Duration (months)", 1, 60, 12)

    sim_result = simulate_growth(topup, rate, duration)
    final_balance = sim_result[-1]

    st.metric("📈 Projected Final Balance", format_rp(final_balance))
    sim_df = pd.DataFrame({
        "Day": list(range(1, len(sim_result)+1)),
        "Balance": sim_result
    })
    sim_chart = alt.Chart(sim_df).mark_area(opacity=0.7, color="#22C55E").encode(x="Day", y="Balance")
    st.altair_chart(sim_chart, use_container_width=True)

# ------------------ TRANSACTIONS ------------------
elif page == "Transactions":
    st.markdown("## 📑 Transaction History")
    with st.form("transaction_form"):
        col1, col2, col3 = st.columns(3)
        t_type = col1.selectbox("Type", ["topup", "profit", "withdraw"])
        amount = col2.number_input("Amount (Rp)", step=10000)
        note = col3.text_input("Note / Description")
        submit = st.form_submit_button("➕ Add Transaction")

        if submit:
            payload = {
                "type": t_type,
                "amount": amount,
                "note": note
            }
            try:
                res = requests.post(GOOGLE_SCRIPT_URL, json=payload)
                if res.status_code == 200:
                    st.success("✅ Transaction saved to Google Sheets!")
                    load_google_sheet_csv.clear()  # 🔁 Refresh live data!
                else:
                    st.error("❌ Failed to save.")
            except Exception as e:
                st.error(f"⚠️ Error: {e}")

    df = load_google_sheet_csv()
    if not df.empty:
        df["Amount"] = df["Amount"].apply(format_rp)
        st.markdown("### 📋 Recent Transactions")
        st.dataframe(df[["Date", "Type", "Amount", "Note"]])
    else:
        st.info("📄 No transactions yet.")

# ------------------ GOAL TRACKER ------------------
elif page == "Goal Tracker":
    st.markdown("## 🎯 Goal Tracker")
    goal = st.number_input("Your Target (Rp)", value=100_000_000, step=1000000)
    df = load_google_sheet_csv()
    top_up = df[df["Type"] == "topup"]["Amount"].sum()
    profit = df[df["Type"] == "profit"]["Amount"].sum()
    balance = top_up + profit
    progress = (balance / goal * 100) if goal else 0
    st.metric("Progress", f"{progress:.1f}%", f"Balance: {format_rp(balance)}")
    st.progress(progress / 100)

# ------------------ SETTINGS ------------------
elif page == "Settings":
    st.markdown("## ⚙️ Settings")
    st.warning("⚠️ Data is saved in Google Sheets. To reset, clear the sheet manually.")
