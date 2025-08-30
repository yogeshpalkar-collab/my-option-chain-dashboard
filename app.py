import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import datetime

st.set_page_config(page_title="Option Chain Dashboard", layout="wide")

# ------------------- CONFIG -------------------
INDICES = {
    "NIFTY": "NIFTY",
    "BANKNIFTY": "BANKNIFTY",
    "FINNIFTY": "FINNIFTY"
}
REFRESH_INTERVAL = 60  # seconds
NSE_URL = "https://www.nseindia.com/api/option-chain-indices?symbol="

# ------------------- FUNCTIONS -------------------
@st.cache_data(ttl=60)
def fetch_option_chain(symbol):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "accept-language": "en,hi;q=0.9",
        "accept-encoding": "gzip, deflate, br",
    }
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers)
    response = session.get(NSE_URL + symbol, headers=headers)
    data = response.json()
    return data

def parse_option_chain(data):
    ce_data = []
    pe_data = []
    for item in data["records"]["data"]:
        strike = item.get("strikePrice")
        if "CE" in item:
            ce = item["CE"]
            ce_data.append([strike, ce["openInterest"], ce["changeinOpenInterest"], ce["lastPrice"]])
        if "PE" in item:
            pe = item["PE"]
            pe_data.append([strike, pe["openInterest"], pe["changeinOpenInterest"], pe["lastPrice"]])
    df_ce = pd.DataFrame(ce_data, columns=["Strike", "OI", "Chg_OI", "LTP"])
    df_pe = pd.DataFrame(pe_data, columns=["Strike", "OI", "Chg_OI", "LTP"])
    return df_ce, df_pe

def market_status():
    now = datetime.datetime.now().time()
    open_time = datetime.time(9, 15)
    close_time = datetime.time(15, 30)
    return open_time <= now <= close_time

# ------------------- UI -------------------
st.title("📊 Option Chain Dashboard")
index_choice = st.selectbox("Select Index", list(INDICES.keys()))

try:
    raw_data = fetch_option_chain(INDICES[index_choice])
    ce_df, pe_df = parse_option_chain(raw_data)

    # Layout
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Call Options (CE)")
        st.dataframe(ce_df.sort_values("Strike"))
        fig_ce = px.bar(ce_df, x="Strike", y="OI", title="CE OI by Strike")
        st.plotly_chart(fig_ce, use_container_width=True)

    with col2:
        st.subheader("📉 Put Options (PE)")
        st.dataframe(pe_df.sort_values("Strike"))
        fig_pe = px.bar(pe_df, x="Strike", y="OI", title="PE OI by Strike")
        st.plotly_chart(fig_pe, use_container_width=True)

    # Signal logic
    st.subheader("🔎 Signals")
    ce_oi = ce_df["OI"].sum()
    pe_oi = pe_df["OI"].sum()
    if ce_oi > pe_oi:
        st.success("Bias → PUT side stronger (Bearish sentiment)")
    elif pe_oi > ce_oi:
        st.success("Bias → CALL side stronger (Bullish sentiment)")
    else:
        st.info("Neutral bias")

    # Market status
    st.markdown(f"**Market Status:** {'🟢 OPEN' if market_status() else '🔴 CLOSED'}")
    st.caption(f"Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

except Exception as e:
    st.error(f"Error fetching data: {e}")

# Auto-refresh
st_autorefresh = st.empty()
st_autorefresh.markdown(
    f"<script>setTimeout(function(){{window.location.reload();}}, {REFRESH_INTERVAL*1000});</script>",
    unsafe_allow_html=True
)
