import streamlit as st
import yfinance as yf
import json
import os
import requests
from streamlit_autorefresh import st_autorefresh

# --- הגדרות טלגרם מעודכנות ---
TELEGRAM_TOKEN = "8247425172:AAHXtpgZN7JDKZAYBFhwLBnlWsPYD_xnlgY"
openai_api_key = st.secrets["OPENAI_API_KEY"]
TELEGRAM_CHAT_ID = "779151879" # שים לב: וודא שזה ה-ID שקיבלת מ-userinfobot
def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        requests.post(url, data=payload)
    except Exception as e:
        pass

# הגדרות עמוד
st.set_page_config(page_title="NEON Stock Watcher 2026", layout="wide")
st_autorefresh(interval=5000, key="datarefresh")

DB_FILE = "alerts_db.json"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                for t in data:
                    data[t] = [{"price": i, "direction": "UP", "hit": False} if isinstance(i, (int, float)) else {**i, "hit": i.get("hit", False)} for i in data[t]]
                return data
        except: return {}
    return {}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

if 'alerts' not in st.session_state:
    st.session_state.alerts = load_data()

def add_alert_callback():
    t_in = st.session_state.ticker_input.upper()
    p_in = st.session_state.price_input
    if t_in and p_in is not None and p_in > 0:
        try:
            curr = yf.Ticker(t_in).fast_info['last_price']
            direction = 'UP' if p_in > curr else 'DOWN'
            if t_in not in st.session_state.alerts:
                st.session_state.alerts[t_in] = []
            st.session_state.alerts[t_in].append({"price": p_in, "direction": direction, "hit": False})
            save_data(st.session_state.alerts)
            st.session_state.ticker_input = ""
            st.session_state.price_input = None
            st.toast(f"מטרה נוספה ל-{t_in}", icon="✅")
        except: st.toast("סימול לא תקין", icon="⚠️")

# עיצוב UI/UX מתוקן
st.markdown("""
    <style>
    .stApp { background: #0b0d11; color: #e0e0e0; }
    .stock-card { 
        background: rgba(255, 255, 255, 0.05); 
        border-radius: 15px; 
        padding: 20px; 
        border-right: 5px solid #00ffff; 
        margin-bottom: 15px;
    }
    .price-main { color: #00ffff; font-size: 1.8rem; font-weight: 800; }
    .price-badge {
        background: rgba(0, 255, 255, 0.1);
        color: #00ffff;
        padding: 4px 12px;
        border-radius: 8px;
        border: 1px solid #00ffff;
        margin: 4px;
        display: inline-block;
        font-weight: bold;
    }
    .hit-badge {
        background: rgba(188, 19, 254, 0.2);
        color: #bc13fe;
        padding: 4px 12px;
        border-radius: 8px;
        border: 1px solid #bc13fe;
        margin: 4px;
        display: inline-block;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# אזור הוספה
with st.container():
    history = list(st.session_state.alerts.keys())
    if history:
        st.write("🕒 בחירה מהירה:")
        h_cols = st.columns(min(len(history), 10))
        for idx, h_ticker in enumerate(history[:10]):
            if h_cols[idx].button(h_ticker, key=f"hist_{h_ticker}"):
                st.session_state.ticker_input = h_ticker

    c1, c2, c3 = st.columns([2, 2, 1])
    with c1: st.text_input("סימול מניה:", key="ticker_input")
    with c2: st.number_input("מחיר יעד ($):", key="price_input", step=0.01, value=None, on_change=add_alert_callback)
    with c3:
        st.write("##")
        if st.button("➕ הוסף", use_container_width=True): add_alert_callback()

st.divider()
edit_mode = st.sidebar.toggle("🛠️ מצב עריכה (מחיקה)")

# תצוגה
if st.session_state.alerts:
    for t, alert_list in list(st.session_state.alerts.items()):
        with st.container():
            st.markdown('<div class="stock-card">', unsafe_allow_html=True)
            col_info, col_prices = st.columns([1, 2])
            try:
                stock_data = yf.Ticker(t).fast_info
                current_p = stock_data['last_price']
                with col_info:
                    st.markdown(f"### {t}")
                    st.markdown(f'<div class="price-main">${current_p:.2f}</div>', unsafe_allow_html=True)
                
                with col_prices:
                    needs_save = False
                    for idx, alert in enumerate(alert_list):
                        p, dir, hit = alert['price'], alert['direction'], alert.get('hit', False)
                        
                        if hit:
                            st.markdown(f'<div class="hit-badge">🎯 {p}$ הושג!</div>', unsafe_allow_html=True)
                        else:
                            is_hit = (dir == 'UP' and current_p >= p) or (dir == 'DOWN' and current_p <= p)
                            if is_hit:
                                alert['hit'] = True
                                needs_save = True
                                st.markdown(f'<div class="hit-badge">🎯 {p}$ הושג!</div>', unsafe_allow_html=True)
                                # שליחה לטלגרם בשורה אחת:
                                send_telegram_msg(f"🚀 {t} HIT! Target: ${p:,.2f} | Price: ${current_p:,.2f} ✅")
                            elif not edit_mode:
                                sym = "▲" if dir == 'UP' else "▼"
                                st.markdown(f'<div class="price-badge">🔔 {sym} {p}$</div>', unsafe_allow_html=True)
                        
                        if edit_mode:
                            if st.button(f"🗑️ {p}$", key=f"del_{t}_{idx}"):
                                st.session_state.alerts[t].pop(idx)
                                if not st.session_state.alerts[t]: del st.session_state.alerts[t]
                                save_data(st.session_state.alerts)
                                st.rerun()
                    
                    if needs_save: save_data(st.session_state.alerts)
            except Exception as e:
                st.write("טוען נתונים...")
            

            st.markdown('</div>', unsafe_allow_html=True)

