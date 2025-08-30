import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from SmartApi import SmartConnect
import pyotp
import os
import datetime

st.set_page_config(page_title="Option Chain Dashboard", layout="wide")

# ------------------- CONFIG -------------------
INDICES = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
REFRESH_INTERVAL = 60  # seconds
INSTRUMENTS_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

# Angel tokens for index spot prices
INDEX_TOKENS = {"NIFTY": "26000", "BANKNIFTY": "26009", "FINNIFTY": "26037"}
# Strike step sizes for indices
INDEX_STEPS = {"NIFTY": 50, "BANKNIFTY": 100, "FINNIFTY": 25}

# ------------------- FUNCTIONS -------------------
@st.cache_data(ttl=3600)
def load_instruments():
    df = pd.read_json(INSTRUMENTS_URL)
    return df

def fetch_option_chain(symbol, expiry_choice, range_n):
    try:
        API_KEY = os.getenv("ANGEL_API_KEY")
        CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
        PASSWORD = os.getenv("ANGEL_PASSWORD")
        TOTP_SECRET = os.getenv("ANGEL_TOTP")

        if not all([API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET]):
            st.error("❌ API credentials not set. Please add them in Streamlit Secrets.")
            return pd.DataFrame(), pd.DataFrame(), None, None, None

        obj = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = obj.generateSession(CLIENT_ID, PASSWORD, totp)

        instruments = load_instruments()
        df = instruments[(instruments['name'] == symbol) & 
                         (instruments['exch_seg'] == 'NFO') & 
                         (instruments['expiry'] == expiry_choice)]

        if df.empty:
            st.error("⚠️ No contracts found for this expiry in instruments list.")
            return pd.DataFrame(), pd.DataFrame(), obj, None, None

        # Get spot price using Angel static tokens
        spot = obj.ltpData("NSE", symbol, INDEX_TOKENS[symbol])
        spot_price = spot['data']['ltp']

        # Find ATM safely
        strikes = sorted(df['strike'].unique())
        if not strikes:
            st.error("⚠️ No strike prices found.")
            return pd.DataFrame(), pd.DataFrame(), obj, spot_price, None

        atm = min(strikes, key=lambda x: abs(x - spot_price))

        # Use slider-based range ±N strikes
        atm_index = strikes.index(atm)
        low = max(0, atm_index - range_n)
        high = min(len(strikes), atm_index + range_n)
        strike_range = strikes[low:high]

        ce_data, pe_data = [], []
        for _, row in df[df['strike'].isin(strike_range)].iterrows():
            params = {"exchange": row['exch_seg'], "tradingsymbol": row['symbol'], "symboltoken": row['token']}
            try:
                q = obj.ltpData(**params)
                if not q or 'data' not in q:
                    continue

                ltp = q['data'].get('ltp', 0)
                oi = q['data'].get('openInterest', 0)
                coi = q['data'].get('changeinOpenInterest', 0)

                # Detect CE/PE
                opt_type = row.get('optiontype', None)
                if not opt_type:
                    if str(row['symbol']).endswith("CE"):
                        opt_type = "CE"
                    elif str(row['symbol']).endswith("PE"):
                        opt_type = "PE"

                if opt_type == "CE":
                    ce_data.append([row['strike'], oi, coi, ltp])
                elif opt_type == "PE":
                    pe_data.append([row['strike'], oi, coi, ltp])

            except Exception:
                continue

        df_ce = pd.DataFrame(ce_data, columns=["Strike", "OI", "Chg_OI", "LTP"])
        df_pe = pd.DataFrame(pe_data, columns=["Strike", "OI", "Chg_OI", "LTP"])
        return df_ce, df_pe, obj, spot_price, atm
    
    except Exception as e:
        st.error(f"Angel fetch failed: {e}")
        return pd.DataFrame(), pd.DataFrame(), None, None, None

def market_status(obj):
    try:
        status = obj.rmsLimit()
        exch_data = status.get('data', {})
        # Check any available exchange segment
        for seg in exch_data.values():
            if isinstance(seg, dict) and seg.get('exchangeStatus') == "OPEN":
                return True
        return False
    except Exception as e:
        st.warning(f"⚠️ Could not fetch market status: {e}")
        return False

def fetch_yesterday_ohlc(obj, symbol):
    try:
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        fromdate = f"{yesterday} 09:15"
        todate = f"{yesterday} 15:30"
        params = {
            "exchange": "NSE",
            "symboltoken": INDEX_TOKENS[symbol],
            "interval": "ONE_DAY",
            "fromdate": fromdate,
            "todate": todate
        }
        candles = obj.getCandleData(params)
        if "data" in candles and candles["data"]:
            _, o, h, l, c, v = candles["data"][-1]
            return float(h), float(l), float(c)
        return None, None, None
    except Exception as e:
        st.warning(f"⚠️ Could not fetch yesterday OHLC: {e}")
        return None, None, None

def calculate_cpr_support_resistance(high, low, close):
    pivot = (high + low + close) / 3
    bc = (high + low) / 2
    tc = pivot + (pivot - bc)

    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    r3 = high + 2 * (pivot - low)
    s3 = low - 2 * (high - pivot)

    return {
        "P": round(pivot, 2), "BC": round(bc, 2), "TC": round(tc, 2),
        "R1": round(r1, 2), "S1": round(s1, 2),
        "R2": round(r2, 2), "S2": round(s2, 2),
        "R3": round(r3, 2), "S3": round(s3, 2)
    }

# ------------------- UI -------------------
st.title("📊 Option Chain Dashboard (Angel One SmartAPI)")
index_choice = st.selectbox("Select Index", INDICES)

instruments = load_instruments()
expiry_list = sorted(instruments[instruments['name'] == index_choice]['expiry'].unique())
expiry_choice = st.selectbox("Select Expiry", expiry_list)

# Slider for strike range
range_n = st.slider("Strikes around ATM (±N)", 5, 25, 10)

ce_df, pe_df, obj, spot_price, atm = fetch_option_chain(index_choice, expiry_choice, range_n)

if not ce_df.empty and not pe_df.empty and atm:
    # --- Signal logic with OI + Chg_OI confirmation ---
    ce_oi = ce_df["OI"].sum()
    pe_oi = pe_df["OI"].sum()
    ce_chg = ce_df["Chg_OI"].sum()
    pe_chg = pe_df["Chg_OI"].sum()
    step = INDEX_STEPS.get(index_choice, 100)

    # --- CPR + Support/Resistance ---
    prev_high, prev_low, prev_close = fetch_yesterday_ohlc(obj, index_choice)
    if prev_high and prev_low and prev_close:
        cpr_levels = calculate_cpr_support_resistance(prev_high, prev_low, prev_close)
    else:
        cpr_levels = None

    bias = "Neutral"
    signal = "⚖️ No clear trade suggestion"
    alignment_msg = "⚠️ CPR alignment not checked"
    go_status = "🔴 NO-GO – Conditions not met"
    panel_color = "red"

    if ce_oi > pe_oi:
        bias = "Bearish (PUT side stronger)"
        if ce_chg > 0:
            if cpr_levels:
                if spot_price < cpr_levels['BC']:
                    signal = f"📉 BUY PUT at {atm} or {atm-step} (Aligned with CPR)"
                    alignment_msg = "✅ Spot below BC → CPR confirms bearish trade"
                    go_status = "🟢 GO – BUY PUT"
                    panel_color = "green"
                else:
                    signal = "⚠️ PUT signal but Spot not below BC → CPR misaligned, avoid trade"
                    alignment_msg = "❌ Misaligned with CPR"
                    go_status = "🔴 NO-GO – CPR misaligned"
            else:
                signal = f"📉 BUY PUT at {atm} or {atm-step} (Chg_OI confirmed)"
        else:
            signal = "⚠️ CE OI strong but unwinding (Chg_OI ≤ 0). Avoid fresh PUT trade."
    elif pe_oi > ce_oi:
        bias = "Bullish (CALL side stronger)"
        if pe_chg > 0:
            if cpr_levels:
                if spot_price > cpr_levels['TC']:
                    signal = f"📈 BUY CALL at {atm} or {atm+step} (Aligned with CPR)"
                    alignment_msg = "✅ Spot above TC → CPR confirms bullish trade"
                    go_status = "🟢 GO – BUY CALL"
                    panel_color = "green"
                else:
                    signal = "⚠️ CALL signal but Spot not above TC → CPR misaligned, avoid trade"
                    alignment_msg = "❌ Misaligned with CPR"
                    go_status = "🔴 NO-GO – CPR misaligned"
            else:
                signal = f"📈 BUY CALL at {atm} or {atm+step} (Chg_OI confirmed)"
        else:
            signal = "⚠️ PE OI strong but unwinding (Chg_OI ≤ 0). Avoid fresh CALL trade."

    # --- Mini Dashboard Panel ---
    st.markdown(
        f"""
        <div style='background-color:{panel_color};padding:15px;border-radius:10px;margin-bottom:20px;color:white;font-size:18px;'>
            <b>{go_status}</b><br>
            📌 Spot: {spot_price} | 🎯 ATM: {atm}<br>
            ⚖️ {bias} | 🚀 {signal}
        </div>
        """,
        unsafe_allow_html=True
    )

    # --- Detailed Summary box ---
    st.markdown("---")
    st.subheader("📊 Dashboard Summary")
    if cpr_levels:
        st.info(f"""
        {go_status}

        📌 Spot Price: {spot_price}  
        🎯 ATM Strike: {atm}  
        ⚖️ Bias: {bias}  
        🚀 Signal: {signal}  
        🔍 CPR Alignment: {alignment_msg}  

        🔹 CPR → TC={cpr_levels['TC']}  P={cpr_levels['P']}  BC={cpr_levels['BC']}  
        🔹 Supports → S1={cpr_levels['S1']}  S2={cpr_levels['S2']}  S3={cpr_levels['S3']}  
        🔹 Resistances → R1={cpr_levels['R1']}  R2={cpr_levels['R2']}  R3={cpr_levels['R3']}  
        """)
    else:
        st.info(f"""
        {go_status}

        📌 Spot Price: {spot_price}  
        🎯 ATM Strike: {atm}  
        ⚖️ Bias: {bias}  
        🚀 Signal: {signal}  
        🔍 CPR Alignment: {alignment_msg}  

        ⚠️ CPR & S/R not available (couldn't fetch yesterday OHLC)
        """)
    st.markdown("---")

    # --- Tables and Charts ---
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

    # Combined CE vs PE OI chart with CPR + S/R levels
    st.subheader("📊 Combined CE vs PE OI")
    fig_combined = go.Figure()
    fig_combined.add_trace(go.Bar(x=ce_df["Strike"], y=ce_df["OI"], name="CE OI", marker_color="blue"))
    fig_combined.add_trace(go.Bar(x=pe_df["Strike"], y=pe_df["OI"], name="PE OI", marker_color="red"))
    if cpr_levels:
        # CPR lines
        fig_combined.add_hline(y=cpr_levels['P'], line_dash="dash", line_color="green", annotation_text="P")
        fig_combined.add_hline(y=cpr_levels['TC'], line_dash="dash", line_color="purple", annotation_text="TC")
        fig_combined.add_hline(y=cpr_levels['BC'], line_dash="dash", line_color="orange", annotation_text="BC")
        # Support levels
        fig_combined.add_hline(y=cpr_levels['S1'], line_dash="dot", line_color="blue", annotation_text="S1")
        fig_combined.add_hline(y=cpr_levels['S2'], line_dash="dot", line_color="blue", annotation_text="S2")
        fig_combined.add_hline(y=cpr_levels['S3'], line_dash="dot", line_color="blue", annotation_text="S3")
        # Resistance levels
        fig_combined.add_hline(y=cpr_levels['R1'], line_dash="dot", line_color="red", annotation_text="R1")
        fig_combined.add_hline(y=cpr_levels['R2'], line_dash="dot", line_color="red", annotation_text="R2")
        fig_combined.add_hline(y=cpr_levels['R3'], line_dash="dot", line_color="red", annotation_text="R3")
    fig_combined.update_layout(barmode="group", xaxis_title="Strike", yaxis_title="Open Interest")
    st.plotly_chart(fig_combined, use_container_width=True)

    # Combined CE vs PE Change in OI chart
    st.subheader("📊 Combined CE vs PE Change in OI")
    fig_chg = go.Figure()
    fig_chg.add_trace(go.Bar(x=ce_df["Strike"], y=ce_df["Chg_OI"], name="CE Chg_OI", marker_color="lightblue"))
    fig_chg.add_trace(go.Bar(x=pe_df["Strike"], y=pe_df["Chg_OI"], name="PE Chg_OI", marker_color="orange"))
    fig_chg.update_layout(barmode="group", xaxis_title="Strike", yaxis_title="Change in OI")
    st.plotly_chart(fig_chg, use_container_width=True)

    # Market status + ATM
    is_open = market_status(obj) if obj else False
    st.markdown(f"**Market Status:** {'🟢 OPEN' if is_open else '🔴 CLOSED'}")
    st.caption(f"Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Auto-refresh
st_autorefresh = st.empty()
st_autorefresh.markdown(
    f"<script>setTimeout(function(){{window.location.reload();}}, {REFRESH_INTERVAL*1000});</script>",
    unsafe_allow_html=True
)
