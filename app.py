import streamlit as st
import pandas as pd
import plotly.express as px
from SmartApi import SmartConnect
import pyotp
import os
import datetime
import requests

st.set_page_config(page_title="Option Chain Dashboard", layout="wide")

# ------------------- CONFIG -------------------
INDICES = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
REFRESH_INTERVAL = 60  # seconds
INSTRUMENTS_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

# ------------------- FUNCTIONS -------------------
@st.cache_data(ttl=3600)
def load_instruments():
    df = pd.read_json(INSTRUMENTS_URL)
    return df

def fetch_option_chain(symbol, expiry_choice):
    try:
        API_KEY = os.getenv("ANGEL_API_KEY")
        CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
        PASSWORD = os.getenv("ANGEL_PASSWORD")
        TOTP_SECRET = os.getenv("ANGEL_TOTP")

        if not all([API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET]):
            st.error("❌ API credentials not set. Please add them in Streamlit Secrets.")
            return pd.DataFrame(), pd.DataFrame()

        obj = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = obj.generateSession(CLIENT_ID, PASSWORD, totp)

        instruments = load_instruments()
        df = instruments[(instruments['name'] == symbol) & 
                         (instruments['exch_seg'] == 'NFO') & 
                         (instruments['instrumenttype'] == 'OPTIDX') & 
                         (instruments['expiry'] == expiry_choice)]

        # Get ATM from index spot price
        spot = obj.ltpData("NSE", symbol, df[df['strike'] == 0].iloc[0]['token'])
        spot_price = spot['data']['ltp']
        strikes = sorted(df['strike'].unique())
        atm = min(strikes, key=lambda x: abs(x - spot_price))

        # Limit to ±10 strikes
        strike_range = [s for s in strikes if atm-1000 <= s <= atm+1000]

        ce_data, pe_data = [], []
        for _, row in df[df['strike'].isin(strike_range)].iterrows():
            params = {"exchange": row['exch_seg'], "tradingsymbol": row['symbol'], "symboltoken": row['token']}
            try:
                q = obj.ltpData(**params)
                ltp = q['data']['ltp']
                oi = q['data'].get('openInterest', 0)
                coi = q['data'].get('changeinOpenInterest', 0)
                if row['optiontype'] == 'CE':
                    ce_data.append([row['strike'], oi, coi, ltp])
                else:
                    pe_data.append([row['strike'], oi, coi, ltp])
            except Exception:
                pass

        df_ce = pd.DataFrame(ce_data, columns=["Strike", "OI", "Chg_OI", "LTP"])
        df_pe = pd.DataFrame(pe_data, columns=["Strike", "OI", "Chg_OI", "LTP"])
        return df_ce, df_pe
    
    except Exception as e:
        st.error(f"Angel fetch failed: {e}")
        return pd.DataFrame(), pd.DataFrame()

def market_status():
    now = datetime.datetime.now().time()
    open_time = datetime.time(9, 15)
    close_time = datetime.time(15, 30)
    return open_time <= now <= close_time

# ------------------- UI -------------------
st.title("📊 Option Chain Dashboard (Angel One SmartAPI)")
index_choice = st.selectbox("Select Index", INDICES)

instruments = load_instruments()
expiry_list = sorted(instruments[instruments['name'] == index_choice]['expiry'].unique())
expiry_choice = st.selectbox("Select Expiry", expiry_list)

ce_df, pe_df = fetch_option_chain(index_choice, expiry_choice)

if not ce_df.empty and not pe_df.empty:
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

# Auto-refresh
st_autorefresh = st.empty()
st_autorefresh.markdown(
    f"<script>setTimeout(function(){{window.location.reload();}}, {REFRESH_INTERVAL*1000});</script>",
    unsafe_allow_html=True
)
