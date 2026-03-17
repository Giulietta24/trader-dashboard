import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime

# ── FINNHUB / YFINANCE DUAL-SOURCE LAYER ──────────────────────────────────────
def _finnhub_key():
    try:
        return st.secrets.get("FINNHUB_KEY") or st.secrets.get("finnhub_key")
    except:
        return None

@st.cache_data(ttl=60)
def _fh_quote(sym: str, key: str) -> dict:
    try:
        r = requests.get(f"https://finnhub.io/api/v1/quote?symbol={sym}&token={key}", timeout=5)
        d = r.json()
        if d.get("c", 0) > 0:
            return {"price": d["c"], "chg_pct": d["dp"], "chg_abs": d["d"],
                    "open": d["o"], "high": d["h"], "low": d["l"],
                    "prev_close": d["pc"], "ok": True, "source": "finnhub"}
    except:
        pass
    return {"ok": False}

def get_live_price(sym: str) -> dict:
    key = _finnhub_key()
    if key:
        fh = _fh_quote(sym, key)
        if fh.get("ok"):
            return fh
    try:
        h = yf.Ticker(sym).history(period="2d")
        if not h.empty and len(h) >= 2:
            p, prev = h["Close"].iloc[-1], h["Close"].iloc[-2]
            return {"price": p, "chg_pct": (p - prev) / prev * 100,
                    "chg_abs": p - prev, "ok": True, "source": "yfinance"}
    except:
        pass
    return {"ok": False, "source": "none"}

def data_source_badge():
    key = _finnhub_key()
    if key:
        return '<span class="badge b-buy">● REAL-TIME · FINNHUB</span>'
    return '<span class="badge b-hold">◐ 15-MIN DELAY · YFINANCE</span>'

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Trader Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── LIGHT THEME CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.block-container{padding:1rem 1.5rem 2rem;max-width:1600px;}
[data-testid="collapsedControl"]{display:none!important;}
section[data-testid="stSidebar"]{display:none!important;}
.sec{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
     color:#9ca3af;margin:1.4rem 0 .7rem;border-bottom:1px solid #e5e7eb;padding-bottom:5px;}
.card{background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:12px 16px;}
.lbl{font-size:11px;color:#9ca3af;letter-spacing:.04em;text-transform:uppercase;margin-bottom:4px;}
.val{font-size:22px;font-weight:600;color:#111827;}
.sub{font-size:12px;color:#6b7280;margin-top:2px;}
.up{color:#16a34a!important;}.dn{color:#dc2626!important;}.neu{color:#9ca3af!important;}.warn{color:#d97706!important;}
.badge{display:inline-block;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:600;}
.b-buy{background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;}
.b-sell{background:#fef2f2;color:#b91c1c;border:1px solid #fecaca;}
.b-hold{background:#fffbeb;color:#b45309;border:1px solid #fde68a;}
.b-neu{background:#f9fafb;color:#6b7280;border:1px solid #e5e7eb;}
.hm{border-radius:6px;padding:8px 6px;text-align:center;}
.sig{background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:8px;text-align:center;}
.sig-n{font-size:9px;color:#9ca3af;letter-spacing:.04em;margin-bottom:2px;}
.sig-v{font-size:11px;font-weight:600;color:#111827;}
.tip-wrap{position:relative;display:inline-block;cursor:pointer;}
.tip-wrap .tip-box{visibility:hidden;opacity:0;background:#1e293b;color:#f1f5f9;font-size:11px;
  line-height:1.5;padding:8px 10px;border-radius:6px;width:220px;position:absolute;
  bottom:125%;left:50%;transform:translateX(-50%);z-index:999;pointer-events:none;
  transition:opacity .2s;font-weight:400;}
.tip-wrap:hover .tip-box{visibility:visible;opacity:1;}
.tip-wrap .tip-box::after{content:"";position:absolute;top:100%;left:50%;margin-left:-5px;
  border:5px solid transparent;border-top-color:#1e293b;}
</style>
""", unsafe_allow_html=True)

# ── DATA FUNCTIONS ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_quote(sym):
    try:
        t = yf.Ticker(sym)
        h = t.history(period="3mo")
        h1y = t.history(period="1y")
        info = t.info
        return {"h": h, "h1y": h1y, "info": info, "ok": True}
    except Exception as e:
        return {"ok": False, "err": str(e)}

@st.cache_data(ttl=300)
def get_indexes():
    syms = {"SPY":  ("#2563eb", "Large Cap",  "S&P 500"),
            "QQQ":  ("#7c3aed", "Tech/Growth", "Nasdaq 100"),
            "^DJI": ("#059669", "Mega Cap",    "Dow Jones"),
            "IWM":  ("#dc2626", "Small Cap",   "Russell 2000")}
    out = {}
    for sym, (col, cap, name) in syms.items():
        d = get_quote(sym)
        if d["ok"] and not d["h"].empty:
            h = d["h"]
            p   = h["Close"].iloc[-1]
            p1  = h["Close"].iloc[-2]
            chg1d = (p - p1) / p1 * 100
            chg1w = (p - h["Close"].iloc[-6])  / h["Close"].iloc[-6]  * 100 if len(h) >= 6  else 0
            chg1m = (p - h["Close"].iloc[-22]) / h["Close"].iloc[-22] * 100 if len(h) >= 22 else 0
            sma50 = h["Close"].tail(50).mean()
            vol_avg   = h["Volume"].tail(20).mean()
            vol_today = h["Volume"].iloc[-1]
            spark = h["Close"].tail(30).tolist()
            out[sym] = {"color": col, "cap": cap, "name": name, "price": p,
                        "chg1d": chg1d, "chg1w": chg1w, "chg1m": chg1m,
                        "sma50": sma50, "above50": p > sma50,
                        "vol_ratio": vol_today / vol_avg if vol_avg > 0 else 1,
                        "spark": spark, "hist": h}
    return out

@st.cache_data(ttl=300)
def get_macro():
    macro_syms = {"^VIX": "VIX", "^TNX": "10Y Yield", "^FVX": "5Y Yield",
                  "^IRX": "3M T-Bill", "DX-Y.NYB": "DXY"}
    out = {}
    for sym, name in macro_syms.items():
        try:
            h = yf.Ticker(sym).history(period="5d")
            if not h.empty and len(h) >= 2:
                p, prev = h["Close"].iloc[-1], h["Close"].iloc[-2]
                out[name] = {"price": p,
                             "chg": p - prev if ("Yield" in name or name == "3M T-Bill") else (p - prev) / prev * 100}
        except:
            pass
    return out

@st.cache_data(ttl=300)
def get_commodities():
    syms = {
        "GC=F":  ("Gold",      "/oz"),
        "SI=F":  ("Silver",    "/oz"),
        "HG=F":  ("Copper",    "/lb"),
        "CL=F":  ("WTI Crude", "/bbl"),
        "BZ=F":  ("Brent",     "/bbl"),
        "NG=F":  ("Nat Gas",   "/MMBtu"),
        "ZW=F":  ("Wheat",     "¢/bu"),
        "ZC=F":  ("Corn",      "¢/bu"),
        "ZS=F":  ("Soybeans",  "¢/bu"),
        "SB=F":  ("Sugar",     "¢/lb"),
        "KC=F":  ("Coffee",    "¢/lb"),
        "CC=F":  ("Cocoa",     "$/t"),
        "CT=F":  ("Cotton",    "¢/lb"),
        "LBS=F": ("Lumber",    "$/1k bf"),
    }
    out = {}
    for sym, (name, unit) in syms.items():
        try:
            h = yf.Ticker(sym).history(period="5d")
            if not h.empty and len(h) >= 2:
                p, prev = h["Close"].iloc[-1], h["Close"].iloc[-2]
                out[name] = {"price": p, "chg": (p - prev) / prev * 100, "unit": unit}
        except:
            pass
    return out

@st.cache_data(ttl=600)
def get_sectors():
    etfs = {"XLK": "Tech", "XLE": "Energy", "XLI": "Industrials", "XLF": "Financials",
            "XLC": "Comm", "XLV": "Health", "XLY": "Disc", "XLP": "Staples",
            "XLU": "Utilities", "XLRE": "R.Estate", "XLB": "Materials"}
    out = {}
    for sym, name in etfs.items():
        try:
            h = yf.Ticker(sym).history(period="1mo")
            if not h.empty and len(h) >= 5:
                p = h["Close"].iloc[-1]
                out[name] = {
                    "1d": (p - h["Close"].iloc[-2])  / h["Close"].iloc[-2]  * 100,
                    "1w": (p - h["Close"].iloc[-6])  / h["Close"].iloc[-6]  * 100 if len(h) >= 6 else 0,
                    "1m": (p - h["Close"].iloc[0])   / h["Close"].iloc[0]   * 100,
                }
        except:
            pass
    return out

@st.cache_data(ttl=3600)  # refresh every hour
def get_earnings_calendar(key: str) -> list:
    """Fetch upcoming earnings from Finnhub for the next 60 days."""
    try:
        today = datetime.now()
        date_from = today.strftime("%Y-%m-%d")
        date_to   = (today + pd.Timedelta(days=60)).strftime("%Y-%m-%d")
        r = requests.get(
            f"https://finnhub.io/api/v1/calendar/earnings"
            f"?from={date_from}&to={date_to}&token={key}",
            timeout=8
        )
        data = r.json().get("earningsCalendar", [])
        # Filter to well-known large caps only, sort by date
        watchlist = {"AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","AMD",
                     "NFLX","ORCL","INTC","QCOM","CRM","AVGO","JPM","GS","BAC",
                     "WMT","HD","V","MA","UNH","LLY","JNJ","XOM","CVX"}
        out = []
        for e in data:
            sym = e.get("symbol","")
            if sym in watchlist:
                date_str = e.get("date","")
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                    out.append({
                        "symbol": sym,
                        "date":   dt.strftime("%b %d"),
                        "hour":   e.get("hour",""),  # bmo=before open, amc=after close
                    })
                except:
                    pass
        # Sort by date, take first 6
        out.sort(key=lambda x: datetime.strptime(x["date"], "%b %d"))
        return out[:6]
    except:
        return []


@st.cache_data(ttl=600)
def compute_signals(sym):
    d = get_quote(sym)
    if not d["ok"] or d["h1y"].empty or len(d["h1y"]) < 50:
        return None
    h = d["h1y"]
    close, vol = h["Close"], h["Volume"]
    price = close.iloc[-1]

    sma50  = close.tail(50).mean()
    sma200 = close.tail(200).mean() if len(close) >= 200 else close.mean()
    ema20  = close.ewm(span=20).mean().iloc[-1]

    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rsi   = float((100 - 100 / (1 + gain / loss)).iloc[-1])

    ema12, ema26 = close.ewm(span=12).mean(), close.ewm(span=26).mean()
    macd_hist = float((ema12 - ema26 - (ema12 - ema26).ewm(span=9).mean()).iloc[-1])

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_pos = (price - float((bb_mid - 2 * bb_std).iloc[-1])) / (float(4 * bb_std.iloc[-1]) + 1e-9)

    tr  = pd.concat([h["High"] - h["Low"],
                     (h["High"] - close.shift()).abs(),
                     (h["Low"]  - close.shift()).abs()], axis=1).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1])
    vol_ratio = float(vol.iloc[-1] / vol.tail(20).mean())

    chg1d = float((price - close.iloc[-2])  / close.iloc[-2]  * 100)
    chg1w = float((price - close.iloc[-6])  / close.iloc[-6]  * 100) if len(close) >= 6  else 0
    chg1m = float((price - close.iloc[-22]) / close.iloc[-22] * 100) if len(close) >= 22 else 0
    chg3m = float((price - close.iloc[-66]) / close.iloc[-66] * 100) if len(close) >= 66 else 0

    score = 50
    if price > sma50:  score += 12
    else: score -= 15
    if price > sma200: score += 10
    else: score -= 15
    if price > ema20:  score += 5
    if rsi > 50: score += 5
    if 40 < rsi < 70: score += 3
    elif rsi > 75: score -= 8
    elif rsi < 35: score -= 8
    if macd_hist > 0: score += 8
    else: score -= 10
    if bb_pos > 0.5: score += 5
    if vol_ratio > 1.1: score += 5
    if chg1m > 0: score += 5
    score = max(0, min(100, score))

    return {"price": price, "sma50": sma50, "sma200": sma200, "ema20": ema20,
            "rsi": rsi, "macd_hist": macd_hist, "bb_pos": bb_pos,
            "atr": atr, "vol_ratio": vol_ratio,
            "chg1d": chg1d, "chg1w": chg1w, "chg1m": chg1m, "chg3m": chg3m,
            "score": score, "close_series": close.tail(60).tolist(),
            "info": d["info"]}

# ── HELPERS ────────────────────────────────────────────────────────────────────

def clr(v, good_pos=True):
    return ("#16a34a" if v >= 0 else "#dc2626") if good_pos else ("#dc2626" if v >= 0 else "#16a34a")

def arr(v): return "▲" if v >= 0 else "▼"

def fp(v):
    if v >= 1000: return f"{v:,.2f}"
    return f"{v:.2f}"

def verdict(s):
    if s >= 80: return ("STRONG BUY",   "#f0fdf4", "#15803d")
    if s >= 65: return ("BUY",           "#f0fdf4", "#16a34a")
    if s >= 50: return ("HOLD / NEUTRAL","#fffbeb", "#d97706")
    if s >= 35: return ("WEAK / AVOID",  "#fef2f2", "#dc2626")
    return             ("STRONG SELL",   "#fef2f2", "#b91c1c")

def spark_html(data, col="#2563eb", h=26):
    if not data: return ""
    mn, mx = min(data), max(data)
    rng = mx - mn or 1
    bars = "".join(
        f'<div style="flex:1;height:{max(int((v-mn)/rng*h),2)}px;'
        f'background:{"' + col + '" if i==len(data)-1 else "#e5e7eb"};'
        f'border-radius:1px 1px 0 0;align-self:flex-end;"></div>'
        for i, v in enumerate(data)
    )
    return f'<div style="display:flex;align-items:flex-end;gap:1px;height:{h}px;margin:5px 0 3px;">{bars}</div>'

def hm_clr(v):
    if v >= 2:   return "#dcfce7", "#15803d"
    if v >= .5:  return "#f0fdf4", "#16a34a"
    if v >= -.5: return "#f9fafb", "#6b7280"
    if v >= -2:  return "#fef2f2", "#dc2626"
    return             "#fee2e2", "#b91c1c"

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    st.markdown("---")
    heat_period = st.radio("Heatmap Period", ["1d", "1w", "1m"], horizontal=True)
    st.markdown("---")
    st.caption(f"Data: Yahoo Finance\nPrices ~15 min delayed\nLast loaded: {datetime.now().strftime('%H:%M:%S')}")
    st.markdown("---")
    st.caption("⚠️ Not financial advice.")

# ── HEADER ─────────────────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.title("📊 Trader Intelligence Dashboard")
    st.caption(f"Live market data · {datetime.now().strftime('%A %d %B %Y · %H:%M')} · Yahoo Finance")
with col_h2:
    st.markdown(f'<div style="text-align:right;padding-top:20px;">{data_source_badge()}</div>',
                unsafe_allow_html=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — INDEX COMPARISON
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">📊 Index Comparison — SPY · QQQ · DOW · IWM</div>', unsafe_allow_html=True)

with st.spinner("Loading index data..."):
    idx = get_indexes()

c1, c2, c3, c4 = st.columns(4)
for col, sym in zip([c1, c2, c3, c4], ["SPY", "QQQ", "^DJI", "IWM"]):
    d = idx.get(sym)
    display_sym = "DOW" if sym == "^DJI" else sym
    with col:
        if d:
            sp = spark_html(d["spark"], d["color"])
            trend_bg  = "#f0fdf4" if d["above50"] else "#fef2f2"
            trend_col = "#15803d" if d["above50"] else "#b91c1c"
            trend_lbl = "Above 50-DMA" if d["above50"] else "Below 50-DMA"
            st.markdown(f"""
            <div class="card">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:14px;font-weight:700;color:{d['color']};">{display_sym}</span>
                <span style="background:{trend_bg};color:{trend_col};font-size:9px;padding:2px 7px;
                      border-radius:4px;font-weight:600;">{trend_lbl}</span>
              </div>
              {sp}
              <div style="font-size:22px;font-weight:700;color:{d['color']};">{fp(d['price'])}</div>
              <div style="font-size:12px;font-weight:600;color:{clr(d['chg1d'])};">{arr(d['chg1d'])} {d['chg1d']:+.2f}% today</div>
              <div style="font-size:11px;color:#9ca3af;margin-top:5px;">{d['name']} · {d['cap']}</div>
              <div style="font-size:11px;color:#9ca3af;">
                1W <span style="color:{clr(d['chg1w'])};font-weight:600;">{d['chg1w']:+.1f}%</span> ·
                1M <span style="color:{clr(d['chg1m'])};font-weight:600;">{d['chg1m']:+.1f}%</span> ·
                Vol <span style="color:{clr(d['vol_ratio']-1)};font-weight:600;">{d['vol_ratio']:.1f}x</span>
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="card"><div style="color:#9ca3af;font-size:12px;">{display_sym} — loading...</div></div>',
                        unsafe_allow_html=True)

# Divergence alert
if "SPY" in idx and "IWM" in idx:
    div = idx["SPY"]["chg1m"] - idx["IWM"]["chg1m"]
    if div > 4:
        st.warning(f"⚠️ **Cap-size divergence:** Small caps (IWM) lagging large caps (SPY) by **{div:.1f}pp** this month — historically precedes pullbacks.")
    elif idx["IWM"]["chg1m"] > idx["SPY"]["chg1m"]:
        st.success("✅ **Broad rally confirmation:** Small caps leading large caps — healthy signal.")

# 30-day relative performance chart
if idx:
    fig_idx = go.Figure()
    for sym, d in idx.items():
        if "hist" in d and not d["hist"].empty:
            h30   = d["hist"].tail(30)
            base  = h30["Close"].iloc[0]
            perf  = ((h30["Close"] - base) / base * 100)
            lbl   = "DOW" if sym == "^DJI" else sym
            fig_idx.add_trace(go.Scatter(
                x=list(range(len(perf))), y=perf.round(2).tolist(),
                name=lbl, mode="lines",
                line=dict(color=d["color"], width=2),
                hovertemplate=f"{lbl}: %{{y:.2f}}%<extra></extra>"
            ))
    fig_idx.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#ffffff",
        font=dict(family="Inter", color="#6b7280", size=10),
        margin=dict(l=40, r=20, t=10, b=30), height=200,
        legend=dict(orientation="h", y=1.1, font=dict(size=11)),
        xaxis=dict(showgrid=False, showticklabels=False, title="30 days"),
        yaxis=dict(gridcolor="#f3f4f6", ticksuffix="%"),
        hovermode="x unified"
    )
    st.plotly_chart(fig_idx, use_container_width=True, config={"displayModeBar": False})

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — MARKET CONDITIONS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🌐 Market Conditions — Rates · Volatility · FX</div>', unsafe_allow_html=True)

with st.spinner("Loading macro data..."):
    macro = get_macro()

m_cols = st.columns(6)
macro_items = [
    ("VIX",      "VIX",       False),
    ("10Y Yield","10Y Yield", False),
    ("5Y Yield", "5Y Yield",  False),
    ("3M T-Bill","3M T-Bill", False),
    ("DXY",      "DXY",       True),
]
for col, (key, label, good_up) in zip(m_cols[:5], macro_items):
    d = macro.get(key, {})
    p = d.get("price", 0); chg = d.get("chg", 0)
    is_yield = "Yield" in key or key == "3M T-Bill"
    c_col = clr(chg, good_up)
    with col:
        st.markdown(f"""
        <div class="card">
          <div class="lbl">{label}</div>
          <div class="val" style="color:{c_col};">{p:.2f}{'%' if is_yield else ''}</div>
          <div class="sub" style="color:{c_col};">{arr(chg)} {chg:+.2f}{'bps' if is_yield else '%'}</div>
        </div>""", unsafe_allow_html=True)

y10  = macro.get("10Y Yield", {}).get("price", 4.3)
y3m  = macro.get("3M T-Bill", {}).get("price", 3.6)
spread = y10 - y3m
with m_cols[5]:
    sc = "#16a34a" if spread > 0 else "#dc2626"
    st.markdown(f"""
    <div class="card">
      <div class="lbl">Yield Curve</div>
      <div class="val" style="color:{sc};">{spread:+.2f}%</div>
      <div class="sub" style="color:{sc};">{'Normal' if spread > 0 else 'INVERTED'}</div>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — COMMODITIES & ENERGY
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🛢️ Commodities & Energy</div>', unsafe_allow_html=True)

with st.spinner("Loading commodities..."):
    comms = get_commodities()

if comms:
    metals_energy = {k: v for k, v in comms.items() if k in ["Gold","Silver","Copper","WTI Crude","Brent","Nat Gas"]}
    agriculture   = {k: v for k, v in comms.items() if k in ["Wheat","Corn","Soybeans","Sugar","Coffee","Cocoa","Cotton","Lumber"]}

    comm_info = {
        "Gold":      ("⭐⭐⭐", "Fear gauge. Rises when markets are stressed. Watch vs VIX — both rising = serious risk-off. Affects gold miners (NEM, GOLD)."),
        "Silver":    ("⭐⭐",   "Follows gold but more volatile. Also industrial metal — rising silver = growth expectations up."),
        "Copper":    ("⭐⭐⭐", "Called Dr Copper — best economic predictor. Rising = global growth. Falling = slowdown coming. Watch before trading industrials & materials."),
        "WTI Crude": ("⭐⭐⭐", "Most important commodity. Drives inflation, Fed decisions, energy stocks (XLE), airlines, and consumer spending all at once."),
        "Brent":     ("⭐⭐⭐", "Global oil benchmark. Moves same as WTI but used for European & Asian pricing. Spike = inflation risk globally."),
        "Nat Gas":   ("⭐⭐",   "Drives utility stocks (XLU) and European energy. Winter spikes hurt consumer spending. Watch for inflation pass-through."),
        "Wheat":     ("⭐⭐",   "Key food inflation driver — feeds into CPI. Russia/Ukraine conflict makes this geopolitically sensitive. Affects ADM, BG."),
        "Corn":      ("⭐⭐",   "Feeds into food & fuel (ethanol) inflation. Rising corn = CPI pressure = Fed watches it. Affects ADM, MOS."),
        "Soybeans":  ("⭐⭐",   "China demand indicator — China buys huge amounts. Rising soybeans = China economy active. Affects BG, ADM."),
        "Sugar":     ("⭐",    "Affects consumer staples (Coke, Hershey, Mondelez costs). Limited broader market impact."),
        "Coffee":    ("⭐",    "Affects Starbucks margins directly. Watch before SBUX earnings. Limited broader impact."),
        "Cocoa":     ("⭐",    "Affects chocolate makers (Hershey, Mondelez). Currently near record highs — watch consumer staples margins."),
        "Cotton":    ("⭐",    "Affects apparel costs — Nike, PVH, Hanesbrands. Slow moving, limited direct market impact."),
        "Lumber":    ("⭐⭐",   "Leading indicator for housing market. Rising lumber = homebuilders active. Watch before DHI, LEN, TOL earnings."),
    }

    def render_comm_row(items):
        cols = st.columns(len(items))
        for col, (name, d) in zip(cols, items.items()):
            c = clr(d["chg"])
            info = comm_info.get(name, ("⭐", "Commodity price data."))
            stars, desc = info
            with col:
                st.markdown(f"""
                <div class="card" style="position:relative;">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div class="lbl">{name}</div>
                    <div class="tip-wrap">
                      <span style="font-size:11px;color:#9ca3af;cursor:pointer;">ℹ</span>
                      <div class="tip-box"><b>{name} {stars}</b><br>{desc}</div>
                    </div>
                  </div>
                  <div style="font-size:15px;font-weight:700;color:{c};">{fp(d["price"])}</div>
                  <div class="sub" style="color:{c};">{arr(d["chg"])} {d["chg"]:+.2f}%</div>
                  <div class="sub">{d["unit"]}</div>
                  <div style="font-size:11px;margin-top:3px;">{stars}</div>
                </div>""", unsafe_allow_html=True)

    if metals_energy:
        st.markdown('<div style="font-size:10px;color:#9ca3af;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin-bottom:5px;">Metals & Energy</div>', unsafe_allow_html=True)
        render_comm_row(metals_energy)

    if agriculture:
        st.markdown('<div style="font-size:10px;color:#9ca3af;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin:10px 0 5px;">Agriculture & Softs</div>', unsafe_allow_html=True)
        render_comm_row(agriculture)

st.markdown("""
<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;">
  <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:7px 14px;font-size:11px;">
    <span style="color:#9ca3af;">OPEC:</span> <span style="color:#d97706;font-weight:600;">Production cuts extended</span>
  </div>
  <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:7px 14px;font-size:11px;">
    <span style="color:#9ca3af;">Energy regime:</span> <span style="color:#d97706;font-weight:600;">Supply-constrained · Geopolitical premium active</span>
  </div>
  <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;padding:7px 14px;font-size:11px;">
    <span style="color:#9ca3af;">XLE vs SPY:</span> <span style="color:#16a34a;font-weight:600;">Outperforming YTD +6.1%</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — INFLATION
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">📈 Inflation Signals</div>', unsafe_allow_html=True)

inf_col1, inf_col2 = st.columns(2)
with inf_col1:
    inf_data = [
        ("CPI (YoY)",     "3.2%",       "#d97706", "Above 2% target"),
        ("Core CPI",      "3.8%",       "#dc2626", "Sticky — ex food & energy"),
        ("PCE (YoY)",     "2.8%",       "#d97706", "Fed preferred measure"),
        ("PPI (YoY)",     "2.4%",       "#16a34a", "Easing at producer level"),
        ("5Y Breakeven",  "2.51%",      "#d97706", "Market-implied inflation"),
        ("Fed Funds Rate","3.50–3.75%", "#d97706", "Held steady Jan 2026"),
    ]
    for label, val, c, note in inf_data:
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
             padding:8px 0;border-bottom:1px solid #f3f4f6;font-size:12px;">
          <div>
            <span style="color:#374151;font-weight:500;">{label}</span><br>
            <span style="font-size:10px;color:#9ca3af;">{note}</span>
          </div>
          <div style="font-weight:700;font-size:15px;color:{c};">{val}</div>
        </div>""", unsafe_allow_html=True)

with inf_col2:
    st.markdown('<div class="lbl" style="margin-bottom:10px;">Inflation Pressure by Category</div>', unsafe_allow_html=True)
    cat_bars = [("Shelter",  5.8, 8, "#dc2626"),
                ("Services", 4.9, 8, "#ef4444"),
                ("Food",     3.4, 8, "#d97706"),
                ("Energy",   2.1, 8, "#d97706"),
                ("Goods",    0.4, 8, "#16a34a")]
    for name, v, mx, c in cat_bars:
        pct = int(v / mx * 100)
        st.markdown(f"""
        <div style="margin-bottom:9px;">
          <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px;">
            <span style="color:#6b7280;">{name}</span>
            <span style="font-weight:700;color:{c};">{v}%</span>
          </div>
          <div style="height:6px;background:#f3f4f6;border-radius:3px;overflow:hidden;">
            <div style="height:6px;width:{pct}%;background:{c};border-radius:3px;"></div>
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:12px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:10px 14px;">
      <div class="lbl" style="margin-bottom:6px;">Fed Rate Path (Market Pricing)</div>
      <div style="font-size:12px;color:#374151;">Market pricing <span style="color:#d97706;font-weight:600;">0–1 cuts</span> in 2026 — Dec at earliest</div>
      <div style="font-size:11px;color:#9ca3af;margin-top:3px;">Rate: 3.50–3.75% · 3 cuts made in 2025</div>
      <div style="font-size:11px;color:#9ca3af;margin-top:2px;">Iran war risk: <span style="color:#dc2626;font-weight:600;">cuts now in doubt</span></div>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — SECTOR HEATMAP
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🔥 Sector Momentum Heatmap</div>', unsafe_allow_html=True)

with st.spinner("Loading sector data..."):
    sectors = get_sectors()

if sectors:
    hm_cols = st.columns(len(sectors))
    for col, (name, d) in zip(hm_cols, sectors.items()):
        v = d.get(heat_period, 0)
        bg, tc = hm_clr(v)
        sign = "+" if v >= 0 else ""
        with col:
            st.markdown(f"""
            <div class="hm" style="background:{bg};border:1px solid {'#bbf7d0' if v>=0.5 else '#fecaca' if v<=-0.5 else '#e5e7eb'};">
              <div style="font-size:10px;font-weight:600;color:{tc};">{name}</div>
              <div style="font-size:11px;color:{tc};font-weight:600;margin-top:1px;">{sign}{v:.1f}%</div>
            </div>""", unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex;justify-content:space-between;font-size:10px;color:#9ca3af;margin-top:5px;">
      <span style="color:#dc2626;">▼ Underperform</span><span>Neutral</span><span style="color:#16a34a;">▲ Outperform</span>
    </div>""", unsafe_allow_html=True)
else:
    st.info("Sector data loading — refresh in a moment")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — THEMES & MOMENTUM
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🎯 Market Themes & Momentum</div>', unsafe_allow_html=True)

themes = {
    "🔥 Hot": [
        ("AI Infrastructure",    "Semis · Data Centers · Power Grid", 98, ["NVDA","AMD","SMCI","CEG","VST"]),
        ("Defense & Aerospace",  "NATO spend · Rearmament cycle",     91, ["LMT","RTX","NOC","BA"]),
        ("Energy Transition",    "Nuclear · Grid storage · LNG",      84, ["NEE","CEG","ETN","FSLR"]),
        ("Reshoring/Industrials","Capex supercycle · Supply chain",    79, ["GE","ETN","CAT","HON"]),
        ("Biotech / GLP-1",      "Obesity · Metabolic drugs",         72, ["NVO","LLY","VRTX","REGN"]),
    ],
    "📉 Fading": [
        ("ESG / Clean Energy",  "Policy reversal headwinds",       38, ["ICLN","ENPH","SEDG","RUN"]),
        ("China Reopening",     "Geopolitical risk · Earnings miss",27, ["BABA","JD","NIO","BIDU"]),
        ("Office REITs",        "Structural vacancy · Rate pressure",22, ["SLG","BXP","VNO"]),
    ],
    "🌱 Emerging": [
        ("Quantum Computing", "Early-stage hardware race",      61, ["IONQ","RGTI","IBM","GOOGL"]),
        ("Humanoid Robotics", "Labor displacement play",        57, ["TSLA","ABB","HON","NVDA"]),
        ("Rare Earths",       "Supply chain strategic assets",  53, ["MP","UUUU","FCX","NEM"]),
    ],
}

tabs = st.tabs(list(themes.keys()))
for tab, (_, theme_list) in zip(tabs, themes.items()):
    with tab:
        for name, meta, score, tickers in theme_list:
            sc = "#16a34a" if score >= 70 else "#d97706" if score >= 45 else "#dc2626"
            c1t, c2t, c3t = st.columns([3, 1, 2])
            with c1t:
                st.markdown(f"**{name}**  \n<small style='color:#9ca3af'>{meta}</small>", unsafe_allow_html=True)
            with c2t:
                st.markdown(f"<div style='font-size:20px;font-weight:700;color:{sc};text-align:right;'>{score}</div>"
                            f"<div style='font-size:10px;color:#9ca3af;text-align:right;'>momentum</div>",
                            unsafe_allow_html=True)
            with c3t:
                pills = " ".join([
                    f'<span style="background:#f3f4f6;border:1px solid #e5e7eb;color:#2563eb;'
                    f'padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600;">{t}</span>'
                    for t in tickers])
                st.markdown(pills, unsafe_allow_html=True)
            st.markdown("<hr style='border-color:#f3f4f6;margin:6px 0;'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — SENTIMENT (LIVE)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">😱 Sentiment · Fear/Greed · Live Analyst Consensus · Insider Activity</div>', unsafe_allow_html=True)

vix_price = macro.get("VIX", {}).get("price", 18)
fg_score  = max(0, min(100, int(100 - (vix_price - 10) / 35 * 100)))
fg_lbl    = ("Extreme Greed" if fg_score >= 80 else "Greed" if fg_score >= 65 else
             "Neutral" if fg_score >= 45 else "Fear" if fg_score >= 25 else "Extreme Fear")
fg_col    = "#16a34a" if fg_score >= 65 else "#d97706" if fg_score >= 45 else "#dc2626"

@st.cache_data(ttl=3600)
def get_analyst_sentiment(symbols, key):
    out = {}
    for sym in symbols:
        try:
            r = requests.get(f"https://finnhub.io/api/v1/stock/recommendation?symbol={sym}&token={key}", timeout=5)
            data = r.json()
            if data:
                latest = data[0]
                buy  = latest.get("buy", 0) + latest.get("strongBuy", 0)
                hold = latest.get("hold", 0)
                sell = latest.get("sell", 0) + latest.get("strongSell", 0)
                total = buy + hold + sell
                if total > 0:
                    out[sym] = {"buy": buy, "hold": hold, "sell": sell,
                                "pct_buy": int(buy / total * 100),
                                "period": latest.get("period", "")}
        except:
            pass
    return out

@st.cache_data(ttl=3600)
def get_insider_sentiment(symbols, key):
    out = {}
    for sym in symbols:
        try:
            r = requests.get(
                f"https://finnhub.io/api/v1/stock/insider-sentiment?symbol={sym}&from=2025-01-01&token={key}",
                timeout=5)
            data = r.json().get("data", [])
            if data:
                latest = sorted(data, key=lambda x: x.get("month", 0))[-1]
                change = latest.get("change", 0)
                out[sym] = {"change": change,
                            "direction": "Buying" if change > 0 else "Selling",
                            "col": "#16a34a" if change > 0 else "#dc2626"}
        except:
            pass
    return out

sc1, sc2, sc3, sc4 = st.columns(4)
fh_key = _finnhub_key()
watchlist = ("SPY", "QQQ", "NVDA", "AAPL", "META", "MSFT", "AMZN")

with sc1:
    st.markdown(f"""
    <div class="card">
      <div class="lbl">Fear & Greed — Live (VIX)</div>
      <div style="font-size:34px;font-weight:700;color:{fg_col};">{fg_score}</div>
      <div style="font-size:13px;font-weight:600;color:{fg_col};margin:3px 0;">{fg_lbl}</div>
      <div style="height:8px;border-radius:4px;background:linear-gradient(to right,#dc2626,#d97706,#16a34a);
           position:relative;margin:8px 0 4px;">
        <div style="position:absolute;top:-3px;left:{max(fg_score-1,1)}%;width:3px;height:14px;
             background:#111827;border-radius:2px;"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:9px;color:#9ca3af;">
        <span>Ext Fear</span><span>Fear</span><span>Neutral</span><span>Greed</span><span>Ext</span>
      </div>
      <div style="font-size:10px;color:#9ca3af;margin-top:8px;">
        Live from VIX={vix_price:.1f}. Under 20=calm, 20-30=caution, over 30=fear, over 40=panic.
      </div>
    </div>""", unsafe_allow_html=True)

with sc2:
    if fh_key:
        with st.spinner("Loading analyst ratings..."):
            analyst = get_analyst_sentiment(watchlist, fh_key)
        st.markdown('<div class="card"><div class="lbl">Analyst Consensus — Live (Finnhub)</div><div style="margin-top:6px;">', unsafe_allow_html=True)
        if analyst:
            for sym, d in list(analyst.items())[:6]:
                bw = d["pct_buy"]
                bc = "#16a34a" if bw >= 60 else "#d97706" if bw >= 40 else "#dc2626"
                st.markdown(f"""
                <div style="margin-bottom:7px;">
                  <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px;">
                    <span style="font-weight:700;color:#374151;">{sym}</span>
                    <span style="color:{bc};font-weight:600;">{bw}% Buy &nbsp;·&nbsp; {d['buy']}B / {d['hold']}H / {d['sell']}S</span>
                  </div>
                  <div style="height:5px;background:#f3f4f6;border-radius:3px;overflow:hidden;">
                    <div style="height:5px;width:{bw}%;background:{bc};border-radius:3px;"></div>
                  </div>
                </div>""", unsafe_allow_html=True)
            st.markdown('<div style="font-size:10px;color:#9ca3af;margin-top:4px;">B=Buy H=Hold S=Sell · Source: Wall St analysts via Finnhub</div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card"><div class="lbl">Analyst Consensus</div><div style="font-size:12px;color:#9ca3af;padding:8px 0;">Add Finnhub key to Streamlit secrets for live analyst ratings.</div></div>', unsafe_allow_html=True)

with sc3:
    if fh_key:
        with st.spinner("Loading insider activity..."):
            insider = get_insider_sentiment(watchlist, fh_key)
        st.markdown('<div class="card"><div class="lbl">Insider Transactions — Live (Finnhub)</div><div style="margin-top:6px;">', unsafe_allow_html=True)
        if insider:
            for sym, d in list(insider.items())[:6]:
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                     padding:5px 0;border-bottom:1px solid #f3f4f6;font-size:12px;">
                  <span style="font-weight:700;color:#374151;">{sym}</span>
                  <span style="color:{d['col']};font-weight:600;">{d['direction']}</span>
                </div>""", unsafe_allow_html=True)
            st.markdown('<div style="font-size:10px;color:#9ca3af;margin-top:6px;">Company insiders buying = bullish signal. Selling = could be profit-taking or caution.</div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card"><div class="lbl">Insider Transactions</div><div style="font-size:12px;color:#9ca3af;padding:8px 0;">Add Finnhub key to Streamlit secrets for live insider transaction data.</div></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7b — AI OPTIONS FLOW ANALYSIS (Anthropic Claude)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🤖 AI Options Flow Analysis — Powered by Claude</div>', unsafe_allow_html=True)

def _anthropic_key():
    try:
        return st.secrets.get("ANTHROPIC_API_KEY") or st.secrets.get("anthropic_api_key")
    except:
        return None

@st.cache_data(ttl=1800)  # refresh every 30 min
def get_ai_options_analysis(spy_chg, qqq_chg, vix, spy_1m, qqq_1m, iwm_1m, sector_summary):
    """Use Claude to generate options flow analysis from live market data."""
    key = _anthropic_key()
    if not key:
        return None
    try:
        prompt = f"""You are an expert options trader. Based on these LIVE market conditions, analyze what the smart money options flow is likely showing and what trades to watch.

LIVE MARKET DATA:
- SPY today: {spy_chg:+.2f}% | 1-month: {spy_1m:+.1f}%
- QQQ today: {qqq_chg:+.2f}% | 1-month: {qqq_1m:+.1f}%
- IWM 1-month: {iwm_1m:+.1f}%
- VIX: {vix:.1f} ({"complacent - low fear" if vix < 18 else "caution zone" if vix < 25 else "elevated fear" if vix < 35 else "panic"})
- Sector performance: {sector_summary}

Provide a SHORT options flow analysis (max 120 words) covering:
1. What options activity the current market setup typically attracts (calls vs puts, which sectors)
2. One specific options strategy that fits current conditions (e.g. covered calls, CSPs, call debit spreads)
3. What to watch for in the next 2 weeks

Be specific, practical, and plain English. No jargon without explanation. End with one key risk to watch."""

        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 300,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=15
        )
        data = r.json()
        text = data.get("content", [{}])[0].get("text", "")
        return text.strip() if text else None
    except:
        return None

ant_key = _anthropic_key()
if ant_key:
    # Build sector summary from live data
    sector_summary = ""
    if sectors:
        top = sorted(sectors.items(), key=lambda x: -x[1].get("1d", 0))[:3]
        bot = sorted(sectors.items(), key=lambda x: x[1].get("1d", 0))[:2]
        sector_summary = f"Leading: {', '.join([s for s,_ in top])} | Lagging: {', '.join([s for s,_ in bot])}"
    else:
        sector_summary = "Data loading"

    spy_d  = idx.get("SPY", {})
    qqq_d  = idx.get("QQQ", {})
    iwm_d  = idx.get("IWM", {})

    with st.spinner("Claude is analysing current options flow..."):
        ai_analysis = get_ai_options_analysis(
            spy_chg=spy_d.get("chg1d", 0),
            qqq_chg=qqq_d.get("chg1d", 0),
            vix=vix_price,
            spy_1m=spy_d.get("chg1m", 0),
            qqq_1m=qqq_d.get("chg1m", 0),
            iwm_1m=iwm_d.get("chg1m", 0),
            sector_summary=sector_summary
        )

    if ai_analysis:
        st.markdown(f"""
        <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:16px 18px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
            <span style="font-size:16px;">🤖</span>
            <span style="font-size:12px;font-weight:700;color:#1d4ed8;">Claude AI · Options Flow Analysis · Live market data</span>
            <span style="font-size:10px;color:#93c5fd;margin-left:auto;">Refreshes every 30 min</span>
          </div>
          <div style="font-size:13px;color:#1e3a5f;line-height:1.7;">{ai_analysis}</div>
        </div>""", unsafe_allow_html=True)

        # Strategy legend
        st.markdown("""
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;font-size:11px;">
          <span style="background:#f0fdf4;color:#15803d;padding:2px 8px;border-radius:4px;font-weight:600;border:1px solid #bbf7d0;">LONG CALL — betting price goes UP</span>
          <span style="background:#fef2f2;color:#b91c1c;padding:2px 8px;border-radius:4px;font-weight:600;border:1px solid #fecaca;">LONG PUT — betting price goes DOWN</span>
          <span style="background:#f0fdf4;color:#15803d;padding:2px 8px;border-radius:4px;font-weight:600;border:1px solid #bbf7d0;">CSP — sell put to buy stock cheaper or collect premium</span>
          <span style="background:#eff6ff;color:#1d4ed8;padding:2px 8px;border-radius:4px;font-weight:600;border:1px solid #bfdbfe;">CC — covered call: sell call against stock you own for income</span>
          <span style="background:#faf5ff;color:#7e22ce;padding:2px 8px;border-radius:4px;font-weight:600;border:1px solid #e9d5ff;">SPREAD — buy one option, sell another to reduce cost</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("AI analysis unavailable — Claude API returned no data")
else:
    st.markdown("""
    <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:14px 18px;">
      <div style="font-size:13px;color:#6b7280;">
        Add your <b>ANTHROPIC_API_KEY</b> to Streamlit secrets to enable AI-powered options flow analysis using Claude.<br>
        <span style="font-size:11px;color:#9ca3af;">You already have this key from your Options Alpha Pro dashboard — just add it here too.</span>
      </div>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — CATALYST CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">📅 Catalyst Calendar</div>', unsafe_allow_html=True)

# Static macro events (always shown)
macro_events = [
    ("FOMC", "Mar 18", "Rate Decision", "HIGH", "warn"),
    ("GDP",  "Mar 27", "Q4 Final",      "MED",  "neu"),
    ("NFP",  "Apr 4",  "Jobs Report",   "HIGH", "warn"),
    ("CPI",  "Apr 10", "Inflation",     "HIGH", "warn"),
]

# Live earnings from Finnhub if key available, else static fallback
fh_key = _finnhub_key()
if fh_key:
    live_earnings = get_earnings_calendar(fh_key)
    earnings_events = [
        (e["symbol"], e["date"],
         f"Earnings ({'Pre-mkt' if e['hour']=='bmo' else 'After close' if e['hour']=='amc' else 'TBC'})",
         "HIGH", "buy")
        for e in live_earnings
    ]
    source_note = "Earnings dates: Finnhub (live)"
else:
    earnings_events = [
        ("AMZN",  "Apr 23", "Earnings", "HIGH", "buy"),
        ("MSFT",  "Apr 29", "Earnings", "HIGH", "buy"),
        ("GOOGL", "Apr 28", "Earnings", "HIGH", "buy"),
        ("NVDA",  "May 27", "Earnings", "HIGH", "buy"),
    ]
    source_note = "Earnings dates: estimated — add Finnhub key for live dates"

cats = macro_events + earnings_events

cc = st.columns(min(len(cats), 8))
for col, (t, d, typ, imp, c) in zip(cc, cats):
    bg = "#f0fdf4" if c=="buy" else "#fffbeb" if c=="warn" else "#f9fafb"
    tc = "#15803d" if c=="buy" else "#b45309" if c=="warn" else "#6b7280"
    bc = "#bbf7d0" if c=="buy" else "#fde68a" if c=="warn" else "#e5e7eb"
    ic = "#dc2626" if imp=="HIGH" else "#9ca3af"
    ib = "#fef2f2" if imp=="HIGH" else "#f9fafb"
    with col:
        st.markdown(f"""
        <div style="background:{bg};border:1px solid {bc};border-radius:6px;padding:8px 10px;">
          <div style="font-size:13px;font-weight:700;color:{tc};">{t}</div>
          <div style="font-size:10px;color:{tc};">{d}</div>
          <div style="font-size:10px;color:{tc};">{typ}</div>
          <span style="background:{ib};color:{ic};font-size:9px;padding:1px 5px;border-radius:2px;font-weight:600;">{imp}</span>
        </div>""", unsafe_allow_html=True)

st.caption(source_note)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — SHORT SQUEEZE RADAR (LIVE via yfinance)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">💥 Short Squeeze Radar — Live (Yahoo Finance)</div>', unsafe_allow_html=True)

@st.cache_data(ttl=43200)  # refresh every 12 hours — FINRA updates twice monthly
def get_short_interest(symbols):
    """Fetch live short interest % and days-to-cover from Yahoo Finance."""
    out = []
    for sym in symbols:
        try:
            info = yf.Ticker(sym).info
            si_pct = info.get("shortPercentOfFloat", 0)
            dtc    = info.get("shortRatio", 0)       # days to cover
            price  = info.get("currentPrice", 0) or info.get("regularMarketPrice", 0)
            # Get 1-month price change for momentum
            h = yf.Ticker(sym).history(period="1mo")
            mom = 0
            if not h.empty and len(h) >= 2:
                mom = (h["Close"].iloc[-1] - h["Close"].iloc[0]) / h["Close"].iloc[0] * 100
            if si_pct and si_pct > 0.05:  # only show if SI > 5%
                out.append({
                    "sym": sym,
                    "si_pct": si_pct * 100,   # convert to %
                    "dtc": dtc or 0,
                    "price": price,
                    "mom": mom,
                })
        except:
            pass
    # Sort by SI % descending
    out.sort(key=lambda x: -x["si_pct"])
    return out

squeeze_watchlist = ["SMCI","MSTR","GME","COIN","RIVN","SOFI","PLTR","BYND","TSLA","AMC","BBAI","SOUN"]

with st.spinner("Loading short interest data..."):
    sqz_data = get_short_interest(squeeze_watchlist)

if sqz_data:
    sqz_cols = st.columns(min(len(sqz_data), 8))
    for col, d in zip(sqz_cols, sqz_data[:8]):
        # Colour by momentum direction
        if d["mom"] > 2:
            bg, tc, bc = "#f0fdf4", "#15803d", "#bbf7d0"
            status = f"▲ {d['mom']:+.1f}%"
        elif d["mom"] < -2:
            bg, tc, bc = "#fef2f2", "#b91c1c", "#fecaca"
            status = f"▼ {d['mom']:+.1f}%"
        else:
            bg, tc, bc = "#f9fafb", "#6b7280", "#e5e7eb"
            status = "— flat"

        # Squeeze score: high SI + high DTC + positive momentum = high score
        squeeze_score = min(100, int((d["si_pct"] * 1.5) + (d["dtc"] * 3) + (max(d["mom"], 0) * 0.5)))

        with col:
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {bc};border-radius:6px;padding:8px;text-align:center;">
              <div style="font-size:13px;font-weight:700;color:{tc};">{d['sym']}</div>
              <div style="font-size:10px;color:{tc};margin-top:2px;">SI: {d['si_pct']:.1f}%</div>
              <div style="font-size:10px;color:{tc};">DTC: {d['dtc']:.1f}d</div>
              <div style="font-size:10px;color:{tc};">{status}</div>
              <div style="font-size:9px;background:{'#dcfce7' if squeeze_score>60 else '#fef9c3' if squeeze_score>35 else '#fee2e2'};
                   color:{'#15803d' if squeeze_score>60 else '#854d0e' if squeeze_score>35 else '#b91c1c'};
                   border-radius:3px;padding:1px 4px;margin-top:3px;font-weight:700;">
                Squeeze: {squeeze_score}
              </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:10px 14px;margin-top:8px;">
      <div style="font-size:11px;font-weight:600;color:#374151;margin-bottom:6px;">How to read this:</div>
      <div style="font-size:11px;color:#6b7280;line-height:1.7;">
        <b style="color:#374151;">SI %</b> = Short Interest: % of all shares currently being shorted. The higher this is, the more "fuel" for a squeeze.<br>
        <b style="color:#374151;">DTC</b> = Days to Cover: how many days it would take shorts to buy back all their shares. Higher = harder to exit = bigger squeeze potential.<br>
        <b style="color:#374151;">▲/▼ %</b> = 1-month price momentum. Green means shorts are already losing money — squeeze pressure building.
      </div>
      <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;font-size:11px;">
        <span style="background:#dcfce7;color:#15803d;padding:2px 8px;border-radius:4px;font-weight:600;">Squeeze 60+ = High risk — watch closely</span>
        <span style="background:#fef9c3;color:#854d0e;padding:2px 8px;border-radius:4px;font-weight:600;">35–60 = On the radar</span>
        <span style="background:#fee2e2;color:#b91c1c;padding:2px 8px;border-radius:4px;font-weight:600;">Under 35 = Shorts in control</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Live: Yahoo Finance · FINRA updates twice monthly · Only stocks with SI >5% shown")
else:
    st.info("Short interest data loading — try refreshing")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — LIVE STOCK SCREENER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🔬 Live Stock Screener</div>', unsafe_allow_html=True)
st.markdown("Enter any ticker for a live technical signal breakdown.")

scr_c1, scr_c2 = st.columns([2, 3])
with scr_c1:
    ticker_input = st.text_input("Ticker", value="NVDA", max_chars=8,
                                  label_visibility="collapsed",
                                  placeholder="e.g. NVDA, AAPL, TSLA").upper().strip()
    run = st.button("🔍 Analyse Live", use_container_width=True)
with scr_c2:
    st.markdown("**Quick picks:**")
    qp_cols = st.columns(10)
    for col, t in zip(qp_cols, ["NVDA","AAPL","META","MSFT","TSLA","AMD","AMZN","GOOGL","SPY","QQQ"]):
        with col:
            if st.button(t, key=f"qp_{t}"):
                ticker_input = t

if run or ticker_input:
    sym = ticker_input.strip().upper()
    if sym:
        with st.spinner(f"Fetching live data for {sym}..."):
            sig = compute_signals(sym)

        if sig and not sig.get("error"):
            score = sig["score"]
            ver, v_bg, v_col = verdict(score)
            price = sig["price"]
            info  = sig.get("info", {})

            r1, r2 = st.columns([3, 1])
            with r1:
                company = info.get("longName", sym)
                sector  = info.get("sector", "—")
                st.markdown(f"""
                <span style="font-size:22px;font-weight:700;color:#111827;">{sym}</span>
                <span style="font-size:13px;color:#9ca3af;margin-left:10px;">{company} · {sector}</span>
                """, unsafe_allow_html=True)
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;font-size:10px;color:#9ca3af;
                     margin-bottom:3px;margin-top:10px;">
                  <span style="color:#dc2626;font-weight:600;">STRONG SELL</span>
                  <span>NEUTRAL</span>
                  <span style="color:#16a34a;font-weight:600;">STRONG BUY</span>
                </div>
                <div style="height:12px;border-radius:6px;
                     background:linear-gradient(to right,#dc2626,#d97706,#16a34a);position:relative;">
                  <div style="position:absolute;top:-3px;left:{min(max(score-1,1),97)}%;
                       width:3px;height:18px;background:#111827;border-radius:2px;"></div>
                </div>""", unsafe_allow_html=True)

                p_cols = st.columns(5)
                for col, (label, val) in zip(p_cols, [
                        ("Price", f"${fp(price)}"),
                        ("1D",  f"{sig['chg1d']:+.2f}%"),
                        ("1W",  f"{sig['chg1w']:+.2f}%"),
                        ("1M",  f"{sig['chg1m']:+.2f}%"),
                        ("3M",  f"{sig['chg3m']:+.2f}%")]):
                    with col:
                        v_is_chg = label != "Price"
                        vc = clr(float(val.replace('%','').replace('$','').replace('+','').replace(',',''))
                                 if v_is_chg else 0) if v_is_chg else "#111827"
                        st.markdown(f"""
                        <div style="text-align:center;padding:7px;background:#f9fafb;
                             border:1px solid #e5e7eb;border-radius:6px;">
                          <div style="font-size:9px;color:#9ca3af;">{label}</div>
                          <div style="font-size:12px;font-weight:700;color:{vc};">{val}</div>
                        </div>""", unsafe_allow_html=True)

            with r2:
                st.markdown(f"""
                <div style="background:{v_bg};border:2px solid {v_col};border-radius:8px;
                     padding:16px;text-align:center;">
                  <div style="font-size:20px;font-weight:700;color:#111827;">${fp(price)}</div>
                  <div style="font-size:12px;font-weight:600;color:{clr(sig['chg1d'])};margin:3px 0;">
                    {arr(sig['chg1d'])} {sig['chg1d']:+.2f}% today</div>
                  <div style="font-size:16px;font-weight:700;color:{v_col};margin-top:8px;">{ver}</div>
                  <div style="font-size:14px;font-weight:700;color:{v_col};">Score: {score}/100</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("**Signal Matrix**")
            sigs = [
                ("SMA 50",   "Above" if price > sig["sma50"]   else "Below", "buy" if price > sig["sma50"]   else "sell"),
                ("SMA 200",  "Above" if price > sig["sma200"]  else "Below", "buy" if price > sig["sma200"]  else "sell"),
                ("EMA 20",   "Above" if price > sig["ema20"]   else "Below", "buy" if price > sig["ema20"]   else "sell"),
                ("RSI(14)",  f"{sig['rsi']:.0f}",
                 "buy" if 45 < sig['rsi'] < 70 else "sell" if sig['rsi'] > 75 or sig['rsi'] < 35 else "neu"),
                ("MACD",     "Positive" if sig["macd_hist"] > 0 else "Negative", "buy" if sig["macd_hist"] > 0 else "sell"),
                ("Bollinger",f"{sig['bb_pos']:.0%}",
                 "buy" if sig['bb_pos'] > 0.5 else "sell" if sig['bb_pos'] < 0.2 else "neu"),
                ("Volume",   f"{sig['vol_ratio']:.1f}x avg",   "buy" if sig['vol_ratio'] > 1.1 else "neu"),
                ("1M Trend", f"{sig['chg1m']:+.1f}%",          "buy" if sig['chg1m'] > 0 else "sell"),
            ]
            sig_cols = st.columns(8)
            for col, (n, v, s) in zip(sig_cols, sigs):
                bg    = "#f0fdf4" if s=="buy" else "#fef2f2" if s=="sell" else "#f9fafb"
                c_txt = "#16a34a" if s=="buy" else "#dc2626" if s=="sell" else "#6b7280"
                bc    = "#bbf7d0" if s=="buy" else "#fecaca" if s=="sell" else "#e5e7eb"
                with col:
                    st.markdown(f"""
                    <div class="sig" style="background:{bg};border-color:{bc};">
                      <div class="sig-n">{n}</div>
                      <div class="sig-v" style="color:{c_txt};">{v}</div>
                      <div style="background:transparent;color:{c_txt};font-size:9px;
                           font-weight:600;margin-top:2px;">{s.upper()}</div>
                    </div>""", unsafe_allow_html=True)

            fund_c, setup_c = st.columns(2)
            with fund_c:
                st.markdown("**Fundamental Snapshot**")
                pe    = info.get("trailingPE");  fwd_pe = info.get("forwardPE")
                eps_g = info.get("earningsQuarterlyGrowth", 0)
                rev_g = info.get("revenueGrowth", 0)
                marg  = info.get("profitMargins", 0)
                mc    = info.get("marketCap", 0)
                mc_s  = f"${mc/1e12:.1f}T" if mc>1e12 else f"${mc/1e9:.0f}B" if mc>1e9 else "N/A"
                for label, val in [
                        ("P/E (TTM)",     f"{pe:.1f}x"          if pe     else "N/A"),
                        ("Forward P/E",   f"{fwd_pe:.1f}x"      if fwd_pe else "N/A"),
                        ("EPS Growth",    f"{eps_g*100:+.1f}%"  if eps_g  else "N/A"),
                        ("Revenue Growth",f"{rev_g*100:+.1f}%"  if rev_g  else "N/A"),
                        ("Net Margin",    f"{marg*100:.1f}%"    if marg   else "N/A"),
                        ("Market Cap",    mc_s)]:
                    st.markdown(f"""
                    <div style="display:flex;justify-content:space-between;padding:6px 0;
                         border-bottom:1px solid #f3f4f6;font-size:12px;">
                      <span style="color:#6b7280;">{label}</span>
                      <span style="font-weight:600;color:#111827;">{val}</span>
                    </div>""", unsafe_allow_html=True)

            with setup_c:
                st.markdown("**Trade Setup (ATR-based)**")
                atr  = sig["atr"]
                stop = price - atr * 2
                t1, t2 = price * 1.08, price * 1.18
                rr   = (t1 - price) / (price - stop + 1e-9)
                for label, val, cls in [
                        ("Current Price",    f"${fp(price)}", ""),
                        ("ATR (14)",         f"${atr:.2f}",   ""),
                        ("Entry Zone",       f"${fp(price*0.99)}–${fp(price*1.005)}", ""),
                        ("Stop Loss (2×ATR)",f"${fp(stop)} (−{(price-stop)/price*100:.1f}%)", "dn"),
                        ("Target 1 (+8%)",   f"${fp(t1)}", "up"),
                        ("Target 2 (+18%)",  f"${fp(t2)}", "up"),
                        ("Risk/Reward",      f"{rr:.1f}:1", "up" if rr >= 2 else "warn")]:
                    vc = "color:#16a34a" if cls=="up" else "color:#dc2626" if cls=="dn" else "color:#d97706" if cls=="warn" else "color:#111827"
                    st.markdown(f"""
                    <div style="display:flex;justify-content:space-between;padding:6px 0;
                         border-bottom:1px solid #f3f4f6;font-size:12px;">
                      <span style="color:#6b7280;">{label}</span>
                      <span style="font-weight:600;{vc}">{val}</span>
                    </div>""", unsafe_allow_html=True)

            if sig["close_series"]:
                prices = sig["close_series"]
                mn_p = min(prices) * 0.98
                mx_p = max(prices) * 1.02
                fig_scr = go.Figure()
                fig_scr.add_trace(go.Scatter(
                    y=prices, mode="lines", name=sym,
                    line=dict(color="#2563eb", width=2),
                    fill="tozeroy", fillcolor="rgba(37,99,235,0.06)",
                    hovertemplate="$%{y:.2f}<extra></extra>"
                ))
                fig_scr.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#ffffff",
                    margin=dict(l=60, r=20, t=10, b=30), height=220,
                    font=dict(family="Inter", color="#9ca3af", size=10),
                    xaxis=dict(showgrid=False, showticklabels=False, title="60 trading days"),
                    yaxis=dict(gridcolor="#f3f4f6", tickprefix="$", range=[mn_p, mx_p]),
                    showlegend=False, hovermode="x unified"
                )
                st.plotly_chart(fig_scr, use_container_width=True, config={"displayModeBar": False})

        elif sig and sig.get("error"):
            st.error(f"Could not fetch **{sym}**: {sig['error']}")
        else:
            st.info(f"No data found for {sym}. Try a major US-listed stock.")

# ── FOOTER ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center;font-size:11px;color:#9ca3af;padding:8px 0;">
  ⚠️ For informational purposes only · Not financial advice · Always do your own research<br>
  Data: Yahoo Finance · Prices ~15 min delayed · Auto-refresh every 5 min
</div>
""", unsafe_allow_html=True)
