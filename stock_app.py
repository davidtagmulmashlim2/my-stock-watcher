import streamlit as st
import yfinance as yf
import json
import os
import requests
from streamlit_autorefresh import st_autorefresh

# --- הגדרות טלגרם מעודכנות ---

openai_api_key = st.secrets["OPENAI_API_KEY"]
TELEGRAM_CHAT_ID = "779151879" # שים לב: וודא שזה ה-ID שקיבלת מ-userinfobot
# פונקציית שליחה לטלגרם
def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        requests.post(url, data=payload)
    except: pass

st.set_page_config(page_title="NEON 2026", layout="wide")
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

# פונקציה לעדכון תיבת הטקסט מההיסטוריה ללא שגיאה
def set_ticker_callback(symbol):
    st.session_state.ticker_input = symbol

def add_alert_callback():
    t_in = st.session_state.ticker_input.upper()
    p_in = st.session_state.price_input
    if t_in and p_in:
        try:
            curr = yf.Ticker(t_in).fast_info['last_price']
            direction = 'UP' if p_in > curr else 'DOWN'
            if t_in not in st.session_state.alerts:
                st.session_state.alerts[t_in] = []
            st.session_state.alerts[t_in].append({"price": p_in, "direction": direction, "hit": False})
            save_data(st.session_state.alerts)
            st.session_state.ticker_input = ""
            st.session_state.price_input = None
            st.toast(f"נוסף {t_in}", icon="✅")
        except: st.toast("שגיאה", icon="⚠️")

# עיצוב דחוס ב-40%
st.markdown("""
    <style>
    .stApp { background: #0b0d11; color: #e0e0e0; }
    h3 { font-size: 0.9rem !important; display: inline; margin-left: 8px; }
    .price-main { color: #00ffff; font-size: 1rem !important; font-weight: 800; display: inline; margin-right: 10px; }
    
    .stock-card { 
        background: rgba(255, 255, 255, 0.03); 
        border-radius: 4px; padding: 4px 10px; 
        border-right: 3px solid #00ffff; margin-bottom: 3px;
        display: flex; align-items: center; white-space: nowrap;
    }

    .alerts-wrapper { display: inline-flex; flex-wrap: nowrap; gap: 4px; }
    .price-badge { background: rgba(0, 255, 255, 0.05); color: #00ffff; padding: 1px 5px; border-radius: 3px; border: 1px solid rgba(0, 255, 255, 0.2); font-size: 0.65rem !important; }
    .hit-badge { background: rgba(188, 19, 254, 0.1); color: #bc13fe; padding: 1px 5px; border-radius: 3px; border: 1px solid #bc13fe; font-size: 0.65rem !important; }

    /* כפתורי היסטוריה - זרימה חופשית בשורה אחת */
    .history-box { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 10px; }
    .stButton > button { padding: 2px 8px !important; font-size: 0.7rem !important; height: auto !important; }
    </style>
    """, unsafe_allow_html=True)

# 1. הזנה למעלה
c1, c2, c3 = st.columns([2, 2, 1])
with c1: st.text_input("סימול:", key="ticker_input")
with c2: st.number_input("יעד ($):", key="price_input", step=0.01, value=None, on_change=add_alert_callback)
with c3:
    st.write("##")
    if st.button("➕", use_container_width=True): add_alert_callback()

# 2. בחירה מהירה - שורה אחת שמתמלאת ורק אז יורדת
history = list(st.session_state.alerts.keys())
if history:
    st.write("🕒 בחירה מהירה:")
    # יצירת מיכל לכפתורים
    container = st.container()
    with container:
        # פריסת כפתורים בשורה רציפה
        cols = st.columns(len(history) if len(history) < 10 else 10)
        for i, h_ticker in enumerate(history):
            col_idx = i % len(cols)
            with cols[col_idx]:
                st.button(h_ticker, key=f"h_{h_ticker}", on_click=set_ticker_callback, args=(h_ticker,))

st.divider()
edit_mode = st.sidebar.toggle("🛠️ עריכה")

# 3. רשימת מניות
if st.session_state.alerts:
    for t, alert_list in list(st.session_state.alerts.items()):
        alert_list.sort(key=lambda x: x['price'])
        try:
            stock_data = yf.Ticker(t).fast_info
            current_p = stock_data['last_price']
            
            card_html = f'<div class="stock-card"><div style="min-width: 110px;"><b>{t}</b> <span class="price-main">${current_p:.2f}</span></div><div class="alerts-wrapper">'
            
            needs_save = False
            for idx, alert in enumerate(alert_list):
                p, dir, hit = alert['price'], alert['direction'], alert.get('hit', False)
                if hit:
                    card_html += f'<div class="hit-badge">🎯 {p}$</div>'
                else:
                    is_hit = (dir == 'UP' and current_p >= p) or (dir == 'DOWN' and current_p <= p)
                    if is_hit:
                        alert['hit'] = True
                        needs_save = True
                        card_html += f'<div class="hit-badge">🎯 {p}$</div>'
                        send_telegram_msg(f"🚀 {t} HIT! ${p}")
                    elif not edit_mode:
                        sym = "▲" if dir == 'UP' else "▼"
                        card_html += f'<div class="price-badge">{sym} {p}$</div>'
                
                if edit_mode:
                    if st.button(f"🗑️ {p}", key=f"del_{t}_{idx}"):
                        st.session_state.alerts[t].pop(idx)
                        if not st.session_state.alerts[t]: del st.session_state.alerts[t]
                        save_data(st.session_state.alerts)
                        st.rerun()

            card_html += '</div></div>'
            st.markdown(card_html, unsafe_allow_html=True)
            if needs_save: save_data(st.session_state.alerts)
        except: pass

