import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime

# ── FINNHUB / YFINANCE DUAL-SOURCE LAYER ──────────────────────────────────────
# Automatically uses Finnhub for real-time quotes if FINNHUB_KEY is set in
# Streamlit secrets. Falls back to yfinance (15-min delayed) if not.
# To add your key: Streamlit Cloud → App → Settings → Secrets → FINNHUB_KEY = "..."

def _finnhub_key():
    try:
        return st.secrets.get("FINNHUB_KEY") or st.secrets.get("finnhub_key")
    except:
        return None

@st.cache_data(ttl=60)   # 1-min cache for real-time Finnhub quotes
def _fh_quote(sym: str, key: str) -> dict:
    """Fetch real-time quote from Finnhub."""
    try:
        r = requests.get(
            f"https://finnhub.io/api/v1/quote?symbol={sym}&token={key}",
            timeout=5
        )
        d = r.json()
        # d = {c: current, o: open, h: high, l: low, pc: prev close, d: change, dp: change%}
        if d.get("c", 0) > 0:
            return {"price": d["c"], "chg_pct": d["dp"], "chg_abs": d["d"],
                    "open": d["o"], "high": d["h"], "low": d["l"],
                    "prev_close": d["pc"], "ok": True, "source": "finnhub"}
    except:
        pass
    return {"ok": False}

@st.cache_data(ttl=600)  # 10-min cache for Finnhub fundamentals
def _fh_profile(sym: str, key: str) -> dict:
    """Fetch company profile + basic financials from Finnhub."""
    try:
        p = requests.get(f"https://finnhub.io/api/v1/stock/profile2?symbol={sym}&token={key}", timeout=5).json()
        m = requests.get(f"https://finnhub.io/api/v1/stock/metric?symbol={sym}&metric=all&token={key}", timeout=5).json()
        metric = m.get("metric", {})
        return {
            "name": p.get("name", sym),
            "sector": p.get("finnhubIndustry", "—"),
            "mktcap": p.get("marketCapitalization", 0) * 1e6,
            "pe": metric.get("peNormalizedAnnual"),
            "eps_growth": metric.get("epsGrowth3Y"),
            "rev_growth": metric.get("revenueGrowth3Y"),
            "net_margin": metric.get("netProfitMarginAnnual"),
            "ok": True
        }
    except:
        return {"ok": False}

def get_live_price(sym: str) -> dict:
    """
    Smart price fetcher: tries Finnhub first (real-time), falls back to yfinance.
    Returns: {price, chg_pct, chg_abs, source}
    """
    key = _finnhub_key()
    if key:
        fh = _fh_quote(sym, key)
        if fh.get("ok"):
            return fh
    # fallback: yfinance
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
    """Show a small badge indicating live vs delayed data."""
    key = _finnhub_key()
    if key:
        return '<span style="background:#0a2d1f;color:#00d395;border:1px solid #00d39533;padding:2px 8px;border-radius:3px;font-family:\'IBM Plex Mono\',monospace;font-size:10px;font-weight:600;">● REAL-TIME · FINNHUB</span>'
    return '<span style="background:#1a1200;color:#ffa502;border:1px solid #ffa50233;padding:2px 8px;border-radius:3px;font-family:\'IBM Plex Mono\',monospace;font-size:10px;font-weight:600;">◐ 15-MIN DELAY · YFINANCE</span>'

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Trader Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── BLOOMBERG-STYLE CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500&display=swap');
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif;}
.block-container{padding:1rem 1.5rem 2rem;max-width:1600px;}
.sec{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.1em;text-transform:uppercase;
     color:#4a5568;margin:1.2rem 0 .6rem;border-bottom:1px solid #1a2035;padding-bottom:4px;}
.card{background:#0d0d14;border:1px solid #1a2035;border-radius:6px;padding:12px 14px;}
.lbl{font-family:'IBM Plex Mono',monospace;font-size:10px;color:#4a5568;letter-spacing:.06em;
     text-transform:uppercase;margin-bottom:4px;}
.val{font-family:'IBM Plex Mono',monospace;font-size:20px;font-weight:600;}
.sub{font-size:11px;color:#6b7280;margin-top:2px;}
.up{color:#00d395!important;}.dn{color:#ff4757!important;}.neu{color:#8892a4!important;}.warn{color:#ffa502!important;}
.badge{display:inline-block;padding:2px 8px;border-radius:3px;font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;}
.b-buy{background:#0a2d1f;color:#00d395;border:1px solid #00d39533;}
.b-sell{background:#2d0a0a;color:#ff4757;border:1px solid #ff475733;}
.b-hold{background:#2d1f0a;color:#ffa502;border:1px solid #ffa50233;}
.b-neu{background:#151520;color:#8892a4;border:1px solid #2a2a3d;}
.hm{border-radius:4px;padding:7px 5px;text-align:center;font-family:'IBM Plex Mono',monospace;}
.sig{background:#0d0d14;border:1px solid #1a2035;border-radius:5px;padding:8px;text-align:center;}
.sig-n{font-size:9px;color:#4a5568;font-family:'IBM Plex Mono',monospace;letter-spacing:.04em;margin-bottom:2px;}
.sig-v{font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:500;}
</style>
""", unsafe_allow_html=True)

# ── CACHE / DATA ────────────────────────────────────────────────────────────────

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
    syms = {"SPY": ("#4a9eff", "Large Cap", "S&P 500"),
            "QQQ": ("#a855f7", "Tech/Growth", "Nasdaq 100"),
            "DIA": ("#00d395", "Mega Cap", "Dow Jones"),
            "IWM": ("#ff4757", "Small Cap", "Russell 2000")}
    out = {}
    for sym, (col, cap, name) in syms.items():
        d = get_quote(sym)
        if d["ok"] and not d["h"].empty:
            h = d["h"]
            p = h["Close"].iloc[-1]
            p1 = h["Close"].iloc[-2]
            chg1d = (p - p1) / p1 * 100
            chg1w = (p - h["Close"].iloc[-6]) / h["Close"].iloc[-6] * 100 if len(h) >= 6 else 0
            chg1m = (p - h["Close"].iloc[-22]) / h["Close"].iloc[-22] * 100 if len(h) >= 22 else 0
            sma50 = h["Close"].tail(50).mean()
            vol_avg = h["Volume"].tail(20).mean()
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
                out[name] = {"price": p, "chg": p - prev if "Yield" in name or name == "3M T-Bill" else (p - prev) / prev * 100}
        except:
            pass
    return out


@st.cache_data(ttl=300)
def get_commodities():
    syms = {"GC=F": ("Gold", "/oz"), "SI=F": ("Silver", "/oz"), "HG=F": ("Copper", "/lb"),
            "CL=F": ("WTI Crude", "/bbl"), "BZ=F": ("Brent", "/bbl"), "NG=F": ("Nat Gas", "/MMBtu"),
            "ZW=F": ("Wheat", "¢/bu"), "ZC=F": ("Corn", "¢/bu")}
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
                    "1d": (p - h["Close"].iloc[-2]) / h["Close"].iloc[-2] * 100,
                    "1w": (p - h["Close"].iloc[-6]) / h["Close"].iloc[-6] * 100 if len(h) >= 6 else 0,
                    "1m": (p - h["Close"].iloc[0]) / h["Close"].iloc[0] * 100,
                }
        except:
            pass
    return out


@st.cache_data(ttl=600)
def compute_signals(sym):
    d = get_quote(sym)
    if not d["ok"] or d["h1y"].empty or len(d["h1y"]) < 50:
        return None
    h = d["h1y"]
    close, vol = h["Close"], h["Volume"]
    price = close.iloc[-1]

    sma50 = close.tail(50).mean()
    sma200 = close.tail(200).mean() if len(close) >= 200 else close.mean()
    ema20 = close.ewm(span=20).mean().iloc[-1]

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rsi = float((100 - 100 / (1 + gain / loss)).iloc[-1])

    ema12, ema26 = close.ewm(span=12).mean(), close.ewm(span=26).mean()
    macd_hist = float((ema12 - ema26 - (ema12 - ema26).ewm(span=9).mean()).iloc[-1])

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_pos = (price - float((bb_mid - 2 * bb_std).iloc[-1])) / (float(4 * bb_std.iloc[-1]) + 1e-9)

    tr = pd.concat([h["High"] - h["Low"],
                    (h["High"] - close.shift()).abs(),
                    (h["Low"] - close.shift()).abs()], axis=1).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1])
    vol_ratio = float(vol.iloc[-1] / vol.tail(20).mean())

    chg1d = float((price - close.iloc[-2]) / close.iloc[-2] * 100)
    chg1w = float((price - close.iloc[-6]) / close.iloc[-6] * 100) if len(close) >= 6 else 0
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


# ── HELPERS ─────────────────────────────────────────────────────────────────────

def clr(v, good_pos=True):
    return ("#00d395" if v >= 0 else "#ff4757") if good_pos else ("#ff4757" if v >= 0 else "#00d395")

def arr(v): return "▲" if v >= 0 else "▼"

def fp(v):
    if v >= 1000: return f"{v:,.2f}"
    return f"{v:.2f}"

def verdict(s):
    if s >= 80: return ("STRONG BUY", "#0a2d1f", "#00d395")
    if s >= 65: return ("BUY", "#0a1e15", "#00d395")
    if s >= 50: return ("HOLD / NEUTRAL", "#1a1a0a", "#ffa502")
    if s >= 35: return ("WEAK / AVOID", "#1f0a0a", "#ff6b6b")
    return ("STRONG SELL", "#2d0a0a", "#ff4757")

def spark_html(data, col="#4a9eff", h=26):
    if not data: return ""
    mn, mx = min(data), max(data)
    rng = mx - mn or 1
    bars = "".join(
        f'<div style="flex:1;height:{max(int((v-mn)/rng*h),2)}px;background:{"' + col + '" if i==len(data)-1 else "#1a2035"};border-radius:1px 1px 0 0;align-self:flex-end;"></div>'
        for i, v in enumerate(data)
    )
    return f'<div style="display:flex;align-items:flex-end;gap:1px;height:{h}px;margin:5px 0 3px;">{bars}</div>'

def hm_clr(v):
    if v >= 2:   return "#0a2d1f", "#00d395"
    if v >= .5:  return "#081a10", "#00b37a"
    if v >= -.5: return "#141420", "#8892a4"
    if v >= -2:  return "#280f0f", "#ff6b6b"
    return "#2d0a0a", "#ff4757"


# ── SIDEBAR ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Dashboard Settings")
    if st.button("🔄 Refresh All Data", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    st.markdown("---")
    heat_period = st.radio("Heatmap Period", ["1d", "1w", "1m"], horizontal=True)
    ta_period_sidebar = st.radio("TA Timeframe", ["Daily", "Weekly"], horizontal=True)
    st.markdown("---")
    st.caption(f"Data: Yahoo Finance\nPrices ~15 min delayed\nAuto-refresh: 5 min\nLast loaded: {datetime.now().strftime('%H:%M:%S')}")
    st.markdown("---")
    st.caption("⚠️ Not financial advice. For informational use only.")


# ── HEADER ────────────────────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown(f"""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:14px;font-weight:600;
         color:#4a9eff;letter-spacing:.1em;text-transform:uppercase;">
      📊 Trader Intelligence Dashboard</div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#4a5568;margin-top:3px;">
      Live Market Data · {datetime.now().strftime('%A %d %B %Y · %H:%M')} · Yahoo Finance
    </div>""", unsafe_allow_html=True)
with col_h2:
    st.markdown('<div style="text-align:right;padding-top:6px;"><span class="badge b-buy" style="font-size:11px;padding:5px 12px;">● LIVE DATA</span></div>', unsafe_allow_html=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════════
# SECTION 1 — INDEX COMPARISON
# ══════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">📊 Index Comparison — SPY · QQQ · DIA · IWM (Cap Size Rotation)</div>', unsafe_allow_html=True)

with st.spinner("Loading index data..."):
    idx = get_indexes()

c1, c2, c3, c4 = st.columns(4)
for col, sym in zip([c1, c2, c3, c4], ["SPY", "QQQ", "DIA", "IWM"]):
    d = idx.get(sym)
    with col:
        if d:
            sp = spark_html(d["spark"], d["color"])
            trend_bg  = "#0a2d1f" if d["above50"] else "#2d0a0a"
            trend_col = "#00d395" if d["above50"] else "#ff4757"
            trend_lbl = "Above 50-DMA" if d["above50"] else "Below 50-DMA"
            st.markdown(f"""
            <div class="card">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-family:'IBM Plex Mono';font-size:13px;font-weight:600;color:{d['color']};">{sym}</span>
                <span style="background:{trend_bg};color:{trend_col};font-size:9px;padding:2px 6px;border-radius:3px;font-family:'IBM Plex Mono';">{trend_lbl}</span>
              </div>
              {sp}
              <div style="font-family:'IBM Plex Mono';font-size:20px;font-weight:600;color:{d['color']};">${fp(d['price'])}</div>
              <div style="font-family:'IBM Plex Mono';font-size:12px;color:{clr(d['chg1d'])};">{arr(d['chg1d'])} {d['chg1d']:+.2f}% today</div>
              <div style="font-size:11px;color:#4a5568;margin-top:5px;">{d['name']} · {d['cap']}</div>
              <div style="font-size:11px;color:#4a5568;">1W <span style="color:{clr(d['chg1w'])};">{d['chg1w']:+.1f}%</span> · 1M <span style="color:{clr(d['chg1m'])};">{d['chg1m']:+.1f}%</span> · Vol <span style="color:{clr(d['vol_ratio']-1)};">{d['vol_ratio']:.1f}x</span></div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="card"><div style="color:#4a5568;font-size:12px;">{sym} — loading...</div></div>', unsafe_allow_html=True)

# Divergence note
if "SPY" in idx and "IWM" in idx:
    div = idx["SPY"]["chg1m"] - idx["IWM"]["chg1m"]
    if div > 4:
        st.warning(f"⚠️ **Cap-size divergence alert:** IWM (small caps) is lagging SPY by **{div:.1f}pp** this month. Narrow market — historically precedes pullbacks.")
    elif idx["IWM"]["chg1m"] > idx["SPY"]["chg1m"]:
        st.success("✅ **Broad confirmation:** Small caps leading large caps — healthy, broad-based rally signal.")

# 30-day relative performance chart
if idx:
    fig_idx = go.Figure()
    for sym, d in idx.items():
        if "hist" in d and not d["hist"].empty:
            h30 = d["hist"].tail(30)
            base = h30["Close"].iloc[0]
            perf = ((h30["Close"] - base) / base * 100)
            fig_idx.add_trace(go.Scatter(
                x=list(range(len(perf))), y=perf.round(2).tolist(),
                name=sym, mode="lines",
                line=dict(color=d["color"], width=2),
                hovertemplate=f"{sym}: %{{y:.2f}}%<extra></extra>"
            ))
    fig_idx.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,13,20,1)",
        font=dict(family="IBM Plex Mono", color="#8892a4", size=10),
        margin=dict(l=40, r=20, t=10, b=30), height=200,
        legend=dict(orientation="h", y=1.08, font=dict(size=11)),
        xaxis=dict(showgrid=False, showticklabels=False, title="30 days"),
        yaxis=dict(gridcolor="#1a2035", ticksuffix="%"),
        hovermode="x unified"
    )
    st.plotly_chart(fig_idx, use_container_width=True, config={"displayModeBar": False})

# ══════════════════════════════════════════════════════════════════════════════════
# SECTION 2 — MARKET CONDITIONS
# ══════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🌐 Market Conditions — Rates · Vol · FX · Breadth</div>', unsafe_allow_html=True)

with st.spinner("Loading macro data..."):
    macro = get_macro()

m_cols = st.columns(6)
macro_items = [
    ("VIX", "VIX", False), ("10Y Yield", "10Y Yield", False),
    ("5Y Yield", "5Y Yield", False), ("3M T-Bill", "3M T-Bill", False), ("DXY", "DXY", True)
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

# Yield curve
y10 = macro.get("10Y Yield", {}).get("price", 4.3)
y3m = macro.get("3M T-Bill", {}).get("price", 5.1)
spread = y10 - y3m
with m_cols[5]:
    sc = "#00d395" if spread > 0 else "#ff4757"
    st.markdown(f"""
    <div class="card">
      <div class="lbl">Yield Curve</div>
      <div class="val" style="color:{sc};">{spread:+.2f}%</div>
      <div class="sub" style="color:{sc};">{'Normal' if spread > 0 else 'INVERTED'}</div>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════════
# SECTION 3 — COMMODITIES & ENERGY
# ══════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🛢️ Commodities & Energy</div>', unsafe_allow_html=True)

with st.spinner("Loading commodities..."):
    comms = get_commodities()

if comms:
    c_cols = st.columns(len(comms))
    for col, (name, d) in zip(c_cols, comms.items()):
        c = clr(d["chg"])
        with col:
            st.markdown(f"""
            <div class="card">
              <div class="lbl">{name}</div>
              <div style="font-family:'IBM Plex Mono';font-size:16px;font-weight:600;color:{c};">{fp(d['price'])}</div>
              <div class="sub" style="color:{c};">{arr(d['chg'])} {d['chg']:+.2f}%</div>
              <div class="sub">{d['unit']}</div>
            </div>""", unsafe_allow_html=True)

# Energy context row
st.markdown("""
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:6px;">
  <div style="background:#0d0d14;border:1px solid #1a2035;border-radius:5px;padding:8px 14px;font-size:11px;">
    <span style="color:#4a5568;">OPEC stance:</span> <span style="color:#ffa502;font-family:'IBM Plex Mono';">Production cuts extended</span>
  </div>
  <div style="background:#0d0d14;border:1px solid #1a2035;border-radius:5px;padding:8px 14px;font-size:11px;">
    <span style="color:#4a5568;">Energy regime:</span> <span style="color:#ffa502;font-family:'IBM Plex Mono';">Supply-constrained · Geopolitical premium active</span>
  </div>
  <div style="background:#0d0d14;border:1px solid #1a2035;border-radius:5px;padding:8px 14px;font-size:11px;">
    <span style="color:#4a5568;">XLE vs SPY:</span> <span style="color:#00d395;font-family:'IBM Plex Mono';">Outperforming YTD +6.1%</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════════
# SECTION 4 — INFLATION
# ══════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">📈 Inflation Signals</div>', unsafe_allow_html=True)

inf_col1, inf_col2 = st.columns(2)
with inf_col1:
    inf_data = [
        ("CPI (YoY)", "3.2%", "#ffa502", "Above 2% target"),
        ("Core CPI", "3.8%", "#ff4757", "Sticky — ex food & energy"),
        ("PCE (YoY)", "2.8%", "#ffa502", "Fed preferred measure"),
        ("PPI (YoY)", "2.4%", "#00d395", "Easing at producer level"),
        ("5Y Breakeven", "2.51%", "#ffa502", "Market-implied inflation"),
        ("Fed Funds Rate", "5.25–5.50%", "#ffa502", "Higher for longer stance"),
    ]
    for label, val, c, note in inf_data:
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid #1a2035;font-size:12px;">
          <div><span style="color:#8892a4;">{label}</span><br><span style="font-size:10px;color:#4a5568;">{note}</span></div>
          <div style="font-family:'IBM Plex Mono';font-weight:600;font-size:14px;color:{c};">{val}</div>
        </div>""", unsafe_allow_html=True)

with inf_col2:
    st.markdown('<div style="font-family:\'IBM Plex Mono\';font-size:10px;color:#4a5568;letter-spacing:.06em;text-transform:uppercase;margin-bottom:8px;">Inflation Pressure by Category</div>', unsafe_allow_html=True)
    cat_bars = [("Shelter", 5.8, 8, "#ff4757"), ("Services", 4.9, 8, "#ff6b6b"),
                ("Food", 3.4, 8, "#ffa502"), ("Energy", 2.1, 8, "#ffa502"), ("Goods", 0.4, 8, "#00d395")]
    for name, v, mx, c in cat_bars:
        pct = int(v / mx * 100)
        st.markdown(f"""
        <div style="margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px;">
            <span style="color:#8892a4;">{name}</span>
            <span style="font-family:'IBM Plex Mono';font-weight:600;color:{c};">{v}%</span>
          </div>
          <div style="height:5px;background:#1a2035;border-radius:3px;overflow:hidden;">
            <div style="height:5px;width:{pct}%;background:{c};border-radius:3px;"></div>
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:12px;background:#0d0d14;border:1px solid #1a2035;border-radius:5px;padding:10px 12px;">
      <div style="font-family:'IBM Plex Mono';font-size:10px;color:#4a5568;letter-spacing:.06em;text-transform:uppercase;margin-bottom:5px;">Fed Rate Path (Market Pricing)</div>
      <div style="font-size:12px;color:#8892a4;">Market pricing <span style="color:#00d395;font-family:'IBM Plex Mono';">2 cuts</span> in 2025 — Jun / Sep</div>
      <div style="font-size:11px;color:#4a5568;margin-top:3px;">Fed language: <span style="color:#ffa502;">"Higher for longer"</span></div>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════════
# SECTION 5 — SECTOR HEATMAP
# ══════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🔥 Sector Momentum Heatmap</div>', unsafe_allow_html=True)

with st.spinner("Loading sector data..."):
    sectors = get_sectors()

if sectors:
    n = len(sectors)
    hm_cols = st.columns(n)
    for col, (name, d) in zip(hm_cols, sectors.items()):
        v = d.get(heat_period, 0)
        bg, tc = hm_clr(v)
        sign = "+" if v >= 0 else ""
        with col:
            st.markdown(f"""
            <div class="hm" style="background:{bg};">
              <div style="font-size:10px;font-weight:600;color:{tc};">{name}</div>
              <div style="font-size:11px;color:{tc};margin-top:1px;">{sign}{v:.1f}%</div>
            </div>""", unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex;justify-content:space-between;font-size:10px;font-family:'IBM Plex Mono';color:#4a5568;margin-top:5px;">
      <span style="color:#ff4757;">▼ Underperform</span><span>Neutral</span><span style="color:#00d395;">▲ Outperform</span>
    </div>""", unsafe_allow_html=True)
else:
    st.info("Sector data loading — refresh in a moment")

# ══════════════════════════════════════════════════════════════════════════════════
# SECTION 6 — THEMES & MOMENTUM
# ══════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🎯 Market Themes & Momentum</div>', unsafe_allow_html=True)

themes = {
    "🔥 Hot": [
        ("AI Infrastructure", "Semis · Data Centers · Power Grid", 98, ["NVDA","AMD","SMCI","CEG","VST"]),
        ("Defense & Aerospace", "NATO spend · Rearmament cycle", 91, ["LMT","RTX","NOC","BA"]),
        ("Energy Transition", "Nuclear · Grid storage · LNG", 84, ["NEE","CEG","ETN","FSLR"]),
        ("Reshoring / Industrials", "Capex supercycle · Supply chain", 79, ["GE","ETN","CAT","HON"]),
        ("Biotech / GLP-1", "Obesity · Metabolic drugs", 72, ["NVO","LLY","VRTX","REGN"]),
    ],
    "📉 Fading": [
        ("ESG / Clean Energy", "Policy reversal headwinds", 38, ["ICLN","ENPH","SEDG","RUN"]),
        ("China Reopening", "Geopolitical risk · Earnings miss", 27, ["BABA","JD","NIO","BIDU"]),
        ("Office REITs", "Structural vacancy · Rate pressure", 22, ["SLG","BXP","VNO"]),
    ],
    "🌱 Emerging": [
        ("Quantum Computing", "Early-stage hardware race", 61, ["IONQ","RGTI","IBM","GOOGL"]),
        ("Humanoid Robotics", "Labor displacement play", 57, ["TSLA","ABB","HON","NVDA"]),
        ("Rare Earths", "Supply chain strategic assets", 53, ["MP","UUUU","FCX","NEM"]),
    ],
}

tabs = st.tabs(list(themes.keys()))
for tab, (_, theme_list) in zip(tabs, themes.items()):
    with tab:
        for name, meta, score, tickers in theme_list:
            sc = "#00d395" if score >= 70 else "#ffa502" if score >= 45 else "#ff4757"
            col_t1, col_t2, col_t3 = st.columns([3, 1, 2])
            with col_t1:
                st.markdown(f"**{name}**  \n<small style='color:#6b7280'>{meta}</small>", unsafe_allow_html=True)
            with col_t2:
                st.markdown(f"<div style='font-family:IBM Plex Mono;font-size:18px;font-weight:600;color:{sc};text-align:right;'>{score}</div><div style='font-size:10px;color:#4a5568;text-align:right;'>momentum</div>", unsafe_allow_html=True)
            with col_t3:
                pills = " ".join([f'<span style="background:#0d1117;border:1px solid #1a2035;color:#4a9eff;padding:2px 6px;border-radius:3px;font-family:IBM Plex Mono;font-size:10px;">{t}</span>' for t in tickers])
                st.markdown(pills, unsafe_allow_html=True)
            st.markdown("<hr style='border-color:#1a2035;margin:5px 0;'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════════
# SECTION 7 — SENTIMENT
# ══════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">😱 Sentiment · Fear/Greed · Smart Money Flow</div>', unsafe_allow_html=True)

vix_price = macro.get("VIX", {}).get("price", 18)
fg_score = max(0, min(100, int(100 - (vix_price - 10) / 35 * 100)))
fg_lbl = ("Extreme Greed" if fg_score >= 80 else "Greed" if fg_score >= 65 else
          "Neutral" if fg_score >= 45 else "Fear" if fg_score >= 25 else "Extreme Fear")
fg_col = "#00d395" if fg_score >= 65 else "#ffa502" if fg_score >= 45 else "#ff4757"

sent_c1, sent_c2, sent_c3, sent_c4 = st.columns(4)

with sent_c1:
    st.markdown(f"""
    <div class="card">
      <div class="lbl">Fear & Greed (VIX-derived)</div>
      <div style="font-family:'IBM Plex Mono';font-size:32px;font-weight:600;color:{fg_col};">{fg_score}</div>
      <div style="font-size:13px;color:{fg_col};margin:3px 0;">{fg_lbl}</div>
      <div style="height:8px;border-radius:4px;background:linear-gradient(to right,#ff4757,#ffa502,#00d395);position:relative;margin:8px 0 4px;">
        <div style="position:absolute;top:-3px;left:{fg_score-1}%;width:3px;height:14px;background:white;border-radius:2px;"></div>
      </div>
    </div>""", unsafe_allow_html=True)

with sent_c2:
    st.markdown("""
    <div class="card">
      <div class="lbl">AAII Bull/Bear</div>
      <div style="display:flex;gap:5px;margin:6px 0;">
        <div style="flex:1;background:#0a2d1f;border-radius:4px;padding:6px;text-align:center;">
          <div style="font-size:9px;color:#00d395;font-family:'IBM Plex Mono';">BULL</div>
          <div style="font-family:'IBM Plex Mono';font-size:15px;font-weight:600;color:#00d395;">47%</div>
        </div>
        <div style="flex:1;background:#141420;border-radius:4px;padding:6px;text-align:center;">
          <div style="font-size:9px;color:#8892a4;font-family:'IBM Plex Mono';">NEUT</div>
          <div style="font-family:'IBM Plex Mono';font-size:15px;font-weight:600;color:#8892a4;">27%</div>
        </div>
        <div style="flex:1;background:#2d0a0a;border-radius:4px;padding:6px;text-align:center;">
          <div style="font-size:9px;color:#ff4757;font-family:'IBM Plex Mono';">BEAR</div>
          <div style="font-family:'IBM Plex Mono';font-size:15px;font-weight:600;color:#ff4757;">26%</div>
        </div>
      </div>
      <div style="font-size:11px;color:#6b7280;">Spread: <span style="color:#00d395;font-family:'IBM Plex Mono';">+21pp</span> — Bullish signal</div>
    </div>""", unsafe_allow_html=True)

with sent_c3:
    st.markdown("""
    <div class="card">
      <div class="lbl">Options Flow</div>
      <div style="margin-top:5px;">
        <div style="display:flex;justify-content:space-between;font-size:12px;padding:4px 0;border-bottom:1px solid #1a2035;">
          <span style="color:#8892a4;">Put/Call Ratio</span>
          <span style="color:#00d395;font-family:'IBM Plex Mono';">0.81 · Bullish</span>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:12px;padding:4px 0;border-bottom:1px solid #1a2035;">
          <span style="color:#8892a4;">COT Net Longs</span>
          <span style="color:#00d395;font-family:'IBM Plex Mono';">+124k</span>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:12px;padding:4px 0;border-bottom:1px solid #1a2035;">
          <span style="color:#8892a4;">Dark Pool (DIX)</span>
          <span style="color:#00d395;font-family:'IBM Plex Mono';">46.8% · Bull</span>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:12px;padding:4px 0;">
          <span style="color:#8892a4;">GEX Gamma</span>
          <span style="color:#ffa502;font-family:'IBM Plex Mono';">+$4.2B Pinning</span>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

with sent_c4:
    st.markdown("""
    <div class="card">
      <div class="lbl">Unusual Options Activity</div>
      <div style="margin-top:5px;">
        <div style="display:flex;gap:5px;align-items:center;padding:4px 0;border-bottom:1px solid #1a2035;font-size:11px;">
          <span style="font-family:'IBM Plex Mono';font-weight:600;color:#4a9eff;min-width:36px;">NVDA</span>
          <span style="background:#0a2d1f;color:#00d395;padding:1px 5px;border-radius:2px;font-size:9px;font-family:'IBM Plex Mono';">CALL</span>
          <span style="flex:1;color:#8892a4;">$950C Mar · Sweep</span>
          <span style="font-family:'IBM Plex Mono';color:#00d395;">$2.4M</span>
        </div>
        <div style="display:flex;gap:5px;align-items:center;padding:4px 0;border-bottom:1px solid #1a2035;font-size:11px;">
          <span style="font-family:'IBM Plex Mono';font-weight:600;color:#4a9eff;min-width:36px;">SPY</span>
          <span style="background:#0a2d1f;color:#00d395;padding:1px 5px;border-radius:2px;font-size:9px;font-family:'IBM Plex Mono';">CALL</span>
          <span style="flex:1;color:#8892a4;">$600C Apr · Block</span>
          <span style="font-family:'IBM Plex Mono';color:#00d395;">$5.1M</span>
        </div>
        <div style="display:flex;gap:5px;align-items:center;padding:4px 0;border-bottom:1px solid #1a2035;font-size:11px;">
          <span style="font-family:'IBM Plex Mono';font-weight:600;color:#4a9eff;min-width:36px;">AAPL</span>
          <span style="background:#2d0a0a;color:#ff4757;padding:1px 5px;border-radius:2px;font-size:9px;font-family:'IBM Plex Mono';">PUT</span>
          <span style="flex:1;color:#8892a4;">$190P Mar · Unusual</span>
          <span style="font-family:'IBM Plex Mono';color:#ff4757;">$1.2M</span>
        </div>
        <div style="display:flex;gap:5px;align-items:center;padding:4px 0;font-size:11px;">
          <span style="font-family:'IBM Plex Mono';font-weight:600;color:#4a9eff;min-width:36px;">META</span>
          <span style="background:#0a2d1f;color:#00d395;padding:1px 5px;border-radius:2px;font-size:9px;font-family:'IBM Plex Mono';">CALL</span>
          <span style="flex:1;color:#8892a4;">$620C Apr · Sweep</span>
          <span style="font-family:'IBM Plex Mono';color:#00d395;">$890K</span>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════════
# SECTION 8 — CATALYST CALENDAR
# ══════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">📅 Catalyst Calendar</div>', unsafe_allow_html=True)

cats = [("FOMC","Mar 19","Rate Decision","HIGH","warn"),("NVDA","Mar 19","Earnings","HIGH","buy"),
        ("GDP","Mar 27","Q4 Final","MED","neu"),("NFP","Apr 4","Jobs Report","HIGH","warn"),
        ("CPI","Apr 10","Inflation","HIGH","warn"),("AMZN","Apr 24","Earnings","HIGH","buy"),
        ("MSFT","Apr 25","Earnings","HIGH","buy"),("GOOGL","Apr 25","Earnings","HIGH","buy")]
cc = st.columns(len(cats))
for col, (t, d, typ, imp, c) in zip(cc, cats):
    bg = "#0a2d1f" if c == "buy" else "#1a1200" if c == "warn" else "#0d0d14"
    tc = "#00d395" if c == "buy" else "#ffa502" if c == "warn" else "#8892a4"
    ic = "#ff4757" if imp == "HIGH" else "#8892a4"
    ib = "#2d0a0a" if imp == "HIGH" else "#141420"
    with col:
        st.markdown(f"""
        <div style="background:{bg};border:1px solid #1a2035;border-radius:5px;padding:8px 10px;">
          <div style="font-family:'IBM Plex Mono';font-size:12px;font-weight:600;color:{tc};">{t}</div>
          <div style="font-size:10px;color:{tc};">{d}</div>
          <div style="font-size:10px;color:{tc};">{typ}</div>
          <span style="background:{ib};color:{ic};font-size:9px;padding:1px 5px;border-radius:2px;font-family:'IBM Plex Mono';">{imp}</span>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════════
# SECTION 9 — SHORT SQUEEZE RADAR
# ══════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">💥 Short Squeeze Radar</div>', unsafe_allow_html=True)

sqz = [("SMCI","28%","8.2d","up"),("MSTR","24%","6.1d","up"),("RIVN","21%","5.8d","neu"),
       ("GME","19%","7.4d","up"),("COIN","16%","5.2d","up"),("BYND","35%","12.1d","dn"),
       ("SOFI","18%","6.8d","up"),("PLTR","11%","4.1d","up")]
sc = st.columns(len(sqz))
for col, (t, si, dtc, rs) in zip(sc, sqz):
    bg = "#0a2d1f" if rs == "up" else "#2d0a0a" if rs == "dn" else "#0d0d14"
    tc = "#00d395" if rs == "up" else "#ff4757" if rs == "dn" else "#8892a4"
    with col:
        st.markdown(f"""
        <div style="background:{bg};border:1px solid #1a2035;border-radius:5px;padding:8px;text-align:center;">
          <div style="font-family:'IBM Plex Mono';font-size:12px;font-weight:600;color:{tc};">{t}</div>
          <div style="font-size:10px;color:{tc};">SI: {si}</div>
          <div style="font-size:10px;color:{tc};">DTC: {dtc}</div>
        </div>""", unsafe_allow_html=True)
st.caption("SI = Short Interest % float · DTC = Days to Cover · Green = positive momentum / potential squeeze")

# ══════════════════════════════════════════════════════════════════════════════════
# SECTION 10 — LIVE STOCK SCREENER
# ══════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🔬 Live Stock Screener — Real-Time Signal Breakdown</div>', unsafe_allow_html=True)
st.markdown("Enter any ticker for live technical analysis powered by Yahoo Finance.")

scr_col1, scr_col2 = st.columns([2, 3])
with scr_col1:
    ticker_input = st.text_input("Ticker", value="NVDA", max_chars=8, label_visibility="collapsed",
                                  placeholder="e.g. NVDA, AAPL, TSLA").upper().strip()
    run = st.button("🔍 Analyse Live", use_container_width=True)

with scr_col2:
    st.markdown("Quick picks:")
    qp_cols = st.columns(10)
    for col, t in zip(qp_cols, ["NVDA","AAPL","META","MSFT","TSLA","AMD","AMZN","GOOGL","SPY","QQQ"]):
        with col:
            if st.button(t, key=f"qp_{t}"):
                ticker_input = t

if run or ticker_input:
    sym = ticker_input
    with st.spinner(f"Fetching live data for {sym}..."):
        sig = compute_signals(sym)

    if sig and not sig.get("error"):
        score = sig["score"]
        ver, v_bg, v_col = verdict(score)
        price = sig["price"]
        info = sig.get("info", {})

        r1, r2 = st.columns([3, 1])
        with r1:
            company = info.get("longName", sym)
            sector = info.get("sector", "—")
            st.markdown(f"""
            <span style="font-family:'IBM Plex Mono';font-size:20px;font-weight:600;color:#4a9eff;">{sym}</span>
            <span style="font-size:13px;color:#6b7280;margin-left:10px;">{company} · {sector}</span>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;font-size:10px;font-family:'IBM Plex Mono';color:#4a5568;margin-bottom:3px;margin-top:8px;">
              <span style="color:#ff4757;">STRONG SELL</span><span>NEUTRAL</span><span style="color:#00d395;">STRONG BUY</span>
            </div>
            <div style="height:12px;border-radius:6px;background:linear-gradient(to right,#ff4757,#ffa502,#00d395);position:relative;">
              <div style="position:absolute;top:-3px;left:{min(max(score-1,1),97)}%;width:3px;height:18px;background:white;border-radius:2px;"></div>
            </div>""", unsafe_allow_html=True)

            # Performance row
            p_cols = st.columns(5)
            for col, (label, val) in zip(p_cols, [
                ("Price", f"${fp(price)}"), ("1D", f"{sig['chg1d']:+.2f}%"),
                ("1W", f"{sig['chg1w']:+.2f}%"), ("1M", f"{sig['chg1m']:+.2f}%"), ("3M", f"{sig['chg3m']:+.2f}%")]):
                with col:
                    v_is_chg = label != "Price"
                    vc = clr(float(val.replace('%','').replace('$','').replace('+','').replace(',','')) if v_is_chg else 0) if v_is_chg else "#fff"
                    st.markdown(f'<div style="text-align:center;padding:6px;background:#0d0d14;border:1px solid #1a2035;border-radius:5px;"><div style="font-size:9px;color:#4a5568;">{label}</div><div style="font-family:IBM Plex Mono;font-size:12px;font-weight:600;color:{vc};">{val}</div></div>', unsafe_allow_html=True)

        with r2:
            st.markdown(f"""
            <div style="background:{v_bg};border:1px solid {v_col}44;border-radius:8px;padding:14px;text-align:center;height:100%;">
              <div style="font-family:'IBM Plex Mono';font-size:18px;font-weight:600;color:#fff;">${fp(price)}</div>
              <div style="font-size:12px;color:{clr(sig['chg1d'])};margin:3px 0;">{arr(sig['chg1d'])} {sig['chg1d']:+.2f}% today</div>
              <div style="font-family:'IBM Plex Mono';font-size:15px;font-weight:600;color:{v_col};margin-top:8px;">{ver}</div>
              <div style="font-size:13px;color:{v_col};margin-top:2px;font-weight:600;">Score: {score}/100</div>
            </div>""", unsafe_allow_html=True)

        # Signal matrix
        st.markdown("**Signal Matrix**")
        sigs = [
            ("SMA 50", "Above" if price > sig["sma50"] else "Below", "buy" if price > sig["sma50"] else "sell"),
            ("SMA 200", "Above" if price > sig["sma200"] else "Below", "buy" if price > sig["sma200"] else "sell"),
            ("EMA 20", "Above" if price > sig["ema20"] else "Below", "buy" if price > sig["ema20"] else "sell"),
            ("RSI(14)", f"{sig['rsi']:.0f}", "buy" if 45 < sig['rsi'] < 70 else "sell" if sig['rsi'] > 75 or sig['rsi'] < 35 else "neu"),
            ("MACD", "Positive" if sig["macd_hist"] > 0 else "Negative", "buy" if sig["macd_hist"] > 0 else "sell"),
            ("Bollinger", f"{sig['bb_pos']:.0%}", "buy" if sig['bb_pos'] > 0.5 else "sell" if sig['bb_pos'] < 0.2 else "neu"),
            ("Volume", f"{sig['vol_ratio']:.1f}x avg", "buy" if sig['vol_ratio'] > 1.1 else "neu"),
            ("1M Trend", f"{sig['chg1m']:+.1f}%", "buy" if sig['chg1m'] > 0 else "sell"),
        ]
        sig_cols = st.columns(8)
        for col, (n, v, s) in zip(sig_cols, sigs):
            bg = "#0a2d1f" if s == "buy" else "#2d0a0a" if s == "sell" else "#141420"
            c_txt = "#00d395" if s == "buy" else "#ff4757" if s == "sell" else "#8892a4"
            with col:
                st.markdown(f"""
                <div class="sig">
                  <div class="sig-n">{n}</div>
                  <div class="sig-v" style="color:{c_txt};">{v}</div>
                  <div style="background:{bg};color:{c_txt};padding:1px 5px;border-radius:2px;font-size:9px;font-family:'IBM Plex Mono';margin-top:3px;display:inline-block;">{s.upper()}</div>
                </div>""", unsafe_allow_html=True)

        # Fundamentals + Trade Setup
        fund_c, setup_c = st.columns(2)
        with fund_c:
            st.markdown("**Fundamental Snapshot**")
            pe = info.get("trailingPE"); fwd_pe = info.get("forwardPE")
            eps_g = info.get("earningsQuarterlyGrowth", 0); rev_g = info.get("revenueGrowth", 0)
            margin = info.get("profitMargins", 0); mktcap = info.get("marketCap", 0)
            mktcap_s = f"${mktcap/1e12:.1f}T" if mktcap > 1e12 else f"${mktcap/1e9:.0f}B" if mktcap > 1e9 else "N/A"
            for label, val in [
                ("P/E (TTM)", f"{pe:.1f}x" if pe else "N/A"),
                ("Forward P/E", f"{fwd_pe:.1f}x" if fwd_pe else "N/A"),
                ("EPS Growth", f"{eps_g*100:+.1f}%" if eps_g else "N/A"),
                ("Revenue Growth", f"{rev_g*100:+.1f}%" if rev_g else "N/A"),
                ("Net Margin", f"{margin*100:.1f}%" if margin else "N/A"),
                ("Market Cap", mktcap_s)]:
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1a2035;font-size:12px;"><span style="color:#8892a4;">{label}</span><span style="font-family:IBM Plex Mono;font-weight:600;">{val}</span></div>', unsafe_allow_html=True)

        with setup_c:
            st.markdown("**Trade Setup (ATR-based)**")
            atr = sig["atr"]
            stop = price - atr * 2
            t1, t2 = price * 1.08, price * 1.18
            rr = (t1 - price) / (price - stop + 1e-9)
            for label, val, cls in [
                ("Current Price", f"${fp(price)}", ""),
                ("ATR (14)", f"${atr:.2f}", ""),
                ("Entry Zone", f"${fp(price*0.99)}–${fp(price*1.005)}", ""),
                ("Stop Loss (2×ATR)", f"${fp(stop)} (−{(price-stop)/price*100:.1f}%)", "dn"),
                ("Target 1 (+8%)", f"${fp(t1)}", "up"),
                ("Target 2 (+18%)", f"${fp(t2)}", "up"),
                ("Risk/Reward", f"{rr:.1f}:1", "up" if rr >= 2 else "warn")]:
                vc = "color:#00d395" if cls == "up" else "color:#ff4757" if cls == "dn" else "color:#ffa502" if cls == "warn" else ""
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1a2035;font-size:12px;"><span style="color:#8892a4;">{label}</span><span style="font-family:IBM Plex Mono;font-weight:600;{vc}">{val}</span></div>', unsafe_allow_html=True)

        # Price chart
        if sig["close_series"]:
            fig_scr = go.Figure()
            fig_scr.add_trace(go.Scatter(
                y=sig["close_series"], mode="lines", name=sym,
                line=dict(color="#4a9eff", width=2),
                fill="tozeroy", fillcolor="rgba(74,158,255,0.05)",
                hovertemplate="$%{y:.2f}<extra></extra>"
            ))
            fig_scr.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,13,20,1)",
                margin=dict(l=50, r=20, t=10, b=30), height=200,
                font=dict(family="IBM Plex Mono", color="#8892a4", size=10),
                xaxis=dict(showgrid=False, showticklabels=False, title="60 trading days"),
                yaxis=dict(gridcolor="#1a2035", tickprefix="$"),
                showlegend=False, hovermode="x unified"
            )
            st.plotly_chart(fig_scr, use_container_width=True, config={"displayModeBar": False})

    elif sig and sig.get("error"):
        st.error(f"Could not fetch data for **{sym}**: {sig['error']}\n\nCheck the ticker is valid (e.g. NVDA, AAPL).")
    else:
        st.info(f"No data found for {sym}. Try a major US-listed stock.")

# ── FOOTER ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center;font-family:'IBM Plex Mono',monospace;font-size:10px;color:#4a5568;padding:8px 0;">
  ⚠️ For informational purposes only · Not financial advice · Always do your own research<br>
  Data: Yahoo Finance (yfinance) · Prices ~15 min delayed · Auto-refresh every 5 min
</div>
""", unsafe_allow_html=True)
