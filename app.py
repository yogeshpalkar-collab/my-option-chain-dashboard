
import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt

# Dependency check for SmartAPI
try:
    from SmartApi import SmartConnect
    SMARTAPI_AVAILABLE = True
except ImportError:
    SMARTAPI_AVAILABLE = False

# ---------------- PASSWORD PROTECTION ----------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Secured Dashboard")
    password = st.text_input("Enter Master Password", type="password")
    if st.button("Login"):
        if password == st.secrets["MASTER_PASSWORD"]:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password")
    st.stop()

# ---------------- STREAMLIT APP BEGINS ----------------
st.title("📊 Option Chain Dashboard (Secured)")

# If SmartAPI is not available → stop with clear message
if not SMARTAPI_AVAILABLE:
    st.error("❌ 'smartapi-python' package is not installed. Please add it to requirements.txt.")
    st.info("👉 Fix: Add 'smartapi-python' to requirements.txt and redeploy the app.")
    st.stop()

# Authenticate with SmartAPI
def get_connection():
    try:
        obj = SmartConnect(api_key=st.secrets["API_KEY"])
        data = obj.generateSession(st.secrets["CLIENT_ID"], st.secrets["PASSWORD"], st.secrets["TOTP"])
        return obj
    except Exception as e:
        st.error(f"❌ SmartAPI Login Failed: {e}")
        if st.button("🔄 Retry Login"):
            st.rerun()
        return None

if "smart_api" not in st.session_state:
    st.session_state["smart_api"] = get_connection()

smart_api = st.session_state["smart_api"]
if not smart_api:
    st.stop()

# ---------------- USER INPUTS ----------------
index_symbol = st.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "FINNIFTY"])

# ---------------- FETCH OPTION CHAIN ----------------
@st.cache_data(ttl=60)
def fetch_option_chain(symbol):
    try:
        # Placeholder for Angel One API call (replace with live implementation)
        strikes = np.arange(22000, 23000, 100)
        data = {
            "StrikePrice": strikes,
            "CE_OI": np.random.randint(1000, 5000, len(strikes)),
            "PE_OI": np.random.randint(1000, 5000, len(strikes)),
            "CE_LTP": np.random.randint(50, 250, len(strikes)),
            "PE_LTP": np.random.randint(50, 250, len(strikes)),
        }
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"❌ Failed to fetch option chain: {e}")
        return pd.DataFrame()

df = fetch_option_chain(index_symbol)
if df.empty:
    st.stop()

# ---------------- CALCULATE CPR ----------------
def calculate_cpr(high, low, close):
    pp = (high + low + close) / 3
    bc = (high + low) / 2
    tc = (pp - bc) + pp
    return pp, bc, tc

high, low, close = 22600, 22400, 22500  # Placeholder values
pp, bc, tc = calculate_cpr(high, low, close)

# ---------------- SUMMARY PANEL ----------------
spot_price = 22500  # Placeholder; should be fetched from live data
atm_strike = min(df["StrikePrice"], key=lambda x: abs(x - spot_price))

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Spot", spot_price)
with col2:
    st.metric("ATM", atm_strike)
with col3:
    bias = "BULLISH" if df["CE_OI"].sum() < df["PE_OI"].sum() else "BEARISH"
    st.metric("Bias", bias)

# ---------------- GO/NO-GO PANEL ----------------
st.subheader("🚦 GO/NO-GO Panel")
if bias == "BULLISH":
    st.success("✅ GO CALL")
else:
    st.error("❌ GO PUT")

# ---------------- CPR DISPLAY ----------------
st.subheader("📏 CPR Levels")
st.write(f"PP: {pp}, BC: {bc}, TC: {tc}")

# ---------------- CE vs PE OI CHART ----------------
st.subheader("CE vs PE Open Interest")
fig, ax = plt.subplots()
ax.plot(df["StrikePrice"], df["CE_OI"], label="CE OI")
ax.plot(df["StrikePrice"], df["PE_OI"], label="PE OI")
ax.axvline(atm_strike, color="gray", linestyle="--", label="ATM")
ax.set_xlabel("Strike Price")
ax.set_ylabel("Open Interest")
ax.legend()
st.pyplot(fig)

# ---------------- CE vs PE Change in OI ----------------
st.subheader("Change in OI (Synthetic Demo)")
df["CE_Change_OI"] = np.random.randint(-500, 500, len(df))
df["PE_Change_OI"] = np.random.randint(-500, 500, len(df))

fig2, ax2 = plt.subplots()
ax2.bar(df["StrikePrice"], df["CE_Change_OI"], alpha=0.7, label="CE ΔOI")
ax2.bar(df["StrikePrice"], df["PE_Change_OI"], alpha=0.7, label="PE ΔOI")
ax2.axvline(atm_strike, color="gray", linestyle="--", label="ATM")
ax2.set_xlabel("Strike Price")
ax2.set_ylabel("Change in OI")
ax2.legend()
st.pyplot(fig2)

# ---------------- OI TABLE ----------------
st.subheader("Option Chain Table")
st.dataframe(df)

# ---------------- CHECKLIST ----------------
st.subheader("📋 Live Checklist")
checklist_items = [
    "Spot above/below CPR",
    "Bias confirmed",
    "GO/NO-GO matched",
    "OI supports bias",
]
for item in checklist_items:
    st.checkbox(item)

# ---------------- SIGNAL HISTORY ----------------
st.subheader("📜 Signal History")
history = [
    {"time": "09:30", "signal": "GO CALL"},
    {"time": "11:15", "signal": "GO PUT"},
]
st.table(pd.DataFrame(history))
