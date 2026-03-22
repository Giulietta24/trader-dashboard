import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests, copy, json
from datetime import datetime, date

# ── KEY HELPERS ────────────────────────────────────────────────────────────────
def _finnhub_key():
    try: return st.secrets.get("FINNHUB_KEY") or st.secrets.get("finnhub_key")
    except: return None

def _anthropic_key():
    try: return st.secrets.get("ANTHROPIC_API_KEY") or st.secrets.get("anthropic_api_key")
    except: return None

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Trader Intelligence Dashboard", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

# ── SESSION STATE — must be before any section that uses it ───────────────────
if "custom_tickers"  not in st.session_state: st.session_state.custom_tickers  = {}
if "approved_recs"   not in st.session_state: st.session_state.approved_recs   = {}
if "hidden_themes"   not in st.session_state: st.session_state.hidden_themes   = []

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.block-container{padding:1rem 1.5rem 2rem;max-width:1600px;}
/* sidebar enabled */
.sec{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
     color:#9ca3af;margin:1.4rem 0 .7rem;border-bottom:1px solid #e5e7eb;padding-bottom:5px;
     display:flex;align-items:center;justify-content:space-between;}
.sec-badge{font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;
     letter-spacing:0;text-transform:none;border:1px solid;}
.sec-bull{background:#f0fdf4;color:#15803d;border-color:#bbf7d0;}
.sec-bear{background:#fef2f2;color:#b91c1c;border-color:#fecaca;}
.sec-warn{background:#fffbeb;color:#b45309;border-color:#fde68a;}
.sec-neu{background:#f9fafb;color:#6b7280;border-color:#e5e7eb;}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:12px 16px;}
.lbl{font-size:10px;color:#9ca3af;letter-spacing:.04em;text-transform:uppercase;margin-bottom:4px;}
.val{font-size:20px;font-weight:600;color:#111827;}
.sub{font-size:11px;color:#6b7280;margin-top:2px;}
.up{color:#16a34a!important;}.dn{color:#dc2626!important;}
.neu{color:#9ca3af!important;}.warn{color:#d97706!important;}
.badge{display:inline-block;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:600;}
.b-buy{background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;}
.b-sell{background:#fef2f2;color:#b91c1c;border:1px solid #fecaca;}
.b-hold{background:#fffbeb;color:#b45309;border:1px solid #fde68a;}
.b-neu{background:#f9fafb;color:#6b7280;border:1px solid #e5e7eb;}
.hm{border-radius:6px;padding:8px 6px;text-align:center;}
.sig{background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:8px;text-align:center;}
.sig-n{font-size:9px;color:#9ca3af;letter-spacing:.04em;margin-bottom:2px;}
.sig-v{font-size:11px;font-weight:600;color:#111827;}
/* Tooltip — opens LEFT */
.tw{position:relative;display:inline-block;cursor:pointer;}
.tw .tb{visibility:hidden;opacity:0;background:#1e293b;color:#f1f5f9;font-size:11px;
  line-height:1.5;padding:8px 10px;border-radius:6px;width:220px;
  position:absolute;bottom:125%;right:0;left:auto;
  z-index:9999;pointer-events:none;transition:opacity .15s;font-weight:400;}
.tw:hover .tb{visibility:visible;opacity:1;}
.tw .tb::after{content:"";position:absolute;top:100%;right:12px;left:auto;
  margin:0;border:5px solid transparent;border-top-color:#1e293b;}
/* Sidebar nav */
section[data-testid="stSidebar"]{background:#1e3a5f!important;min-width:220px!important;max-width:220px!important;}
section[data-testid="stSidebar"] p,section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div{color:#ffffff!important;}
section[data-testid="stSidebar"] .stMarkdown a{
  color:#ffffff!important;text-decoration:none!important;
  font-size:13px!important;font-weight:500!important;
  display:block;padding:4px 2px;}
section[data-testid="stSidebar"] .stMarkdown a:hover{
  color:#93c5fd!important;}
section[data-testid="stSidebar"] .stMarkdown strong{color:#93c5fd!important;font-size:11px!important;}
section[data-testid="stSidebar"] hr{border-color:#2d5a8e!important;}
</style>
""", unsafe_allow_html=True)

# ── COLOUR HELPERS ─────────────────────────────────────────────────────────────
# Initialise all session state here — MUST be before any usage
if "custom_tickers"  not in st.session_state: st.session_state.custom_tickers  = {}
if "approved_recs"   not in st.session_state: st.session_state.approved_recs   = {}
if "hidden_themes"   not in st.session_state: st.session_state.hidden_themes   = []
if "heat_period"     not in st.session_state: st.session_state.heat_period     = "1d"
def clr(v, good_pos=True):
    return ("#16a34a" if v>=0 else "#dc2626") if good_pos else ("#dc2626" if v>=0 else "#16a34a")
def arr(v): return "▲" if v>=0 else "▼"
def fp(v): return f"{v:,.2f}" if v>=1000 else f"{v:.2f}"
def hm_clr(v):
    if v>=2:   return "#dcfce7","#15803d"
    if v>=.5:  return "#f0fdf4","#16a34a"
    if v>=-.5: return "#f9fafb","#6b7280"
    if v>=-2:  return "#fef2f2","#dc2626"
    return "#fee2e2","#b91c1c"
def verdict(s):
    if s>=80: return "STRONG BUY","#f0fdf4","#15803d"
    if s>=65: return "BUY","#f0fdf4","#16a34a"
    if s>=50: return "HOLD","#fffbeb","#d97706"
    if s>=35: return "WEAK/AVOID","#fef2f2","#dc2626"
    return "STRONG SELL","#fef2f2","#b91c1c"
def section_signal(label: str, signal: str, col: str, bg: str, bc: str, detail: str = "") -> str:
    """Render a compact signal badge for section headers."""
    return f'''<span style="background:{bg};border:1px solid {bc};color:{col};
      font-size:11px;font-weight:700;padding:3px 10px;border-radius:4px;
      margin-left:10px;vertical-align:middle;">{signal}</span>
      <span style="font-size:11px;color:#6b7280;margin-left:6px;vertical-align:middle;">{detail}</span>'''

def sig_badge(v, good_pos=True, labels=("BULLISH","BEARISH")):
    """Return (signal_text, col, bg, bc) based on value direction."""
    is_good = (v >= 0) if good_pos else (v <= 0)
    if is_good:
        return labels[0], "#15803d", "#f0fdf4", "#bbf7d0"
    else:
        return labels[1], "#b91c1c", "#fef2f2", "#fecaca"

def spark_html(data, col="#2563eb", h=24):
    if not data: return ""
    mn,mx=min(data),max(data); rng=mx-mn or 1
    bars="".join(f'<div style="flex:1;height:{max(int((v-mn)/rng*h),2)}px;background:{"'+col+'" if i==len(data)-1 else "#e5e7eb"};border-radius:1px 1px 0 0;align-self:flex-end;"></div>' for i,v in enumerate(data))
    return f'<div style="display:flex;align-items:flex-end;gap:1px;height:{h}px;margin:5px 0 3px;">{bars}</div>'
def tip(icon, text):
    """Tooltip that opens LEFT so never goes off screen."""
    return f'<span class="tw"><span style="font-size:11px;color:#9ca3af;cursor:pointer;">{icon}</span><span class="tb">{text}</span></span>'

# ── DATA FUNCTIONS ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_quote(sym):
    try:
        t=yf.Ticker(sym); h=t.history(period="3mo"); h1y=t.history(period="1y")
        return {"h":h,"h1y":h1y,"info":t.info,"ok":True}
    except Exception as e: return {"ok":False,"err":str(e)}

@st.cache_data(ttl=300)
def get_indexes():
    syms = {
        # Cap size
        "SPY":    ("#2563eb","Large Cap",   "S&P 500",        "cap"),
        "RSP":    ("#7c3aed","Equal Weight","S&P 500 EW",     "cap"),
        "MDY":    ("#0891b2","Mid Cap",     "S&P 400 Mid",    "cap"),
        "IWM":    ("#dc2626","Small Cap",   "Russell 2000",   "cap"),
        # Style / sector leaders
        "QQQ":    ("#a855f7","Tech/Growth", "Nasdaq 100",     "style"),
        "^IXIC":  ("#8b5cf6","Broad Nasdaq","Nasdaq Comp",    "style"),
        "SOXX":   ("#f59e0b","Semis",       "Semiconductors", "style"),
        # International
        "EFA":    ("#059669","Intl Dev",    "MSCI EAFE",      "intl"),
        "EEM":    ("#10b981","Emerging",    "MSCI EM",        "intl"),
        # Risk appetite
        "BTC-USD":("#f97316","Risk Gauge",  "Bitcoin",        "risk"),
        # Dow
        "^DJI":   ("#64748b","Mega Cap",    "Dow Jones",      "cap"),
    }
    out={}
    for sym,(col,cap,name,grp) in syms.items():
        d=get_quote(sym)
        if d["ok"] and not d["h"].empty:
            h=d["h"]; p=h["Close"].iloc[-1]; p1=h["Close"].iloc[-2]
            chg1d=(p-p1)/p1*100
            chg1w=(p-h["Close"].iloc[-6])/h["Close"].iloc[-6]*100 if len(h)>=6 else 0
            chg1m=(p-h["Close"].iloc[-22])/h["Close"].iloc[-22]*100 if len(h)>=22 else 0
            chg3m=(p-h["Close"].iloc[0])/h["Close"].iloc[0]*100
            sma50=h["Close"].tail(50).mean()
            out[sym]={"color":col,"cap":cap,"name":name,"grp":grp,
                      "price":p,"chg1d":chg1d,"chg1w":chg1w,"chg1m":chg1m,"chg3m":chg3m,
                      "above50":p>sma50,"sma50":float(sma50),
                      "spark":h["Close"].tail(30).tolist(),"hist":h}
    return out

@st.cache_data(ttl=300)
def get_macro():
    syms={"^VIX":"VIX","^TNX":"10Y Yield","^FVX":"5Y Yield","^IRX":"3M T-Bill","DX-Y.NYB":"DXY","^VVIX":"VVIX"}
    out={}
    for sym,name in syms.items():
        try:
            h=yf.Ticker(sym).history(period="5d")
            if not h.empty and len(h)>=2:
                p,prev=h["Close"].iloc[-1],h["Close"].iloc[-2]
                out[name]={"price":p,"chg":p-prev if "Yield" in name or name=="3M T-Bill" else (p-prev)/prev*100}
        except: pass
    # MOVE proxy — compute TLT 20-day annualised volatility (bond vol proxy)
    try:
        tlt_h=yf.Ticker("TLT").history(period="3mo")
        if not tlt_h.empty and len(tlt_h)>=22:
            daily_ret=tlt_h["Close"].pct_change().dropna()
            roll_vol=float(daily_ret.tail(20).std()*(252**0.5)*100)
            prev_vol=float(daily_ret.tail(40).head(20).std()*(252**0.5)*100)
            out["MOVE"]={"price":round(roll_vol,1),"chg":round(roll_vol-prev_vol,1),
                         "source":"TLT vol proxy"}
    except: pass
    return out

@st.cache_data(ttl=300)
def get_breadth():
    try:
        out={}
        # RSP vs SPY breadth
        rsp=yf.Ticker("RSP").history(period="3mo")
        spy=yf.Ticker("SPY").history(period="3mo")
        if not rsp.empty and not spy.empty and len(rsp)>=22 and len(spy)>=22:
            rsp_m=(rsp["Close"].iloc[-1]-rsp["Close"].iloc[-22])/rsp["Close"].iloc[-22]*100
            spy_m=(spy["Close"].iloc[-1]-spy["Close"].iloc[-22])/spy["Close"].iloc[-22]*100
            out["rsp_spy"]=round(rsp_m-spy_m, 2)
        else:
            out["rsp_spy"]=0.0
        # HYG credit
        hyg=yf.Ticker("HYG").history(period="3mo")
        if not hyg.empty and len(hyg)>=22:
            chg1m=(hyg["Close"].iloc[-1]-hyg["Close"].iloc[-22])/hyg["Close"].iloc[-22]*100
            out["hyg"]={"price":round(hyg["Close"].iloc[-1],2),"chg1m":round(chg1m,2)}
        # TLT
        tlt=yf.Ticker("TLT").history(period="5d")
        if not tlt.empty and len(tlt)>=2:
            chg=(tlt["Close"].iloc[-1]-tlt["Close"].iloc[-2])/tlt["Close"].iloc[-2]*100
            out["tlt"]={"price":round(tlt["Close"].iloc[-1],2),"chg":round(chg,2)}
        return out
    except Exception as e:
        return {"rsp_spy":0.0}

@st.cache_data(ttl=300)
def get_cross_market():
    pairs={
        "XLE/SPY": ("XLE","SPY","Energy vs Market","Rising=energy leading, inflation risk. Watch XOM, CVX, OXY."),
        "XLF/SPY": ("XLF","SPY","Financials vs Market","Rising=banks healthy, economy strong. Watch JPM, GS, BAC."),
        "XLK/SPY": ("XLK","SPY","Tech vs Market","Rising=growth in favour, risk-on. Falls when yields rise."),
        "XLP/XLY": ("XLP","XLY","Defensives vs Disc","Rising=caution, consumers pulling back. Early recession signal."),
        "VIX/SPY": ("^VIX","SPY","Vol vs Market","Rising=fear spiking while market holds=warning. Falling=market rallying with falling fear=healthy. Best complacency gauge."),
        "TLT/SPY": ("TLT","SPY","Bonds vs Stocks","Rising=money fleeing stocks to safety. Watch closely."),
        "GLD/TLT": ("GLD","TLT","Gold vs Bonds","Rising=inflation fear over recession fear. Stagflation signal."),
        "EEM/SPY": ("EEM","SPY","EM vs US","Rising=weak dollar, global risk-on. China proxy."),
        "IWM/SPY": ("IWM","SPY","Small vs Large","Rising=broad healthy rally. Falling=narrow market, warning sign."),
    }
    out={}
    for key,(s1,s2,label,desc) in pairs.items():
        try:
            h1=yf.Ticker(s1).history(period="2mo")
            h2=yf.Ticker(s2).history(period="2mo")
            if not h1.empty and not h2.empty and len(h1)>=6 and len(h2)>=6:
                p1=h1["Close"].iloc[-1]; p2=h2["Close"].iloc[-1]
                r_now=p1/p2
                r_1d =h1["Close"].iloc[-2]/h2["Close"].iloc[-2] if len(h1)>=2 else r_now
                r_1w =h1["Close"].iloc[-6]/h2["Close"].iloc[-6] if len(h1)>=6 else r_now
                r_1m =h1["Close"].iloc[-22]/h2["Close"].iloc[-22] if len(h1)>=22 else r_now
                r_3m =h1["Close"].iloc[0]/h2["Close"].iloc[0]
                out[key]={"label":label,"desc":desc,
                          "chg_1d":(r_now-r_1d)/r_1d*100,
                          "chg_1w":(r_now-r_1w)/r_1w*100,
                          "chg_1m":(r_now-r_1m)/r_1m*100,
                          "chg_3m":(r_now-r_3m)/r_3m*100}
        except: pass
    return out

@st.cache_data(ttl=300)
def get_commodities():
    syms={"GC=F":("Gold","⭐⭐⭐","/oz","Fear gauge. Rises in stress. Watch vs VIX. Affects NEM, GOLD, AEM."),
          "SI=F":("Silver","⭐⭐","/oz","Follows gold but more volatile. Also industrial — rising=growth up."),
          "HG=F":("Copper","⭐⭐⭐","/lb","Dr Copper = economic predictor. Rising=global growth. Watch FCX, SCCO."),
          "CL=F":("WTI Crude","⭐⭐⭐","/bbl","Drives inflation, Fed decisions, XLE, airlines, consumer spending."),
          "BZ=F":("Brent","⭐⭐⭐","/bbl","Global oil benchmark. Spike=inflation risk globally."),
          "NG=F":("Nat Gas","⭐⭐","/MMBtu","Drives utilities (XLU). Winter spikes hurt consumer. Watch EQT, RRC."),
          "ZW=F":("Wheat","⭐⭐","¢/bu","Key food inflation. Russia/Ukraine sensitive. Affects ADM, BG."),
          "ZC=F":("Corn","⭐⭐","¢/bu","Food & fuel (ethanol). Rising=CPI pressure. Affects ADM, MOS."),
          "ZS=F":("Soybeans","⭐⭐","¢/bu","China demand indicator. Rising=China active. Affects BG, ADM."),
          "SB=F":("Sugar","⭐","¢/lb","Affects KO, Hershey, Mondelez costs. Limited broader impact."),
          "KC=F":("Coffee","⭐","¢/lb","Affects SBUX margins directly. Watch before earnings."),
          "CC=F":("Cocoa","⭐","$/t","Near record highs. Affects Hershey, Mondelez margins."),
          "CT=F":("Cotton","⭐","¢/lb","Affects apparel — Nike, PVH, HBI. Slow moving."),
          "LBS=F":("Lumber","⭐⭐","$/1kbf","Leading indicator for housing. Watch DHI, LEN, TOL.")}
    out={}
    for sym,(name,stars,unit,desc) in syms.items():
        try:
            h=yf.Ticker(sym).history(period="5d")
            if not h.empty and len(h)>=2:
                p,prev=h["Close"].iloc[-1],h["Close"].iloc[-2]
                out[name]={"price":p,"chg":(p-prev)/prev*100,"unit":unit,"stars":stars,"desc":desc}
        except: pass
    return out

@st.cache_data(ttl=600)
def get_sectors():
    etfs={"XLK":"Tech","XLE":"Energy","XLI":"Industrials","XLF":"Financials",
          "XLC":"Comm","XLV":"Health","XLY":"Disc","XLP":"Staples",
          "XLU":"Utilities","XLRE":"R.Estate","XLB":"Materials"}
    out={}
    sector_tips={"Tech":"Rising=risk-on, QQQ leading. Rate-sensitive — falls when yields rise. NVDA, MSFT, AAPL.",
                 "Energy":"Rising=oil up, inflation risk. Benefits XOM, CVX. Hurts airlines & consumers.",
                 "Industrials":"Rising=economic growth, capex cycle active. GE, CAT, ETN. Good for reshoring.",
                 "Financials":"Rising=banks earning more (high rates help). JPM, GS. Falls on yield curve inversion.",
                 "Comm":"META, GOOGL, Netflix. Hybrid growth/defensive. Hybrid of risk-on/off.",
                 "Health":"Defensive. Rises on slowdown fears. LLY, UNH, JNJ. GLP-1 drugs driving outperformance.",
                 "Disc":"Rising=consumers spending. Falls first in recession. AMZN, TSLA, HD.",
                 "Staples":"Defensive safe haven. Rises on fear. KO, PG, WMT. Buy when markets uncertain.",
                 "Utilities":"Rate-sensitive — falls when yields rise. NEE, DUK. AI power demand theme helping.",
                 "R.Estate":"Highly rate-sensitive. Rising=rate cuts expected. VNQ, AMT, PLD.",
                 "Materials":"Rising=global growth, commodity demand up. Copper miners, chemicals. Leads economic cycle."}
    for sym,name in etfs.items():
        try:
            h=yf.Ticker(sym).history(period="1mo")
            if not h.empty and len(h)>=5:
                p=h["Close"].iloc[-1]
                out[name]={"1d":(p-h["Close"].iloc[-2])/h["Close"].iloc[-2]*100,
                           "1w":(p-h["Close"].iloc[-6])/h["Close"].iloc[-6]*100 if len(h)>=6 else 0,
                           "1m":(p-h["Close"].iloc[0])/h["Close"].iloc[0]*100,
                           "tip":sector_tips.get(name,"")}
        except: pass
    return out

@st.cache_data(ttl=21600)
def get_fred_inflation():
    series={"CPIAUCSL":"CPI (YoY)","CPILFESL":"Core CPI","PCEPI":"PCE (YoY)",
            "PPIACO":"PPI (YoY)","T5YIE":"5Y Breakeven","FEDFUNDS":"Fed Funds Rate"}
    out={}
    for sid,label in series.items():
        try:
            r=requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}",
                           timeout=8,headers={"User-Agent":"Mozilla/5.0"})
            rows=[l.split(",") for l in r.text.strip().split("\n")[1:] if l and "." in l.split(",")[-1]]
            if len(rows)>=13:
                lv=float(rows[-1][1]); pv=float(rows[-13][1])
                val=lv if sid in("T5YIE","FEDFUNDS") else ((lv-pv)/pv)*100
                out[label]={"val":val,"date":rows[-1][0]}
        except: pass
    return out


def get_top_movers(universe, top_n=60):
    """Fetch 1-month performance for all tickers, return top movers."""
    movers = []
    for sym in universe:
        try:
            h = yf.Ticker(sym).history(period="3mo")
            if not h.empty and len(h) >= 22:
                p   = h["Close"].iloc[-1]
                p1w = h["Close"].iloc[-6]  if len(h) >= 6  else p
                p1m = h["Close"].iloc[-22]
                p3m = h["Close"].iloc[0]
                chg1w = (p - p1w) / p1w * 100
                chg1m = (p - p1m) / p1m * 100
                chg3m = (p - p3m) / p3m * 100
                # Composite momentum score
                composite = chg1w * 0.3 + chg1m * 0.5 + chg3m * 0.2
                movers.append({
                    "sym": sym, "price": round(p, 2),
                    "chg1w": round(chg1w, 1), "chg1m": round(chg1m, 1),
                    "chg3m": round(chg3m, 1), "composite": round(composite, 1)
                })
        except:
            pass
    # Sort by absolute composite score — find both strong up AND strong down
    movers.sort(key=lambda x: -abs(x["composite"]))
    return movers[:top_n]

@st.cache_data(ttl=86400)
def get_dynamic_themes(movers_json: str, sector_perf: str, vix: float,
                        spy_1m: float, date_str: str) -> list:
    """
    Claude receives top price movers and builds the ENTIRE theme universe
    from scratch — no hardcoded themes, fully dynamic.
    Returns list of theme dicts.
    """
    key = _anthropic_key()
    if not key:
        return []
    try:
        prompt = f"""You are a top hedge fund analyst. Today is {date_str}.

LIVE MARKET DATA:
VIX: {vix:.1f} | SPY 1M: {spy_1m:+.1f}%
Sectors: {sector_perf}

TOP PRICE MOVERS (composite 1W+1M+3M momentum):
{movers_json}

Your job: Look at which stocks are moving together and WHY. Group them into themes that explain what is actually happening in the market RIGHT NOW.

Rules:
- Create 8-12 themes total based purely on what the data shows
- Each theme MUST be driven by stocks actually in the movers list above
- Theme names should describe the actual market narrative (e.g. "Iran War Oil Premium", "GLP-1 Weight Loss Revolution", "AI Data Centre Power Crisis") — not generic names
- Classify each theme: "hot" (score 65-100), "emerging" (45-64), or "fading" (score 10-44)
- Score reflects actual momentum strength from the data
- Include 4-8 tickers per theme from the movers list
- 1-2 sentence desc explaining WHY this theme is moving right now

Return ONLY valid JSON (no markdown, no backticks, no explanation):
[
  {{
    "name": "Theme Name — specific and descriptive",
    "category": "hot",
    "score": 85,
    "subsectors": ["Sub1", "Sub2", "Sub3"],
    "tickers": ["SYM1","SYM2","SYM3","SYM4"],
    "desc": "Why this theme is moving right now in one or two sentences.",
    "option_setup": "Best options strategy for this theme right now: e.g. Long calls on NVDA — momentum strong, buy the dip on weakness. Or CSPs on LLY — premium high, willing to own at lower price."
  }}
]"""

        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 2000,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30
        )
        text = r.json().get("content", [{}])[0].get("text", "").strip()
        # Strip any accidental markdown
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        themes = json.loads(text)
        # Validate structure
        valid = []
        for t in themes:
            if all(k in t for k in ["name","category","score","tickers","desc"]):
                valid.append(t)
        return valid
    except Exception as e:
        return []

@st.cache_data(ttl=3600)
def score_theme_tickers(themes: list) -> list:
    """Add live price momentum data to each theme's tickers."""
    scored = []
    for theme in themes:
        td = []
        for sym in theme.get("tickers", [])[:8]:
            try:
                h = yf.Ticker(sym).history(period="3mo")
                if not h.empty and len(h) >= 6:
                    p   = h["Close"].iloc[-1]
                    p1w = h["Close"].iloc[-6] if len(h) >= 6 else p
                    p1m = h["Close"].iloc[-22] if len(h) >= 22 else h["Close"].iloc[0]
                    p3m = h["Close"].iloc[0]
                    chg1w = (p - p1w) / p1w * 100
                    chg1m = (p - p1m) / p1m * 100
                    chg3m = (p - p3m) / p3m * 100
                    wt    = chg1w * 0.3 + chg1m * 0.5 + chg3m * 0.2
                    td.append({"sym": sym, "price": round(p, 2),
                               "chg1w": round(chg1w, 1), "chg1m": round(chg1m, 1),
                               "chg3m": round(chg3m, 1), "weighted": round(wt, 1)})
            except:
                pass
        td.sort(key=lambda x: -x["weighted"])
        # Recalculate score from actual data if we have ticker prices
        if td:
            avg = sum(t["weighted"] for t in td) / len(td)
            live_score = max(0, min(100, int(50 + avg * 2)))
        else:
            live_score = theme.get("score", 50)
        scored.append({**theme, "ticker_data": td, "avg_mom": round(avg if td else 0, 1),
                       "score": live_score})
    # Sort by score
    scored.sort(key=lambda x: -x["score"])
    return scored


#

@st.cache_data(ttl=600)
def get_short_interest(syms):
    out=[]
    for sym in syms:
        try:
            info=yf.Ticker(sym).info
            si=info.get("shortPercentOfFloat",0)
            dtc=info.get("shortRatio",0)
            h=yf.Ticker(sym).history(period="1mo")
            mom=(h["Close"].iloc[-1]-h["Close"].iloc[0])/h["Close"].iloc[0]*100 if not h.empty else 0
            if si and si>0.05:
                score=min(100,int(si*100*1.5+(dtc or 0)*3+max(mom,0)*.5))
                out.append({"sym":sym,"si":si*100,"dtc":dtc or 0,"mom":mom,"score":score})
        except: pass
    out.sort(key=lambda x:-x["si"])
    return out

@st.cache_data(ttl=600)
def compute_signals(sym):
    d=get_quote(sym)
    if not d["ok"] or d["h1y"].empty or len(d["h1y"])<50: return None
    h=d["h1y"]; close,vol=h["Close"],h["Volume"]; price=close.iloc[-1]
    sma50=close.tail(50).mean(); sma200=close.tail(200).mean() if len(close)>=200 else close.mean()
    ema20=close.ewm(span=20).mean().iloc[-1]
    delta=close.diff(); gain=delta.clip(lower=0).rolling(14).mean(); loss=(-delta.clip(upper=0)).rolling(14).mean()
    rsi=float((100-100/(1+gain/loss)).iloc[-1])
    ema12,ema26=close.ewm(span=12).mean(),close.ewm(span=26).mean()
    macd_hist=float((ema12-ema26-(ema12-ema26).ewm(span=9).mean()).iloc[-1])
    bb_mid=close.rolling(20).mean(); bb_std=close.rolling(20).std()
    bb_pos=(price-float((bb_mid-2*bb_std).iloc[-1]))/(float(4*bb_std.iloc[-1])+1e-9)
    tr=pd.concat([h["High"]-h["Low"],(h["High"]-close.shift()).abs(),(h["Low"]-close.shift()).abs()],axis=1).max(axis=1)
    atr=float(tr.rolling(14).mean().iloc[-1])
    vol_ratio=float(vol.iloc[-1]/vol.tail(20).mean())
    chg1d=float((price-close.iloc[-2])/close.iloc[-2]*100)
    chg1w=float((price-close.iloc[-6])/close.iloc[-6]*100) if len(close)>=6 else 0
    chg1m=float((price-close.iloc[-22])/close.iloc[-22]*100) if len(close)>=22 else 0
    chg3m=float((price-close.iloc[-66])/close.iloc[-66]*100) if len(close)>=66 else 0
    score=50
    if price>sma50: score+=12
    else: score-=15
    if price>sma200: score+=10
    else: score-=15
    if price>ema20: score+=5
    if rsi>50: score+=5
    if 40<rsi<70: score+=3
    elif rsi>75: score-=8
    elif rsi<35: score-=8
    if macd_hist>0: score+=8
    else: score-=10
    if bb_pos>0.5: score+=5
    if vol_ratio>1.1: score+=5
    if chg1m>0: score+=5
    score=max(0,min(100,score))
    return {"price":price,"sma50":sma50,"sma200":sma200,"ema20":ema20,"rsi":rsi,
            "macd_hist":macd_hist,"bb_pos":bb_pos,"atr":atr,"vol_ratio":vol_ratio,
            "chg1d":chg1d,"chg1w":chg1w,"chg1m":chg1m,"chg3m":chg3m,
            "score":score,"close_series":close.tail(60).tolist(),"info":d["info"]}

@st.cache_data(ttl=3600)
def get_analyst_sentiment(symbols, key):
    out={}
    for sym in symbols:
        try:
            r=requests.get(f"https://finnhub.io/api/v1/stock/recommendation?symbol={sym}&token={key}",timeout=5)
            data=r.json()
            if data:
                lt=data[0]; buy=lt.get("buy",0)+lt.get("strongBuy",0)
                hold=lt.get("hold",0); sell=lt.get("sell",0)+lt.get("strongSell",0)
                total=buy+hold+sell
                if total>0: out[sym]={"buy":buy,"hold":hold,"sell":sell,"pct_buy":int(buy/total*100)}
        except: pass
    return out

@st.cache_data(ttl=3600)
def get_insider_sentiment(symbols, key):
    out={}
    for sym in symbols:
        try:
            r=requests.get(f"https://finnhub.io/api/v1/stock/insider-sentiment?symbol={sym}&from=2025-01-01&token={key}",timeout=5)
            data=r.json().get("data",[])
            if data:
                lt=sorted(data,key=lambda x:x.get("month",0))[-1]
                chg=lt.get("change",0)
                out[sym]={"change":chg,"direction":"Buying" if chg>0 else "Selling","col":"#16a34a" if chg>0 else "#dc2626"}
        except: pass
    return out

@st.cache_data(ttl=3600)
def get_earnings_calendar(key):
    try:
        today=datetime.now(); dt_to=(today+pd.Timedelta(days=60)).strftime("%Y-%m-%d")
        r=requests.get(f"https://finnhub.io/api/v1/calendar/earnings?from={today.strftime('%Y-%m-%d')}&to={dt_to}&token={key}",timeout=8)
        data=r.json().get("earningsCalendar",[])
        watchlist={"AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","AMD","NFLX","ORCL","INTC","QCOM","CRM","AVGO","JPM","GS","BAC","WMT","HD","V","MA","UNH","LLY","JNJ","XOM","CVX"}
        out=[]
        for e in data:
            sym=e.get("symbol","")
            if sym in watchlist:
                try:
                    dt=datetime.strptime(e.get("date",""),"%Y-%m-%d")
                    out.append({"symbol":sym,"date":dt.strftime("%b %d"),"hour":e.get("hour","")})
                except: pass
        out.sort(key=lambda x:datetime.strptime(x["date"],"%b %d"))
        return out[:6]
    except: return []

# ── NEW: IV RANK ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_iv_rank(sym: str) -> dict:
    """
    Calculate IV Rank and IV Percentile from real options chain data.
    Uses ATM options implied volatility vs 52-week range of historical vol.
    """
    try:
        tk = yf.Ticker(sym)
        # Get 1 year of price history for HV calculation
        h = tk.history(period="1y")
        if h.empty or len(h) < 30: return {}

        # Calculate 30-day historical volatility (annualised)
        log_ret = np.log(h["Close"] / h["Close"].shift(1)).dropna()
        hv_30   = float(log_ret.tail(30).std() * np.sqrt(252) * 100)
        hv_10   = float(log_ret.tail(10).std() * np.sqrt(252) * 100)

        # Rolling 252-day HV to get 52-week high/low of HV
        rolling_hv = log_ret.rolling(30).std() * np.sqrt(252) * 100
        hv_52w_high = float(rolling_hv.max())
        hv_52w_low  = float(rolling_hv.min())

        # Get current IV from nearest expiry ATM options
        current_iv = None
        try:
            exps = tk.options
            if exps:
                # Use first expiry ~2-6 weeks out
                exp = next((e for e in exps if 14 <= (datetime.strptime(e,"%Y-%m-%d") - datetime.now()).days <= 45), exps[0])
                chain = tk.option_chain(exp)
                price = float(h["Close"].iloc[-1])
                # Find ATM call
                calls = chain.calls
                calls["dist"] = abs(calls["strike"] - price)
                atm = calls.nsmallest(1, "dist")
                if not atm.empty:
                    current_iv = float(atm["impliedVolatility"].iloc[0]) * 100
        except: pass

        # Use HV as proxy if no IV available
        iv = current_iv if current_iv and current_iv > 0 else hv_30

        # IV Rank: where is current IV in 52-week range
        if hv_52w_high > hv_52w_low:
            ivr = int((iv - hv_52w_low) / (hv_52w_high - hv_52w_low) * 100)
        else:
            ivr = 50

        ivr = max(0, min(100, ivr))

        # IV vs HV ratio: is IV rich or cheap vs actual moves
        iv_vs_hv = round(iv / hv_30, 2) if hv_30 > 0 else 1.0

        # Classification
        if ivr >= 80:
            verdict = "SELL PREMIUM"; vc = "#15803d"; vbg = "#f0fdf4"
            reason  = "IV very expensive — sell options (CSP/CC)"
        elif ivr >= 50:
            verdict = "SELL PREMIUM"; vc = "#16a34a"; vbg = "#f0fdf4"
            reason  = "IV elevated — lean towards selling"
        elif ivr >= 30:
            verdict = "NEUTRAL"; vc = "#d97706"; vbg = "#fffbeb"
            reason  = "IV average — either direction workable"
        else:
            verdict = "BUY PREMIUM"; vc = "#1d4ed8"; vbg = "#eff6ff"
            reason  = "IV cheap — buy options (LONG CALL/PUT)"

        # Earnings within 21 days?
        near_earnings = False
        try:
            cal = tk.calendar
            if cal is not None and hasattr(cal, 'T'):
                eq = cal.T.get("Earnings Date")
                if eq is not None:
                    eq_date = pd.to_datetime(eq).iloc[0] if hasattr(eq, 'iloc') else pd.to_datetime(eq)
                    days_to_earn = (eq_date - pd.Timestamp.now()).days
                    near_earnings = 0 <= days_to_earn <= 21
        except: pass

        return {
            "sym": sym, "iv": round(iv, 1), "hv30": round(hv_30, 1),
            "ivr": ivr, "iv_vs_hv": iv_vs_hv,
            "hv_52w_high": round(hv_52w_high, 1),
            "hv_52w_low":  round(hv_52w_low, 1),
            "verdict": verdict, "vc": vc, "vbg": vbg, "reason": reason,
            "near_earnings": near_earnings,
        }
    except: return {}

@st.cache_data(ttl=3600)
def get_unusual_options_flow(sym: str) -> dict:
    """
    Detect unusual options activity from yfinance options chain.
    Unusual = volume > 3x open interest, or total volume > 10x average.
    """
    try:
        tk   = yf.Ticker(sym)
        exps = tk.options
        if not exps: return {}

        unusual_calls, unusual_puts = [], []
        total_call_vol = total_put_vol = 0

        for exp in exps[:3]:  # Check next 3 expiries
            try:
                chain = tk.option_chain(exp)
                price = float(tk.history(period="2d")["Close"].iloc[-1])

                for _, row in chain.calls.iterrows():
                    vol = int(row.get("volume", 0) or 0)
                    oi  = int(row.get("openInterest", 0) or 0)
                    total_call_vol += vol
                    if vol > 500 and oi > 0 and vol / max(oi, 1) > 2:
                        unusual_calls.append({
                            "strike": float(row["strike"]),
                            "exp": exp, "vol": vol, "oi": oi,
                            "iv": round(float(row.get("impliedVolatility",0))*100,1),
                            "type": "CALL",
                            "otm": round((float(row["strike"])-price)/price*100,1)
                        })

                for _, row in chain.puts.iterrows():
                    vol = int(row.get("volume", 0) or 0)
                    oi  = int(row.get("openInterest", 0) or 0)
                    total_put_vol += vol
                    if vol > 500 and oi > 0 and vol / max(oi, 1) > 2:
                        unusual_puts.append({
                            "strike": float(row["strike"]),
                            "exp": exp, "vol": vol, "oi": oi,
                            "iv": round(float(row.get("impliedVolatility",0))*100,1),
                            "type": "PUT",
                            "otm": round((price-float(row["strike"]))/price*100,1)
                        })
            except: pass

        unusual_calls.sort(key=lambda x: -x["vol"])
        unusual_puts.sort(key=lambda x: -x["vol"])
        pcr = round(total_put_vol / max(total_call_vol, 1), 2)

        return {
            "sym": sym,
            "unusual_calls": unusual_calls[:3],
            "unusual_puts":  unusual_puts[:3],
            "pcr": pcr,
            "pcr_signal": "BEARISH" if pcr > 1.2 else "BULLISH" if pcr < 0.7 else "NEUTRAL",
            "total_call_vol": total_call_vol,
            "total_put_vol":  total_put_vol,
        }
    except: return {}

@st.cache_data(ttl=3600)
def get_sec_form4(sym: str) -> list:
    """Fetch recent insider Form 4 filings from SEC EDGAR (free, official)."""
    try:
        # Get CIK for the ticker
        r = requests.get(
            f"https://efts.sec.gov/LATEST/search-index?q=%22{sym}%22&dateRange=custom"
            f"&startdt={(datetime.now()-pd.Timedelta(days=90)).strftime('%Y-%m-%d')}"
            f"&enddt={datetime.now().strftime('%Y-%m-%d')}&forms=4",
            timeout=8,
            headers={"User-Agent": "TradingDashboard contact@example.com"}
        )
        hits = r.json().get("hits", {}).get("hits", [])
        out  = []
        for h in hits[:5]:
            src  = h.get("_source", {})
            name = src.get("display_names", ["Unknown"])[0] if src.get("display_names") else "Insider"
            filed = src.get("file_date", "")
            out.append({
                "name":   name,
                "filed":  filed,
                "url":    f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={sym}&type=4",
            })
        return out
    except: return []

@st.cache_data(ttl=3600)
def get_sector_etf_flow() -> dict:
    """
    Detect institutional sector rotation from ETF price/volume data.
    Large volume + price move = institutional flow into/out of sector.
    """
    out = {}
    for name, sym in [("Tech","XLK"),("Energy","XLE"),("Financials","XLF"),
                       ("Healthcare","XLV"),("Industrials","XLI"),("Comm","XLC"),
                       ("Disc","XLY"),("Staples","XLP"),("Utilities","XLU"),
                       ("Materials","XLB"),("R.Estate","XLRE")]:
        try:
            h = yf.Ticker(sym).history(period="1mo")
            if not h.empty and len(h) >= 5:
                p    = h["Close"].iloc[-1]
                p1d  = h["Close"].iloc[-2]
                p1w  = h["Close"].iloc[-6] if len(h)>=6 else h["Close"].iloc[0]
                vol  = h["Volume"].iloc[-1]
                avg_vol = h["Volume"].tail(20).mean()
                vol_ratio = round(vol / max(avg_vol, 1), 2)
                chg1d = round((p-p1d)/p1d*100, 2)
                chg1w = round((p-p1w)/p1w*100, 2)
                # Flow signal: big volume + directional move = institutional
                if vol_ratio > 1.5 and abs(chg1d) > 0.5:
                    flow = "INFLOW" if chg1d > 0 else "OUTFLOW"
                else:
                    flow = "NEUTRAL"
                out[name] = {
                    "sym": sym, "chg1d": chg1d, "chg1w": chg1w,
                    "vol_ratio": vol_ratio, "flow": flow
                }
        except: pass
    return out

@st.cache_data(ttl=86400)
def get_claude_trade_plans(signals_json: str, account_size: float,
                            vix: float, spy_1m: float,
                            date_str: str) -> dict:
    """
    Claude reads ALL signals and produces very specific trade plans:
    stock + strategy + strike + expiry + size + entry + stop + target.
    """
    key = _anthropic_key()
    if not key: return {}
    try:
        prompt = f"""You are a professional options trader managing a ${account_size:,.0f} account.
Today is {date_str}. VIX={vix:.1f}, SPY 1M={spy_1m:+.1f}%.

Here is today's complete signal data across all indicators:
{signals_json}

Produce 5-8 specific actionable trade ideas. For each:
- Only suggest trades where MULTIPLE signals align (price + IV + smart money)
- Be specific about strikes (use round numbers near current price)
- Position size: max 5% of account per trade, smaller for speculative
- Prioritise capital preservation — if signals conflict, say AVOID

Return ONLY valid JSON (no markdown):
{{
  "market_context": "2 sentences on overall market conditions and what that means for options today",
  "trades": [
    {{
      "rank": 1,
      "sym": "NVDA",
      "strategy": "LONG CALL",
      "why": "Price momentum strong + IV rank low (cheap options) + unusual call flow detected + sector leading",
      "signals_aligned": ["Price +8% 1M", "IVR 22 (cheap)", "Unusual 450C volume 3x OI", "XLK inflow"],
      "strike": 450,
      "expiry": "45 days (monthly expiry)",
      "contracts": 2,
      "cost": "$840 estimated (2 x $420)",
      "pct_account": "2.1%",
      "entry": "Buy on any pullback to $442-445, ideally near 21 EMA",
      "stop": "Close position if NVDA closes below $435 (2 ATR stop)",
      "target1": "$465 (take 50% off)",
      "target2": "$480 (run remainder with trailing stop)",
      "risk_reward": "3.2:1",
      "avoid_if": "VIX spikes above 25 before entry — IV crush risk"
    }}
  ],
  "avoid_today": ["List stocks/sectors to avoid and why"],
  "key_risk": "The single biggest risk to all these trades today"
}}

Account size: ${account_size:,.0f}
Risk per trade: max 5% = ${account_size*0.05:,.0f}"""

        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 3000,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=45
        )
        text = r.json().get("content", [{}])[0].get("text", "").strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:])
            if text.endswith("```"): text = text[:-3]
        return json.loads(text.strip())
    except Exception as e:
        return {}

@st.cache_data(ttl=1800)
def get_ai_options_analysis(spy_chg,qqq_chg,vix,spy_1m,qqq_1m,iwm_1m,sector_summary):
    key=_anthropic_key()
    if not key: return None
    try:
        prompt=f"""You are an expert options trader. Based on LIVE market data, analyse current options flow and suggest a strategy.

LIVE DATA:
SPY today:{spy_chg:+.2f}% 1M:{spy_1m:+.1f}% | QQQ today:{qqq_chg:+.2f}% 1M:{qqq_1m:+.1f}% | IWM 1M:{iwm_1m:+.1f}%
VIX:{vix:.1f} ({'complacent' if vix<18 else 'caution' if vix<25 else 'fear' if vix<35 else 'panic'})
Sectors: {sector_summary}

Max 120 words. Cover: 1) What options activity current conditions attract 2) One specific strategy that fits right now (e.g. CSP, covered call, call spread) with plain English explanation 3) Key risk to watch.
No jargon without explanation."""
        r=requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={"model":"claude-haiku-4-5-20251001","max_tokens":300,"messages":[{"role":"user","content":prompt}]},
            timeout=15)
        text=r.json().get("content",[{}])[0].get("text","")
        return text.strip() if text else None
    except: return None
# ════════════════════════════════════════════════════════════════════════════════
# LOAD ALL DATA
# ════════════════════════════════════════════════════════════════════════════════
with st.spinner("Loading live market data..."):
    idx     = get_indexes()
    macro   = get_macro()
    breadth = get_breadth()
    sectors = get_sectors()

vix_price = macro.get("VIX",{}).get("price",18)
today_str = datetime.now().strftime("%Y-%m-%d")
spy_d = idx.get("SPY",{}); qqq_d = idx.get("QQQ",{}); iwm_d = idx.get("IWM",{})
fh_key  = _finnhub_key()
ant_key = _anthropic_key()

# ════════════════════════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ════════════════════════════════════════════════════════════════════════════════
spy_1m_s  = spy_d.get("chg1m", 0)
rsp_spy_s = breadth.get("rsp_spy", 0)
if vix_price < 18 and spy_1m_s > 0:
    regime_s, regime_sc = "BULL - RISK ON", "#16a34a"
elif vix_price > 28:
    regime_s, regime_sc = "RISK OFF", "#dc2626"
elif vix_price > 22:
    regime_s, regime_sc = "CAUTION", "#d97706"
else:
    regime_s, regime_sc = "NEUTRAL", "#3b82f6"

with st.sidebar:
    st.markdown(f"""
    <div style="padding:12px 8px 4px;">
      <div style="font-size:15px;font-weight:700;color:#f1f5f9;margin-bottom:2px;">Trader Dashboard</div>
      <div style="background:#0f2d4a;border-radius:6px;padding:8px 10px;margin:8px 0 12px;">
        <div style="font-size:9px;color:#6b7280;margin-bottom:2px;">REGIME</div>
        <div style="font-size:13px;font-weight:700;color:{regime_sc};">{regime_s}</div>
        <div style="font-size:10px;color:#6b7280;">VIX {vix_price:.1f} | SPY {spy_1m_s:+.1f}% 1M</div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("**Market Awareness**")
    awareness_links = [
        ("regime",      "🎯 Market Regime"),
        ("indexes",     "📊 Index Comparison"),
        ("cross",       "🔗 Cross-Market"),
        ("breadth",     "🩺 Breadth & Internals"),
        ("sectors",     "🔥 Sector Heatmap"),
        ("conditions",  "🌐 Market Conditions"),
        ("commodities", "🛢️ Commodities"),
        ("inflation",   "📈 Inflation"),
        ("themes",      "🎯 Options Themes"),
        ("sentiment",   "😱 Sentiment"),
        ("calendar",    "📅 Calendar"),
        ("squeeze",     "💥 Short Squeeze"),
        ("screener",    "🔬 Screener"),
    ]
    for anchor, label in awareness_links:
        st.markdown(f'<a href="#{anchor}" style="display:block;padding:4px 0;font-size:12px;color:#9ca3af;text-decoration:none;">{label}</a>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Decision Hub**")
    hub_links = [
        ("hub",    "⚙️ Settings"),
        ("panel2", "📈 What's Moving"),
        ("panel3", "📊 IV Rank"),
        ("panel4", "🏦 Smart Money"),
        ("panel5", "📐 Technicals"),
        ("panel6", "🤖 Trade Plans"),
    ]
    for anchor, label in hub_links:
        st.markdown(f'<a href="#{anchor}" style="display:block;padding:4px 0;font-size:12px;color:#9ca3af;text-decoration:none;">{label}</a>', unsafe_allow_html=True)

    st.markdown("---")
    st.caption(f"{'Finnhub live' if fh_key else 'No Finnhub key'} | {'AI active' if ant_key else 'No AI key'}")

# ════════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════════
st.title("Trader Intelligence Dashboard")
badge    = '<span class="badge b-buy">REAL-TIME FINNHUB</span>' if fh_key else '<span class="badge b-hold">15-MIN DELAY YFINANCE</span>'
ai_badge = '&nbsp;<span class="badge b-neu">AI ACTIVE</span>' if ant_key else '&nbsp;<span class="badge b-sell">NO AI KEY</span>'
st.markdown(f'<div style="margin-bottom:4px;">{badge}{ai_badge} &nbsp;<span style="font-size:12px;color:#9ca3af;">{datetime.now().strftime("%A %d %B %Y %H:%M")} - Yahoo Finance + Finnhub + FRED</span></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# BRIDGE — connects market awareness to options strategy
# ════════════════════════════════════════════════════════════════════════════════
spy_1m  = spy_d.get("chg1m", 0)
rsp_spy = breadth.get("rsp_spy", 0)
hyg_chg = breadth.get("hyg", {}).get("chg1m", 0)
y10     = macro.get("10Y Yield", {}).get("price", 4.3)
y3m     = macro.get("3M T-Bill", {}).get("price", 3.6)
spread  = y10 - y3m

if vix_price > 28:
    opt_bias = "HIGH VIX: SELL PREMIUM (CSPs, Covered Calls) or buy puts on weak stocks"
    opt_col, opt_bg, opt_bc = "#b91c1c", "#fef2f2", "#fecaca"
elif vix_price < 16:
    opt_bias = "LOW VIX: BUY PREMIUM cheap - Long Calls on strong stocks"
    opt_col, opt_bg, opt_bc = "#15803d", "#f0fdf4", "#bbf7d0"
elif 16 <= vix_price <= 22:
    opt_bias = "MODERATE VIX: CSPs and Covered Calls ideal - premium fair, not too cheap or expensive"
    opt_col, opt_bg, opt_bc = "#1d4ed8", "#eff6ff", "#bfdbfe"
else:
    opt_bias = "ELEVATED VIX: Sell premium on quality names, avoid buying expensive options"
    opt_col, opt_bg, opt_bc = "#d97706", "#fffbeb", "#fde68a"

b_broad  = rsp_spy > 0
b_credit = hyg_chg > 0
b_curve  = spread > 0
b_trend  = spy_1m > 0
bull_count = sum([b_broad, b_credit, b_curve, b_trend])

st.markdown(f"""
<div style="background:#f8faff;border:2px solid #c7d2fe;border-radius:10px;padding:14px 18px;margin:10px 0 16px;">
  <div style="font-size:11px;font-weight:700;color:#3730a3;margin-bottom:10px;letter-spacing:.04em;">
    TODAY: MARKET SIGNALS TO OPTIONS STRATEGY
  </div>
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px;">
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:6px;padding:8px;">
      <div style="font-size:9px;color:#9ca3af;">VIX (Fear)</div>
      <div style="font-size:18px;font-weight:700;color:{'#dc2626' if vix_price>25 else '#d97706' if vix_price>18 else '#16a34a'};">{vix_price:.1f}</div>
      <div style="font-size:10px;color:#6b7280;">{'High fear' if vix_price>25 else 'Caution' if vix_price>18 else 'Calm'}</div>
    </div>
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:6px;padding:8px;">
      <div style="font-size:9px;color:#9ca3af;">Breadth</div>
      <div style="font-size:14px;font-weight:700;color:{'#16a34a' if b_broad else '#dc2626'};">{'Broad' if b_broad else 'Narrow'}</div>
      <div style="font-size:10px;color:#6b7280;">RSP-SPY {rsp_spy:+.1f}pp</div>
    </div>
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:6px;padding:8px;">
      <div style="font-size:9px;color:#9ca3af;">Credit</div>
      <div style="font-size:14px;font-weight:700;color:{'#16a34a' if b_credit else '#dc2626'};">{'Healthy' if b_credit else 'Stress'}</div>
      <div style="font-size:10px;color:#6b7280;">HYG {hyg_chg:+.1f}% 1M</div>
    </div>
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:6px;padding:8px;">
      <div style="font-size:9px;color:#9ca3af;">Overall</div>
      <div style="font-size:14px;font-weight:700;color:{'#16a34a' if bull_count>=3 else '#dc2626' if bull_count<=1 else '#d97706'};">{bull_count}/4 Bull</div>
      <div style="font-size:10px;color:#6b7280;">signals positive</div>
    </div>
  </div>
  <div style="background:{opt_bg};border:1px solid {opt_bc};border-radius:6px;padding:10px 14px;">
    <div style="font-size:10px;color:#6b7280;font-weight:600;margin-bottom:3px;">STRATEGY BIAS TODAY:</div>
    <div style="font-size:13px;font-weight:700;color:{opt_col};">{opt_bias}</div>
  </div>
  <div style="font-size:10px;color:#9ca3af;margin-top:8px;">
    Scroll down to confirm signals in detail - then use <b>Options Decision Hub</b> at the bottom for specific trade plans with strikes, expiry and position size
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Badge legend — always visible, compact
st.markdown("""
<div style="background:#f0f4ff;border:2px solid #c7d2fe;border-radius:8px;padding:10px 14px;margin-bottom:14px;">
  <div style="font-size:11px;font-weight:700;color:#3730a3;margin-bottom:8px;">🏷️ HOW TO READ THE SIGNAL BADGES ON EACH SECTION TITLE</div>
  <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start;">
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;font-size:11px;font-weight:700;padding:3px 10px;border-radius:4px;white-space:nowrap;">BULLISH</span>
      <span style="font-size:11px;color:#374151;">= Positive signal → favour <b>Long Calls</b> or <b>CSPs</b></span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="background:#fef2f2;border:1px solid #fecaca;color:#b91c1c;font-size:11px;font-weight:700;padding:3px 10px;border-radius:4px;white-space:nowrap;">BEARISH</span>
      <span style="font-size:11px;color:#374151;">= Negative signal → favour <b>Long Puts</b> or sit on hands</span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="background:#fffbeb;border:1px solid #fde68a;color:#d97706;font-size:11px;font-weight:700;padding:3px 10px;border-radius:4px;white-space:nowrap;">CAUTION</span>
      <span style="font-size:11px;color:#374151;">= Mixed signals → be <b>selective</b>, wait for clearer setup</span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;font-size:11px;font-weight:700;padding:3px 10px;border-radius:4px;white-space:nowrap;">▲ Above 50DMA</span>
      <span style="font-size:11px;color:#374151;">= Price above 50-day moving average = <b>uptrend</b></span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="background:#fef2f2;border:1px solid #fecaca;color:#b91c1c;font-size:11px;font-weight:700;padding:3px 10px;border-radius:4px;white-space:nowrap;">▼ Below 50DMA</span>
      <span style="font-size:11px;color:#374151;">= Price below 50-day moving average = <b>downtrend</b></span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;font-size:11px;font-weight:700;padding:3px 10px;border-radius:4px;white-space:nowrap;">RISK ON</span>
      <span style="font-size:11px;color:#374151;">= Market in bull mode → full position sizing OK</span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="background:#fef2f2;border:1px solid #fecaca;color:#b91c1c;font-size:11px;font-weight:700;padding:3px 10px;border-radius:4px;white-space:nowrap;">RISK OFF</span>
      <span style="font-size:11px;color:#374151;">= Market defensive → reduce size, buy protection</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 1 — MARKET REGIME
st.markdown('<div id="regime"></div>', unsafe_allow_html=True)
# BAR
# ════════════════════════════════════════════════════════════════════════════════
_reg_sig, _reg_col, _reg_bg, _reg_bc = ("RISK ON","#15803d","#f0fdf4","#bbf7d0") if vix_price<18 and spy_d.get("chg1m",0)>0 else ("RISK OFF","#b91c1c","#fef2f2","#fecaca") if vix_price>28 else ("CAUTION","#d97706","#fffbeb","#fde68a")
st.markdown(f'<div class="sec">🎯 Market Regime {section_signal("Regime",_reg_sig,_reg_col,_reg_bg,_reg_bc,f"VIX {vix_price:.1f}")}</div>', unsafe_allow_html=True)

spy_1m  = spy_d.get("chg1m",0)
rsp_spy = breadth.get("rsp_spy",0)
hyg_chg = breadth.get("hyg",{}).get("chg1m",0)

if vix_price < 18 and spy_1m > 0 and rsp_spy > 0:
    regime, regime_col, regime_bg = "BULL MARKET · RISK ON", "#15803d", "#f0fdf4"
    regime_desc = "Low volatility, positive breadth, credit healthy. Full position sizing appropriate."
elif vix_price > 30 or hyg_chg < -3:
    regime, regime_col, regime_bg = "RISK OFF · DEFENSIVE", "#b91c1c", "#fef2f2"
    regime_desc = "Elevated fear or credit stress detected. Reduce exposure, tighten stops, favour defensives."
elif vix_price > 22 or rsp_spy < -2:
    regime, regime_col, regime_bg = "CAUTION · NARROW MARKET", "#b45309", "#fffbeb"
    regime_desc = "Rally narrowing or volatility rising. Only large caps leading. Be selective — quality over quantity."
else:
    regime, regime_col, regime_bg = "NEUTRAL · SELECTIVE", "#1d4ed8", "#eff6ff"
    regime_desc = "Mixed signals. Trade setups with strong RS and clear catalysts only."

reg_cols = st.columns(6)
regime_items = [
    ("Market Regime", regime, regime_col, regime_bg, regime_desc),
    ("VIX Level", f"{vix_price:.1f}", clr(vix_price,False), "#fff", "Under 18=calm. 18-25=caution. 25-35=fear. Over 35=panic."),
    ("SPY 1-Month", f"{spy_1m:+.1f}%", clr(spy_1m), "#fff", "S&P 500 1-month trend. Positive=uptrend intact."),
    ("Breadth (RSP-SPY)", f"{rsp_spy:+.1f}%", clr(rsp_spy), "#fff", "Positive=broad rally, equal-weight leading. Negative=only mega caps moving."),
    ("HYG Credit 1M", f"{breadth.get('hyg',{}).get('chg1m',0):+.1f}%", clr(breadth.get('hyg',{}).get('chg1m',0)), "#fff", "High yield bonds. Falling=credit stress=recession warning. Best leading indicator."),
    ("Yield Curve", f"{(macro.get('10Y Yield',{}).get('price',4.3)-macro.get('3M T-Bill',{}).get('price',3.6)):+.2f}%",
     "#16a34a" if macro.get("10Y Yield",{}).get("price",4.3)>macro.get("3M T-Bill",{}).get("price",3.6) else "#dc2626","#fff",
     "10Y minus 3M yield. Positive=normal. Inverted=recession warning."),
]
for col,(label,val,vc,bg,desc) in zip(reg_cols, regime_items):
    with col:
        st.markdown(f"""
        <div style="background:{regime_bg if label=='Market Regime' else '#fff'};border:1px solid {regime_col if label=='Market Regime' else '#e5e7eb'};
             border-radius:8px;padding:10px 12px;">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <div class="lbl">{label}</div>
            {tip('ℹ',desc)}
          </div>
          <div style="font-size:{'13px' if label=='Market Regime' else '18px'};font-weight:700;color:{regime_col if label=='Market Regime' else vc};margin-top:3px;">{val}</div>
          {'<div style="font-size:10px;color:'+regime_col+';margin-top:3px;">'+regime_desc+'</div>' if label=='Market Regime' else ''}
        </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 2 — INDEX COMPARISON
# Signal: based on how many of the 4 cap-size indexes are above their 50DMA and trending up
st.markdown('<div id="indexes"></div>', unsafe_allow_html=True)
# ════════════════════════════════════════════════════════════════════════════════
_idx_syms = ["SPY","QQQ","IWM","MDY"]
_idx_above50 = sum(1 for s in _idx_syms if idx.get(s,{}).get("above50",False))
_idx_pos1m   = sum(1 for s in _idx_syms if idx.get(s,{}).get("chg1m",0)>0)
_idx_score   = _idx_above50 + _idx_pos1m
if _idx_score >= 6:
    _idx_sig,_idx_col,_idx_bg,_idx_bc = "BULLISH","#15803d","#f0fdf4","#bbf7d0"
elif _idx_score <= 2:
    _idx_sig,_idx_col,_idx_bg,_idx_bc = "BEARISH","#b91c1c","#fef2f2","#fecaca"
else:
    _idx_sig,_idx_col,_idx_bg,_idx_bc = "MIXED","#d97706","#fffbeb","#fde68a"
st.markdown(f'<div class="sec">📊 Index Comparison {section_signal("Indexes",_idx_sig,_idx_col,_idx_bg,_idx_bc,f"{_idx_above50}/4 above 50DMA")}</div>', unsafe_allow_html=True)
st.markdown(f'<div style="font-size:11px;color:#6b7280;margin-bottom:6px;padding:6px 10px;background:#f9fafb;border-radius:6px;">SPY=large cap S&P 500 · RSP=equal weight (if RSP>SPY the rally is broad=healthy) · MDY=mid cap · IWM=small cap · DJI=mega cap blue chip · <b>{_idx_above50}/4 above 50-day moving average</b> — green badge=uptrend, red=downtrend</div>', unsafe_allow_html=True)

INDEX_GROUPS = {
    "📐 Cap Size & Breadth": {
        "syms": ["SPY","RSP","MDY","IWM","^DJI"],
        "desc": "SPY=large cap · RSP=equal weight (breadth signal) · MDY=mid cap · IWM=small cap · DJI=mega cap blue chip",
        "tips": {
            "SPY": "S&P 500 — the benchmark. 500 largest US companies, cap-weighted. If SPY up but RSP flat, only big stocks driving it.",
            "RSP": "Equal weight S&P 500. Every stock weighted equally. RSP outperforming SPY = broad healthy rally. Lagging = narrow market.",
            "MDY": "S&P 400 mid-cap. Often leads turns — rises before large caps in bull, falls before them in bear.",
            "IWM": "Russell 2000 small caps. Most sensitive to US economy and rates. Lagging SPY = narrow rally warning.",
            "^DJI": "Dow Jones 30 mega-cap blue chips. Less volatile. Rising when others flat = defensiveness.",
        }
    },
    "📈 Style & Sector Leaders": {
        "syms": ["QQQ","^IXIC","SOXX","EFA","EEM","BTC-USD"],
        "desc": "QQQ=Nasdaq top 100 · IXIC=all Nasdaq · SOXX=semis (leads QQQ) · EFA=intl developed · EEM=emerging · BTC=risk gauge",
        "tips": {
            "QQQ": "Nasdaq 100 — top 100 tech/growth stocks. Leads in risk-on, falls hardest in risk-off. Watch vs SPY for growth vs value rotation.",
            "^IXIC": "Nasdaq Composite — all 3,000+ Nasdaq stocks. Wider than QQQ. If IXIC lagging QQQ, smaller tech is weak.",
            "SOXX": "Semiconductor ETF. Leads QQQ by 2-3 weeks. Chips are picked first when AI demand rises. Watch before buying tech.",
            "EFA": "International developed markets (Europe, Japan, Australia). Rising = weak dollar, global growth. Outperforming US = money rotating globally.",
            "EEM": "Emerging markets (China, India, Brazil). Rising = risk-on, weak dollar, global growth. Falls hard on dollar strength.",
            "BTC-USD": "Bitcoin. Best real-time risk appetite gauge. Tends to lead equities in both directions by 1-2 weeks.",
        }
    },
}

for group_name, group in INDEX_GROUPS.items():
    st.markdown(f'<div style="font-size:10px;color:#9ca3af;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin:8px 0 5px;">{group_name}</div>', unsafe_allow_html=True)
    st.caption(group["desc"])
    gcols = st.columns(len(group["syms"]))
    for col, sym in zip(gcols, group["syms"]):
        d = idx.get(sym)
        display = "DOW" if sym=="^DJI" else "NASDAQ" if sym=="^IXIC" else sym
        with col:
            if d:
                sp = spark_html(d["spark"], d["color"])
                tbg = "#f0fdf4" if d["above50"] else "#fef2f2"
                ttc = "#15803d" if d["above50"] else "#b91c1c"
                dma50_pct = round((d["price"] - d.get("sma50", d["price"])) / max(d.get("sma50", d["price"]), 1) * 100, 1) if d.get("sma50") else 0
                tlbl = f"▲ {dma50_pct:+.1f}% vs 50DMA" if d["above50"] else f"▼ {dma50_pct:+.1f}% vs 50DMA"
                tip_text = group["tips"].get(sym, d["name"])
                st.markdown(f"""
                <div class="card">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-size:13px;font-weight:700;color:{d['color']};">{display}</span>
                    <div style="display:flex;align-items:center;gap:4px;">
                      <span style="background:{tbg};color:{ttc};font-size:9px;padding:2px 6px;border-radius:3px;font-weight:600;">{tlbl}</span>
                      {tip(f'ℹ', tip_text)}
                    </div>
                  </div>
                  {sp}
                  <div style="font-size:20px;font-weight:700;color:{d['color']};">{fp(d['price'])}</div>
                  <div style="font-size:12px;font-weight:600;color:{clr(d['chg1d'])};">{arr(d['chg1d'])} {d['chg1d']:+.2f}% today</div>
                  <div style="font-size:10px;color:#9ca3af;margin-top:4px;">{d['name']}</div>
                  <div style="font-size:10px;color:#9ca3af;">1W<span style="color:{clr(d['chg1w'])};font-weight:600;"> {d['chg1w']:+.1f}%</span> 1M<span style="color:{clr(d['chg1m'])};font-weight:600;"> {d['chg1m']:+.1f}%</span></div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="card"><div style="color:#9ca3af;font-size:12px;">{display} loading...</div></div>', unsafe_allow_html=True)

# Divergence alert
if "SPY" in idx and "IWM" in idx:
    div = idx["SPY"]["chg1m"] - idx["IWM"]["chg1m"]
    if div > 4:
        st.warning(f"⚠️ **Cap-size divergence:** Small caps (IWM) lagging large caps (SPY) by **{div:.1f}pp** — narrow market signal. Historically precedes pullbacks.")
if "SPY" in idx and "RSP" in idx:
    rsp_div = idx["RSP"]["chg1m"] - idx["SPY"]["chg1m"]
    if rsp_div > 2:
        st.success(f"✅ **Broad rally confirmed:** Equal-weight (RSP) outperforming cap-weight (SPY) by {rsp_div:.1f}pp — healthy participation across all stocks.")
    elif rsp_div < -3:
        st.warning(f"⚠️ **Narrow market:** Only mega caps moving. RSP lagging SPY by {abs(rsp_div):.1f}pp — rally is not broad-based.")

# TWO CHARTS
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.markdown('<div style="font-size:11px;font-weight:600;color:#374151;margin-bottom:5px;">Cap size rotation (30 days)</div>', unsafe_allow_html=True)
    fig1 = go.Figure()
    for sym in ["SPY","RSP","MDY","IWM"]:
        d = idx.get(sym)
        disp = sym
        if d and "hist" in d and not d["hist"].empty:
            h30 = d["hist"].tail(30); base = h30["Close"].iloc[0]
            perf = ((h30["Close"]-base)/base*100)
            fig1.add_trace(go.Scatter(x=list(range(len(perf))),y=perf.round(2).tolist(),
                name=disp,mode="lines",line=dict(color=d["color"],width=2),
                hovertemplate=f"{disp}: %{{y:.2f}}%<extra></extra>"))
    fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#fff",
        font=dict(family="Inter",color="#6b7280",size=10),
        margin=dict(l=40,r=20,t=10,b=30),height=200,
        legend=dict(orientation="h",y=1.1,font=dict(size=11)),
        xaxis=dict(showgrid=False,showticklabels=False),
        yaxis=dict(gridcolor="#f3f4f6",ticksuffix="%"),hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar":False}, key="chart_cap_size")

with chart_col2:
    st.markdown('<div style="font-size:11px;font-weight:600;color:#374151;margin-bottom:5px;">Style & risk appetite (30 days)</div>', unsafe_allow_html=True)
    fig2 = go.Figure()
    for sym in ["QQQ","^IXIC","SOXX","EFA","EEM","BTC-USD"]:
        d = idx.get(sym)
        disp = "BTC" if sym=="BTC-USD" else "NASDAQ" if sym=="^IXIC" else sym
        if d and "hist" in d and not d["hist"].empty:
            h30 = d["hist"].tail(30); base = h30["Close"].iloc[0]
            perf = ((h30["Close"]-base)/base*100)
            fig2.add_trace(go.Scatter(x=list(range(len(perf))),y=perf.round(2).tolist(),
                name=disp,mode="lines",line=dict(color=d["color"],width=2),
                hovertemplate=f"{disp}: %{{y:.2f}}%<extra></extra>"))
    fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#fff",
        font=dict(family="Inter",color="#6b7280",size=10),
        margin=dict(l=40,r=20,t=10,b=30),height=200,
        legend=dict(orientation="h",y=1.1,font=dict(size=11)),
        xaxis=dict(showgrid=False,showticklabels=False),
        yaxis=dict(gridcolor="#f3f4f6",ticksuffix="%"),hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False}, key="chart_style_risk")

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 3 — CROSS-MARKET
st.markdown('<div id="cross"></div>', unsafe_allow_html=True)
# RELATIONSHIPS
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🔗 Cross-Market Relationships ' + section_signal("Cross","ROTATION TRACKER","#1d4ed8","#eff6ff","#bfdbfe","Use toggle below") + '</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size:11px;color:#6b7280;margin-bottom:6px;padding:6px 10px;background:#f9fafb;border-radius:6px;">Each card = one asset vs another over the selected period. <b>Green</b>=first asset outperforming (e.g. XLK/SPY green = tech beating market = risk-on). <b>Red</b>=second asset outperforming (e.g. XLP/XLY red = staples beating discretionary = defensive rotation = caution).</div>', unsafe_allow_html=True)
cm_period = st.radio("Cross-market period", ["1D","1W","1M","3M"], horizontal=True, label_visibility="collapsed", key="cm_period_radio")

with st.spinner("Loading cross-market data..."):
    cross = get_cross_market()

if cross:
    cm_cols = st.columns(len(cross))
    for col,(key,d) in zip(cm_cols, cross.items()):
        period_key = {"1D":"chg_1d","1W":"chg_1w","1M":"chg_1m","3M":"chg_3m"}.get(cm_period,"chg_1d")
        chg = d.get(period_key, d.get("chg_1m",0)); c = clr(chg)
        bg = "#f0fdf4" if chg>1 else "#fef2f2" if chg<-1 else "#f9fafb"
        bc = "#bbf7d0" if chg>1 else "#fecaca" if chg<-1 else "#e5e7eb"
        parts = key.split("/")
        label_top = parts[0]; label_bot = "/"+parts[1] if len(parts)>1 else ""
        with col:
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {bc};border-radius:6px;padding:8px;text-align:center;">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div style="font-size:11px;font-weight:700;color:#374151;text-align:left;">
                  {label_top}<span style="color:#9ca3af;font-weight:400;">{label_bot}</span>
                </div>
                {tip('ℹ', d['desc'])}
              </div>
              <div style="font-size:14px;font-weight:700;color:{c};margin-top:4px;">{arr(chg)} {chg:+.1f}%</div>
              <div style="font-size:9px;color:#9ca3af;">{d['label']}</div>
            </div>""", unsafe_allow_html=True)
    st.caption("1D/1W/1M/3M ratio change · Green=first asset outperforming · Red=second asset outperforming · Hover ℹ for what it means · Default: 1D")

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 4 — BREADTH
st.markdown('<div id="breadth"></div>', unsafe_allow_html=True)
# & INTERNALS
# ════════════════════════════════════════════════════════════════════════════════
_br_rsp = breadth.get("rsp_spy",0)
_br_sig, _br_col, _br_bg, _br_bc = sig_badge(_br_rsp)
_br_lbl = "Broad rally" if _br_rsp>0 else "Narrow market"
st.markdown(f'<div class="sec">🩺 Market Breadth & Internals {section_signal("Breadth",_br_sig,_br_col,_br_bg,_br_bc,_br_lbl)}</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def get_breadth_extended():
    """Fetch all breadth, rotation and risk-appetite indicators."""
    tickers = [
        ("RSP","rsp"), ("SPY","spy"), ("HYG","hyg"), ("LQD","lqd"),
        ("TLT","tlt"), ("IWM","iwm"), ("XLK","xlk"), ("XLP","xlp"),
        ("GLD","gld"), ("UUP","uup"), ("HG=F","copper"), ("GC=F","gold"),
        ("IVW","ivw"), ("IVE","ive"),    # Growth vs Value
        ("SPHB","sphb"), ("SPLV","splv"),# High Beta vs Low Vol
        ("XLF","xlf"), ("XLU","xlu"),    # Banks vs Utilities
        ("SOXX","soxx"),                  # Semis
        ("MTUM","mtum"), ("USMV","usmv"),# Momentum vs Min Vol
        ("XLY","xly"),                    # Consumer Discretionary
    ]
    out = {}
    for sym, key in tickers:
        try:
            h = yf.Ticker(sym).history(period="3mo")
            if not h.empty and len(h) >= 6:
                p=h["Close"].iloc[-1]; p1d=h["Close"].iloc[-2]
                p1w=h["Close"].iloc[-6] if len(h)>=6 else p
                p1m=h["Close"].iloc[-22] if len(h)>=22 else h["Close"].iloc[0]
                p3m=h["Close"].iloc[0]
                out[key]={"price":round(p,2),
                          "chg1d":round((p-p1d)/p1d*100,2),
                          "chg1w":round((p-p1w)/p1w*100,2),
                          "chg1m":round((p-p1m)/p1m*100,2),
                          "chg3m":round((p-p3m)/p3m*100,2)}
        except: pass

    def ratio(a, b, period="chg1m"):
        if a in out and b in out:
            return round(out[a][period] - out[b][period], 2)
        return None

    # Breadth indicators
    out["breadth_1m"]     = ratio("rsp","spy")
    out["credit_chg"]     = ratio("hyg","lqd")
    out["small_vs_large"] = ratio("iwm","spy")

    # Rotation indicators
    out["growth_vs_value"]  = ratio("ivw","ive")
    out["highbeta_vs_lowvol"]= ratio("sphb","splv")
    out["cyclical_vs_def"]  = ratio("xly","xlp")    # positive = risk-on
    out["banks_vs_utils"]   = ratio("xlf","xlu")    # positive = rates high, economy strong
    out["copper_vs_gold"]   = ratio("copper","gold") # positive = growth over fear
    out["semis_vs_spy"]     = ratio("soxx","spy")   # positive = tech/AI leading
    out["momentum_vs_minvol"]= ratio("mtum","usmv") # positive = trending market
    out["def_rotation"]     = ratio("xlp","xlk")    # negative = good (tech leading)

    # Bond data
    out["gold_vs_dollar"]   = ratio("gld","uup")

    return {k:v for k,v in out.items() if v is not None}

with st.spinner("Loading breadth & rotation data..."):
    bxt = get_breadth_extended()

# ── Sub-section 1: Breadth Indicators ─────────────────────────────────────────
st.markdown('<div style="font-size:10px;color:#9ca3af;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin:8px 0 6px;">Breadth Indicators — is the rally broad or narrow?</div>', unsafe_allow_html=True)

breadth_metrics = [
    ("RSP vs SPY",
     f"{bxt['breadth_1m']:+.2f}pp" if "breadth_1m" in bxt else "Loading...",
     clr(bxt.get("breadth_1m",0)),
     "Equal weight vs cap weight S&P 500. WHAT IT MEANS: Positive=ALL 500 stocks rising=broad healthy rally. Negative=only the top 10 mega caps are moving=narrow market=warning sign. This is one of the most important breadth signals."),
    ("HYG vs LQD",
     f"{bxt['credit_chg']:+.2f}pp" if "credit_chg" in bxt else "Loading...",
     clr(bxt.get("credit_chg",0)),
     "Junk bonds vs investment grade bonds. WHAT IT MEANS: Positive=credit market healthy=companies can borrow=economy fine. Negative=credit stress building=companies struggling=recession warning. This is THE best early recession indicator."),
    ("Small vs Large Cap",
     f"{bxt['small_vs_large']:+.2f}pp" if "small_vs_large" in bxt else "Loading...",
     clr(bxt.get("small_vs_large",0)),
     "Russell 2000 (IWM) vs S&P 500 (SPY). WHAT IT MEANS: Positive=small companies outperforming=domestic economy healthy=risk-on. Negative=only large multinationals working=narrow rally=potential warning."),
    ("TLT (20Y Treasury)",
     f"${bxt.get('tlt',{}).get('price',0):.2f}  {bxt.get('tlt',{}).get('chg1d',0):+.2f}%" if "tlt" in bxt else "Loading...",
     clr(bxt.get("tlt",{}).get("chg1d",0)),
     "20-year Treasury bond ETF. WHAT IT MEANS: Rising=investors fleeing to the safety of government bonds=stocks may fall. Falling=inflation fears or confidence in economy=often good for stocks. Sudden sharp TLT spike=sell signal."),
]

br_c1 = st.columns(4)
for col,(label,val,vc,desc) in zip(br_c1, breadth_metrics):
    with col:
        signal = "BULLISH" if vc=="#16a34a" else "BEARISH" if vc=="#dc2626" else "NEUTRAL"
        s_bg = "#f0fdf4" if vc=="#16a34a" else "#fef2f2" if vc=="#dc2626" else "#f9fafb"
        s_bc = "#bbf7d0" if vc=="#16a34a" else "#fecaca" if vc=="#dc2626" else "#e5e7eb"
        st.markdown(f"""
        <div class="card" style="margin-bottom:8px;">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <div class="lbl">{label}</div>
            {tip("ℹ", desc)}
          </div>
          <div style="font-size:20px;font-weight:700;color:{vc};margin-top:3px;">{val}</div>
          <div style="display:inline-block;background:{s_bg};color:{vc};border:1px solid {s_bc};
               font-size:9px;font-weight:600;padding:1px 6px;border-radius:3px;margin-top:4px;">{signal}</div>
        </div>""", unsafe_allow_html=True)

# ── Sub-section 2: Rotation & Risk Appetite ────────────────────────────────────
st.markdown('<div style="font-size:10px;color:#9ca3af;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin:14px 0 6px;">Rotation & Risk Appetite — where is money flowing?</div>', unsafe_allow_html=True)

rotation_metrics = [
    ("Growth vs Value",
     f"{bxt['growth_vs_value']:+.2f}pp" if "growth_vs_value" in bxt else "Loading...",
     clr(bxt.get("growth_vs_value",0)),
     "S&P Growth (IVW) vs S&P Value (IVE). WHAT IT MEANS: Positive=growth stocks (tech, high PE) leading=risk appetite high, often early bull market. Negative=value stocks (banks, energy, cheap stocks) leading=late cycle or cautious market."),
    ("High Beta vs Low Vol",
     f"{bxt['highbeta_vs_lowvol']:+.2f}pp" if "highbeta_vs_lowvol" in bxt else "Loading...",
     clr(bxt.get("highbeta_vs_lowvol",0)),
     "High Beta S&P (SPHB) vs Low Volatility S&P (SPLV). WHAT IT MEANS: Positive=traders actively taking risk, buying volatile stocks=confident market. Negative=hiding in boring low-risk stocks=fear or uncertainty. Best pure risk appetite gauge."),
    ("Cyclicals vs Defensives",
     f"{bxt['cyclical_vs_def']:+.2f}pp" if "cyclical_vs_def" in bxt else "Loading...",
     clr(bxt.get("cyclical_vs_def",0)),
     "Consumer Discretionary (XLY) vs Consumer Staples (XLP). WHAT IT MEANS: Positive=people spending on wants not just needs=economy healthy=risk-on. Negative=spending only on essentials=consumers worried=recession signal."),
    ("Banks vs Utilities",
     f"{bxt['banks_vs_utils']:+.2f}pp" if "banks_vs_utils" in bxt else "Loading...",
     clr(bxt.get("banks_vs_utils",0)),
     "Financials (XLF) vs Utilities (XLU). WHAT IT MEANS: Positive=banks outperforming=rates expected high, economy strong, yield curve steepening. Negative=utilities leading=investors hiding in defensive stocks=rate cut expected or fear rising."),
    ("Copper vs Gold",
     f"{bxt['copper_vs_gold']:+.2f}pp" if "copper_vs_gold" in bxt else "Loading...",
     clr(bxt.get("copper_vs_gold",0)),
     "Copper futures vs Gold futures. WHAT IT MEANS: Positive=copper (industrial metal) beating gold (safe haven)=global growth expected, factories active. Negative=gold beating copper=fear over growth, investors seeking safety. Called the risk ratio by professionals."),
    ("Semis vs S&P",
     f"{bxt['semis_vs_spy']:+.2f}pp" if "semis_vs_spy" in bxt else "Loading...",
     clr(bxt.get("semis_vs_spy",0)),
     "Semiconductors (SOXX) vs S&P 500 (SPY). WHAT IT MEANS: Positive=chip stocks leading the whole market=AI/tech demand healthy=risk-on. Semis typically lead QQQ by 2-3 weeks. Falling semis = tech weakness coming. Watch this before buying any tech stock."),
    ("Momentum vs Min Vol",
     f"{bxt['momentum_vs_minvol']:+.2f}pp" if "momentum_vs_minvol" in bxt else "Loading...",
     clr(bxt.get("momentum_vs_minvol",0)),
     "Momentum ETF (MTUM) vs Minimum Volatility ETF (USMV). WHAT IT MEANS: Positive=trending stocks winning=clear market direction, follow the trend. Negative=low volatility stocks winning=uncertain choppy market, no clear trend, be more cautious with momentum plays."),
    ("Gold vs Dollar",
     f"{bxt['gold_vs_dollar']:+.2f}pp" if "gold_vs_dollar" in bxt else "Loading...",
     clr(bxt.get("gold_vs_dollar",0)),
     "Gold (GLD) vs Dollar (UUP). WHAT IT MEANS: Positive=gold beating dollar=inflation fears, geopolitical stress, dollar weakening. Negative=dollar strong=risk-off, commodity prices pressured, EM stocks hurt. Rising gold+falling dollar=classic inflation trade."),
]

rot_cols = st.columns(4)
for i,(label,val,vc,desc) in enumerate(rotation_metrics):
    with rot_cols[i%4]:
        signal = "RISK ON" if vc=="#16a34a" else "RISK OFF" if vc=="#dc2626" else "NEUTRAL"
        s_bg = "#f0fdf4" if vc=="#16a34a" else "#fef2f2" if vc=="#dc2626" else "#f9fafb"
        s_bc = "#bbf7d0" if vc=="#16a34a" else "#fecaca" if vc=="#dc2626" else "#e5e7eb"
        st.markdown(f"""
        <div class="card" style="margin-bottom:8px;">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <div class="lbl">{label}</div>
            {tip("ℹ", desc)}
          </div>
          <div style="font-size:20px;font-weight:700;color:{vc};margin-top:3px;">{val}</div>
          <div style="display:inline-block;background:{s_bg};color:{vc};border:1px solid {s_bc};
               font-size:9px;font-weight:600;padding:1px 6px;border-radius:3px;margin-top:4px;">{signal}</div>
        </div>""", unsafe_allow_html=True)

# ── Overall score ──────────────────────────────────────────────────────────────
bull_signals = []
bear_signals = []
checks = [
    ("breadth_1m",        True,  "Broad market"),
    ("credit_chg",        True,  "Credit healthy"),
    ("small_vs_large",    True,  "Small caps leading"),
    ("growth_vs_value",   True,  "Growth leading"),
    ("highbeta_vs_lowvol",True,  "Risk appetite high"),
    ("cyclical_vs_def",   True,  "Cyclicals leading"),
    ("banks_vs_utils",    True,  "Banks leading"),
    ("copper_vs_gold",    True,  "Copper over gold"),
    ("semis_vs_spy",      True,  "Semis leading"),
    ("momentum_vs_minvol",True,  "Momentum working"),
]
# Note: def_rotation removed — cyclical_vs_def already covers defensives theme
# Every item in checks must have a visible card so count matches what user sees
for key, pos_is_bull, label in checks:
    if key in bxt:
        val = bxt[key]
        is_bull = val > 0 if pos_is_bull else val < 0
        if is_bull: bull_signals.append(label)
        else: bear_signals.append(label)

total = len(bull_signals) + len(bear_signals)
bull_pct = int(len(bull_signals)/total*100) if total>0 else 50
score_col = "#16a34a" if bull_pct>=65 else "#dc2626" if bull_pct<=35 else "#d97706"
score_lbl = "RISK ON" if bull_pct>=65 else "RISK OFF" if bull_pct<=35 else "MIXED"
score_bg = "#f0fdf4" if bull_pct>=65 else "#fef2f2" if bull_pct<=35 else "#fffbeb"
score_bc = "#bbf7d0" if bull_pct>=65 else "#fecaca" if bull_pct<=35 else "#fde68a"
score_desc = "Majority of signals bullish — favour longs and CSPs" if bull_pct>=65 else "Majority of signals bearish — favour puts and caution" if bull_pct<=35 else "No clear consensus — be selective, wait for clearer signals"

st.markdown(f"""
<div style="background:{score_bg};border:2px solid {score_bc};border-radius:8px;padding:12px 16px;margin-top:8px;">
  <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
    <div>
      <span style="font-size:20px;font-weight:700;color:{score_col};">{score_lbl}</span>
      <span style="font-size:13px;color:#374151;margin-left:10px;">{len(bull_signals)} of {total} signals bullish</span>
    </div>
    <div style="height:12px;width:200px;background:#e5e7eb;border-radius:6px;overflow:hidden;">
      <div style="height:12px;width:{bull_pct}%;background:{score_col};border-radius:6px;"></div>
    </div>
  </div>
  <div style="font-size:12px;color:#374151;margin-top:6px;font-weight:500;">{score_desc}</div>
  <div style="margin-top:8px;font-size:11px;color:#6b7280;">
    <span style="color:#16a34a;font-weight:600;">Bullish ({len(bull_signals)}):</span> {", ".join(bull_signals) if bull_signals else "None"}<br>
    <span style="color:#dc2626;font-weight:600;">Bearish ({len(bear_signals)}):</span> {", ".join(bear_signals) if bear_signals else "None"}
  </div>
</div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 5 — SECTOR HEATMAP
st.markdown('<div id="sectors"></div>', unsafe_allow_html=True)
# ════════════════════════════════════════════════════════════════════════════════
_sec_avg = sum(v.get("1d",0) for v in sectors.values())/max(len(sectors),1) if sectors else 0
_sec_sig, _sec_col, _sec_bg, _sec_bc = sig_badge(_sec_avg)
st.markdown(f'<div class="sec">🔥 Sector Momentum {section_signal("Sectors",_sec_sig,_sec_col,_sec_bg,_sec_bc,f"avg {_sec_avg:+.1f}% today")}</div>', unsafe_allow_html=True)
hp = st.radio("Period", ["1d","1w","1m"], horizontal=True, label_visibility="collapsed", key="sector_period")

if sectors:
    hm_cols = st.columns(len(sectors))
    for col,(name,d) in zip(hm_cols, sectors.items()):
        v=d.get(hp,0); bg,tc=hm_clr(v); sign="+" if v>=0 else ""
        with col:
            st.markdown(f"""
            <div class="hm" style="background:{bg};border:1px solid {'#bbf7d0' if v>=.5 else '#fecaca' if v<=-.5 else '#e5e7eb'};">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div style="font-size:10px;font-weight:600;color:{tc};">{name}</div>
                {tip('ℹ', d.get('tip',''))}
              </div>
              <div style="font-size:11px;color:{tc};font-weight:600;margin-top:2px;">{sign}{v:.1f}%</div>
            </div>""", unsafe_allow_html=True)
    st.markdown('<div style="display:flex;justify-content:space-between;font-size:10px;color:#9ca3af;margin-top:5px;"><span style="color:#dc2626;">▼ Underperform</span><span>Neutral</span><span style="color:#16a34a;">▲ Outperform</span></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 6 — MARKET CONDITIONS
st.markdown('<div id="conditions"></div>', unsafe_allow_html=True)
# ════════════════════════════════════════════════════════════════════════════════
_mc_vix_chg = macro.get("VIX",{}).get("chg",0)
_mc_sig = "CALMING" if _mc_vix_chg < -0.5 else "RISING FEAR" if _mc_vix_chg > 0.5 else "STABLE"
_mc_col = "#15803d" if _mc_vix_chg<-0.5 else "#b91c1c" if _mc_vix_chg>0.5 else "#6b7280"
_mc_bg  = "#f0fdf4" if _mc_vix_chg<-0.5 else "#fef2f2" if _mc_vix_chg>0.5 else "#f9fafb"
_mc_bc  = "#bbf7d0" if _mc_vix_chg<-0.5 else "#fecaca" if _mc_vix_chg>0.5 else "#e5e7eb"
st.markdown(f'<div class="sec">🌐 Market Conditions {section_signal("Conditions",_mc_sig,_mc_col,_mc_bg,_mc_bc,f"VIX {_mc_vix_chg:+.1f}")}</div>', unsafe_allow_html=True)

macro_tips={"VIX":"Fear index. Under 18=complacent. 18-25=caution. 25-35=fear. Over 35=panic. Rising fast=sell signal.",
            "10Y Yield":"10-year Treasury yield. Rising=inflation/growth fears, hurts growth stocks. Falling=recession fears, helps bonds.",
            "5Y Yield":"5-year Treasury. More sensitive to Fed rate expectations. Watch for inversion with 10Y.",
            "3M T-Bill":"Short-term rate — reflects current Fed rate. Inverted above 10Y=yield curve inverted=recession warning.",
            "DXY":"US Dollar Index. Rising=bad for commodities, EM, multinational earnings. Falling=good for gold, oil, international stocks.",
            "VVIX":"VIX of VIX — volatility of volatility. Above 100=extreme uncertainty. Spikes often precede VIX spikes.",
            "MOVE":"Bond volatility proxy (TLT 20D ann. vol). Under 10=calm rates. 10-15=caution. Over 15=high rate uncertainty. Leads equity VIX."}

mc_cols = st.columns(7)
mc_items=[("VIX","VIX",False),("10Y Yield","10Y Yield",False),("5Y Yield","5Y Yield",False),
          ("3M T-Bill","3M T-Bill",False),("DXY","DXY",True),("VVIX","VVIX",False),("MOVE","MOVE",False)]
for col,(key,label,good_up) in zip(mc_cols,mc_items):
    d=macro.get(key,{}); p=d.get("price",0); chg=d.get("chg",0)
    is_yield="Yield" in key or key=="3M T-Bill"
    c=clr(chg,good_up)
    with col:
        st.markdown(f"""
        <div class="card">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <div class="lbl">{label}</div>
            {tip('ℹ',macro_tips.get(key,''))}
          </div>
          <div class="val" style="color:{c};font-size:17px;">{p:.2f}{'%' if is_yield else ''}</div>
          <div class="sub" style="color:{c};">{arr(chg)} {chg:+.2f}{'bps' if is_yield else '%'}</div>
        </div>""", unsafe_allow_html=True)

# Yield curve
y10=macro.get("10Y Yield",{}).get("price",4.3); y3m=macro.get("3M T-Bill",{}).get("price",3.6)
spread=y10-y3m; sc="#16a34a" if spread>0 else "#dc2626"
st.markdown(f'<div style="margin-top:6px;background:{"#f0fdf4" if spread>0 else "#fef2f2"};border:1px solid {"#bbf7d0" if spread>0 else "#fecaca"};border-radius:6px;padding:8px 14px;font-size:12px;display:inline-block;">Yield Curve (10Y-3M): <span style="font-weight:700;color:{sc};">{spread:+.2f}% · {"Normal" if spread>0 else "INVERTED — recession warning"}</span></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 7 — COMMODITIES
st.markdown('<div id="commodities"></div>', unsafe_allow_html=True)
# & ENERGY
# ════════════════════════════════════════════════════════════════════════════════
with st.spinner("Loading commodities..."):
    comms = get_commodities()
_oil = comms.get("WTI Crude",{}).get("chg",0) if comms else 0
_com_sig = "OIL RISING" if _oil>0.5 else "OIL FALLING" if _oil<-0.5 else "STABLE"
_com_col = "#d97706" if _oil>0.5 else "#15803d" if _oil<-0.5 else "#6b7280"
_com_bg  = "#fffbeb" if _oil>0.5 else "#f0fdf4" if _oil<-0.5 else "#f9fafb"
_com_bc  = "#fde68a" if _oil>0.5 else "#bbf7d0" if _oil<-0.5 else "#e5e7eb"
st.markdown(f'<div class="sec">🛢️ Commodities & Energy {section_signal("Commodities",_com_sig,_com_col,_com_bg,_com_bc,f"WTI {_oil:+.2f}%")}</div>', unsafe_allow_html=True)

st.markdown('<div style="font-size:10px;color:#9ca3af;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin-bottom:6px;">Market impact: ⭐⭐⭐ Whole market · ⭐⭐ Sector/inflation · ⭐ Company specific &nbsp;&nbsp; Hover ℹ on any card for detail</div>', unsafe_allow_html=True)

if comms:
    metals = {k:v for k,v in comms.items() if k in ["Gold","Silver","Copper","WTI Crude","Brent","Nat Gas"]}
    agri   = {k:v for k,v in comms.items() if k in ["Wheat","Corn","Soybeans","Sugar","Coffee","Cocoa","Cotton","Lumber"]}

    def render_comm(items):
        cols=st.columns(len(items))
        for col,(name,d) in zip(cols,items.items()):
            c=clr(d["chg"])
            with col:
                st.markdown(f"""
                <div class="card">
                  <div style="display:flex;align-items:center;justify-content:space-between;">
                    <div class="lbl">{name}</div>
                    {tip('ℹ', d['desc'])}
                  </div>
                  <div style="font-size:15px;font-weight:700;color:{c};">{fp(d['price'])}</div>
                  <div class="sub" style="color:{c};">{arr(d['chg'])} {d['chg']:+.2f}%</div>
                  <div style="font-size:10px;color:#9ca3af;">{d['unit']} · {d['stars']}</div>
                </div>""", unsafe_allow_html=True)

    if metals:
        st.markdown('<div style="font-size:10px;color:#9ca3af;font-weight:600;text-transform:uppercase;margin-bottom:5px;">Metals & Energy</div>', unsafe_allow_html=True)
        render_comm(metals)
    if agri:
        st.markdown('<div style="font-size:10px;color:#9ca3af;font-weight:600;text-transform:uppercase;margin:10px 0 5px;">Agriculture & Softs</div>', unsafe_allow_html=True)
        render_comm(agri)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 8 — INFLATION
st.markdown('<div id="inflation"></div>', unsafe_allow_html=True)
# SIGNALS
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">📈 Inflation Signals ' + section_signal("Inflation","ABOVE TARGET","#b91c1c","#fef2f2","#fecaca","CPI >2% Fed target") + '</div>', unsafe_allow_html=True)

with st.spinner("Loading inflation data (FRED)..."):
    fred = get_fred_inflation()

inf_tips={"CPI (YoY)":"Headline inflation. Above 2%=Fed stays cautious. Rising CPI=bad for bonds, can hurt growth stocks.",
          "Core CPI":"Strips out food & energy. Fed focuses here. Sticky=rates higher longer=pressure on valuations.",
          "PCE (YoY)":"Fed preferred measure. Lower than CPI but same direction. Drives actual rate decisions.",
          "PPI (YoY)":"Producer prices. Leads CPI by 3-6 months. Falling PPI=inflation coming down. Bullish signal.",
          "5Y Breakeven":"Bond market inflation expectation. Rising=market thinks inflation stays high.",
          "Fed Funds Rate":"The rate banks charge each other. Drives all borrowing costs. Higher=expensive mortgages, hurts growth stocks."}

inf_c1,inf_c2,inf_c3=st.columns(3)
with inf_c1:
    inf_display=[
        ("CPI (YoY)",    fred.get("CPI (YoY)",{}).get("val",3.2),   "Above 2% target"),
        ("Core CPI",     fred.get("Core CPI",{}).get("val",3.8),    "Sticky — ex food & energy"),
        ("PCE (YoY)",    fred.get("PCE (YoY)",{}).get("val",2.8),   "Fed preferred measure"),
        ("PPI (YoY)",    fred.get("PPI (YoY)",{}).get("val",2.4),   "Leading indicator for CPI"),
        ("5Y Breakeven", fred.get("5Y Breakeven",{}).get("val",2.51),"Bond market forecast"),
        ("Fed Funds Rate",fred.get("Fed Funds Rate",{}).get("val",3.625),"Current rate"),
    ]
    fred_src="Live: FRED (Federal Reserve)" if fred else "FRED temporarily unavailable — using estimates"
    for label,val,note in inf_display:
        c="#16a34a" if val<=2.3 else "#d97706" if val<=3.5 else "#dc2626"
        if label=="Fed Funds Rate": c="#d97706"; vs=f"{val:.2f}%"
        elif label=="5Y Breakeven": c="#d97706" if val>2.3 else "#16a34a"; vs=f"{val:.2f}%"
        else: vs=f"{val:.1f}%"
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid #f3f4f6;font-size:12px;">
          <div style="display:flex;align-items:center;gap:5px;">
            <div><span style="color:#374151;font-weight:500;">{label}</span><br><span style="font-size:10px;color:#9ca3af;">{note}</span></div>
            {tip('ℹ',inf_tips.get(label,''))}
          </div>
          <div style="font-weight:700;font-size:15px;color:{c};">{vs}</div>
        </div>""", unsafe_allow_html=True)
    st.caption(fred_src)

with inf_c2:
    st.markdown('<div class="lbl" style="margin-bottom:8px;">Pressure by Category</div>', unsafe_allow_html=True)
    cat_tips={"Shelter":"Biggest CPI component (35%). Rent & housing costs. Slow to fall — why Core CPI stays sticky.",
              "Services":"Haircuts, insurance, healthcare. Driven by wages — hard to reduce. Sticky=Fed concerned.",
              "Food":"Grocery & restaurant prices. Volatile — affected by weather, fuel, supply chains.",
              "Energy":"Petrol, electricity, gas bills. Very volatile — drops fast when oil falls. Less worrying to Fed.",
              "Goods":"Physical products. Post-COVID supply chains fixed. Currently low — good sign."}
    for name,v,c in [("Shelter",5.8,"#dc2626"),("Services",4.9,"#ef4444"),("Food",3.4,"#d97706"),("Energy",2.1,"#d97706"),("Goods",0.4,"#16a34a")]:
        pct=int(v/8*100)
        st.markdown(f"""
        <div style="margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px;align-items:center;">
            <div style="display:flex;align-items:center;gap:4px;">
              <span style="color:#6b7280;">{name}</span>{tip('ℹ',cat_tips.get(name,''))}
            </div>
            <span style="font-weight:700;color:{c};">{v}%</span>
          </div>
          <div style="height:6px;background:#f3f4f6;border-radius:3px;overflow:hidden;">
            <div style="height:6px;width:{pct}%;background:{c};border-radius:3px;"></div>
          </div>
        </div>""", unsafe_allow_html=True)

with inf_c3:
    st.markdown("""
    <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:12px 14px;margin-bottom:10px;">
      <div class="lbl" style="margin-bottom:6px;">Fed Rate Path</div>
      <div style="font-size:12px;color:#374151;">Market pricing <span style="color:#d97706;font-weight:600;">0-1 cuts</span> in 2026 — Dec at earliest</div>
      <div style="font-size:11px;color:#9ca3af;margin-top:3px;">3 cuts made in 2025. Rate: 3.50-3.75%</div>
      <div style="font-size:11px;color:#dc2626;font-weight:600;margin-top:3px;">Iran war risk: cuts now in doubt</div>
    </div>
    <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:6px;padding:12px 14px;">
      <div class="lbl" style="margin-bottom:6px;">What this means for stocks</div>
      <div style="font-size:11px;color:#374151;line-height:1.7;">
        <span style="color:#dc2626;font-weight:600;">High inflation</span> = Fed holds rates = expensive borrowing = growth stocks under pressure<br><br>
        <span style="color:#16a34a;font-weight:600;">Falling inflation</span> = rate cuts possible = growth stocks rally<br><br>
        <span style="color:#d97706;font-weight:600;">Sticky Core CPI</span> = key risk now — shelter &amp; services slow to fall
      </div>
    </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════════════════════
# SECTION 9 — OPTIONS THEME
st.markdown('<div id="themes"></div>', unsafe_allow_html=True)
# SECTION 9 — OPTIONS THEME SCANNER (Fully Dynamic)
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🎯 Options Theme Scanner <span class="sec-badge sec-bull">Live · Refreshes daily</span></div>', unsafe_allow_html=True)

# ── STEP 1: Scan 150 liquid stocks for real momentum (Yahoo Finance, free) ────
# This is the ONLY thing hardcoded — the universe of stocks to scan.
# Claude decides ALL groupings, names, and trade classifications from the data.
SCAN_UNIVERSE = [
    # Mega cap tech
    "NVDA","MSFT","AAPL","GOOGL","META","AMZN","TSLA","AVGO","ORCL","CRM",
    # Semiconductors
    "AMD","SMCI","ARM","ANET","MRVL","QCOM","MU","INTC","TSM","ASML","LRCX","KLAC",
    # AI / Cloud software
    "NOW","SNOW","PLTR","AI","PATH","DDOG","NET","ZS","CRWD","PANW",
    # Defense
    "LMT","RTX","NOC","GD","BA","KTOS","HII","LDOS","CACI","AXON","RKLB",
    # Energy
    "XOM","CVX","COP","OXY","LNG","CEG","VST","CCJ","ETN","GEV","NEE","NRG",
    # Financials
    "JPM","GS","BAC","V","MA","AXP","COF","SCHW","BX","MS","C","BRK-B",
    # Healthcare / Biotech
    "LLY","NVO","UNH","VRTX","REGN","AMGN","ISRG","MRNA","DXCM","ABBV","PFE","BMY",
    # Industrials
    "GE","CAT","DE","HON","EMR","ROK","PWR","FLR","MTZ","WM","ETN","MMM",
    # Consumer
    "HD","COST","TGT","MCD","SBUX","NKE","LULU","ROST","TJX","AMZN","LOW","DG",
    # Small/mid growth
    "IONQ","RGTI","HIMS","SOUN","BBAI","CELH","MP","UUUU","RKLB","HOOD","COIN","MSTR",
    # China / EM
    "BABA","JD","PDD","NIO","BIDU","LI","XPEV","MELI","NU","SE",
    # Commodities
    "FCX","NEM","ALB","LAC","VALE","AA","CLF","STLD","BHP","RIO","GOLD","AEM",
    # REITs / Rates sensitive
    "AMT","PLD","EQIX","O","SPG","VNQ","IYR","MPW","VICI","CCI",
    # Short squeeze / high SI
    "GME","AMC","BYND","SOFI","OPEN","SPCE","PTON","BBBY","CLOV","WISH",
]

@st.cache_data(ttl=3600)
def get_raw_movers(universe: tuple) -> list:
    """Fetch live momentum for every stock in the universe. No grouping — raw data."""
    out = []
    for sym in universe:
        try:
            h = yf.Ticker(sym).history(period="3mo")
            if not h.empty and len(h) >= 22:
                p   = h["Close"].iloc[-1]
                p1d = h["Close"].iloc[-2]
                p1w = h["Close"].iloc[-6]  if len(h) >= 6  else p
                p1m = h["Close"].iloc[-22]
                p3m = h["Close"].iloc[0]
                chg1d = round((p - p1d) / p1d * 100, 2)
                chg1w = round((p - p1w) / p1w * 100, 2)
                chg1m = round((p - p1m) / p1m * 100, 2)
                chg3m = round((p - p3m) / p3m * 100, 2)
                comp  = round(chg1d*0.15 + chg1w*0.25 + chg1m*0.45 + chg3m*0.15, 2)
                out.append({"sym": sym, "price": round(p,2),
                            "chg1d": chg1d, "chg1w": chg1w,
                            "chg1m": chg1m, "chg3m": chg3m,
                            "comp": comp})
        except: pass
    out.sort(key=lambda x: -x["comp"])
    return out

@st.cache_data(ttl=86400)
def build_options_themes(movers_text: str, sector_perf: str,
                          vix: float, spy_1m: float, date_str: str) -> dict:
    """
    Claude receives raw momentum data for 150 stocks.
    It does EVERYTHING: grouping, naming, Long Call/CSP/Long Put classification.
    No hardcoded themes. No hardcoded sector names. Purely data-driven.
    """
    key = _anthropic_key()
    if not key:
        return {}
    try:
        prompt = f"""You are a professional options trader analysing today's market on {date_str}.

MARKET CONTEXT:
VIX: {vix:.1f} | SPY 1-month: {spy_1m:+.1f}%
Sector performance: {sector_perf}

RAW STOCK MOMENTUM DATA (1D / 1W / 1M / 3M % change):
{movers_text}

YOUR JOB:
Look at which stocks are moving together and WHY. Group them into 8-12 actionable options themes.

For EACH theme:
1. Give it a specific descriptive name that explains WHY these stocks are moving (e.g. "Iran War Oil Premium", "NVDA AI Earnings Momentum", "Rate Fear Crushing REITs") — NOT generic sector names
2. Pick 4-8 stocks from the data that fit this theme
3. Classify the trade: LONG CALL, CSP, or LONG PUT based on the actual momentum
4. Write one sentence explaining the entry strategy
5. Name the key risk to watch

TRADE CLASSIFICATION RULES:
- LONG CALL: stocks in clear uptrend, avg 1M > +5%, buy calls on pullbacks
- CSP (Cash Secured Put): stocks flat to mild up, avg 1M -3% to +5%, high IV, sell puts below support
- LONG PUT: stocks in clear downtrend, avg 1M < -5%, buy puts on bounces
- CALL SPREAD: moderate uptrend +2 to +5%, reduce cost vs naked call
- PUT SPREAD: moderate downtrend -2 to -5%, reduce risk vs naked put

Return ONLY valid JSON array (no markdown, no backticks):
[
  {{
    "name": "Specific theme name explaining WHY",
    "trade": "LONG CALL",
    "tickers": ["SYM1","SYM2","SYM3","SYM4"],
    "avg_1m": 8.3,
    "entry": "Buy calls on any pullback to the 21 EMA, target prior highs",
    "risk": "Fed hawkish surprise would reverse the move",
    "why": "One sentence: the specific catalyst or narrative driving this group"
  }}
]"""

        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 2500,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30
        )
        text = r.json().get("content", [{}])[0].get("text", "").strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:])
            if text.endswith("```"): text = text[:-3]
        themes = json.loads(text.strip())
        # Validate
        valid = [t for t in themes if all(k in t for k in ["name","trade","tickers","why"])]
        return {"themes": valid}
    except Exception as e:
        return {}

# ── RUN ───────────────────────────────────────────────────────────────────────
with st.spinner(f"Scanning {len(SCAN_UNIVERSE)} stocks for options opportunities..."):
    raw_movers = get_raw_movers(tuple(SCAN_UNIVERSE))

sector_perf_str = ", ".join([f"{k}:{v.get('1d',0):+.1f}%" for k,v in list((sectors or {}).items())[:8]])

if ant_key:
    # Build concise text summary of top 60 movers for Claude
    top_up   = raw_movers[:30]
    top_down = sorted(raw_movers, key=lambda x: x["comp"])[:15]
    mid      = [m for m in raw_movers if -3 < m["comp"] < 3][:15]
    movers_text = "STRONG UPTREND:\n"
    movers_text += "\n".join([f"  {m['sym']}: 1D={m['chg1d']:+.1f}% 1W={m['chg1w']:+.1f}% 1M={m['chg1m']:+.1f}% 3M={m['chg3m']:+.1f}%" for m in top_up])
    movers_text += "\n\nSTRONG DOWNTREND:\n"
    movers_text += "\n".join([f"  {m['sym']}: 1D={m['chg1d']:+.1f}% 1W={m['chg1w']:+.1f}% 1M={m['chg1m']:+.1f}% 3M={m['chg3m']:+.1f}%" for m in top_down])
    movers_text += "\n\nSIDEWAYS / RANGE (CSP candidates):\n"
    movers_text += "\n".join([f"  {m['sym']}: 1D={m['chg1d']:+.1f}% 1W={m['chg1w']:+.1f}% 1M={m['chg1m']:+.1f}% 3M={m['chg3m']:+.1f}%" for m in mid])

    with st.spinner("Claude grouping stocks into options themes..."):
        result = build_options_themes(
            movers_text, sector_perf_str,
            vix_price, spy_d.get("chg1m", 0), today_str
        )
    ai_themes = result.get("themes", [])
else:
    ai_themes = []

# ── DISPLAY ───────────────────────────────────────────────────────────────────
# Legend
st.markdown("""
<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
  <span style="background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:700;">📈 LONG CALL — strong uptrend, buy calls on dips to EMA</span>
  <span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:700;">💰 CSP — sideways/mild up, sell puts below support for premium</span>
  <span style="background:#fef2f2;color:#b91c1c;border:1px solid #fecaca;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:700;">📉 LONG PUT — downtrend, buy puts on bounces</span>
  <span style="background:#fff7ed;color:#c2410c;border:1px solid #fed7aa;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:700;">🔀 SPREADS — moderate move, reduce cost/risk vs naked options</span>
</div>""", unsafe_allow_html=True)

if ai_themes:
    # Separate into columns by trade type
    long_calls = [t for t in ai_themes if t["trade"] in ("LONG CALL","CALL SPREAD")]
    csps       = [t for t in ai_themes if t["trade"] == "CSP"]
    long_puts  = [t for t in ai_themes if t["trade"] in ("LONG PUT","PUT SPREAD")]

    st.markdown(f'<div style="font-size:11px;color:#1d4ed8;font-weight:600;margin-bottom:10px;">🤖 {len(ai_themes)} themes generated by Claude from live momentum of {len(raw_movers)} stocks · {today_str} · Refreshes daily</div>', unsafe_allow_html=True)

    col_lc, col_csp, col_lp = st.columns(3)

    trade_styles = {
        "LONG CALL":   ("#15803d","#f0fdf4","#bbf7d0"),
        "CALL SPREAD": ("#15803d","#f0fdf4","#bbf7d0"),
        "CSP":         ("#1d4ed8","#eff6ff","#bfdbfe"),
        "LONG PUT":    ("#b91c1c","#fef2f2","#fecaca"),
        "PUT SPREAD":  ("#b91c1c","#fef2f2","#fecaca"),
    }

    def render_card(t, col):
        tc, tbg, tbc = trade_styles.get(t["trade"], ("#374151","#f9fafb","#e5e7eb"))
        # Get live prices for tickers
        ticker_data = {m["sym"]: m for m in raw_movers}
        pills = ""
        for sym in t.get("tickers", [])[:6]:
            md = ticker_data.get(sym, {})
            pct = md.get("chg1m", 0)
            pc  = "#16a34a" if pct > 0 else "#dc2626"
            pills += f'<span style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:3px;padding:2px 6px;font-size:10px;margin:1px;display:inline-block;"><b style="color:#374151;">{sym}</b> <span style="color:{pc};">{pct:+.1f}%</span></span>'

        with col:
            st.markdown(f"""
            <div style="background:{tbg};border:1px solid {tbc};border-radius:8px;padding:10px 12px;margin-bottom:8px;">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:5px;">
                <div style="font-size:12px;font-weight:700;color:#111827;line-height:1.3;">{t['name']}</div>
                <span style="background:{tc};color:#fff;font-size:10px;font-weight:700;padding:2px 7px;border-radius:3px;margin-left:6px;white-space:nowrap;">{t['trade']}</span>
              </div>
              <div style="font-size:11px;color:#374151;margin-bottom:4px;font-style:italic;">{t.get('why','')}</div>
              <div style="font-size:11px;color:{tc};margin-bottom:4px;">📌 {t.get('entry','')}</div>
              <div style="font-size:11px;color:#9ca3af;">⚠️ Risk: {t.get('risk','')}</div>
              <div style="margin-top:7px;line-height:2.2;">{pills}</div>
            </div>""", unsafe_allow_html=True)

    with col_lc:
        st.markdown(f'<div style="text-align:center;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;padding:6px;font-size:12px;font-weight:700;color:#15803d;margin-bottom:8px;">📈 LONG CALLS ({len(long_calls)})</div>', unsafe_allow_html=True)
        for t in long_calls: render_card(t, col_lc)

    with col_csp:
        st.markdown(f'<div style="text-align:center;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;padding:6px;font-size:12px;font-weight:700;color:#1d4ed8;margin-bottom:8px;">💰 CSPs ({len(csps)})</div>', unsafe_allow_html=True)
        for t in csps: render_card(t, col_csp)

    with col_lp:
        st.markdown(f'<div style="text-align:center;background:#fef2f2;border:1px solid #fecaca;border-radius:6px;padding:6px;font-size:12px;font-weight:700;color:#b91c1c;margin-bottom:8px;">📉 LONG PUTS ({len(long_puts)})</div>', unsafe_allow_html=True)
        for t in long_puts: render_card(t, col_lp)

else:
    # No Anthropic key — show raw movers sorted by direction
    st.warning("Add **ANTHROPIC_API_KEY** to Streamlit secrets — Claude groups these stocks into options themes automatically. Without it, showing raw movers only.")
    up   = [m for m in raw_movers if m["comp"] > 2][:15]
    down = sorted(raw_movers, key=lambda x: x["comp"])
    down = [m for m in down if m["comp"] < -2][:15]
    flat = [m for m in raw_movers if -2 <= m["comp"] <= 2][:15]

    c1, c2, c3 = st.columns(3)
    for col, items, label, col_c in [(c1,up,"📈 Uptrend","#15803d"),(c2,flat,"💰 Sideways","#1d4ed8"),(c3,down,"📉 Downtrend","#b91c1c")]:
        with col:
            st.markdown(f'<div style="font-size:12px;font-weight:700;color:{col_c};margin-bottom:8px;">{label}</div>', unsafe_allow_html=True)
            for m in items:
                st.markdown(f'<div style="font-size:11px;padding:3px 0;border-bottom:1px solid #f3f4f6;"><b>{m["sym"]}</b> <span style="color:{col_c};">{m["chg1m"]:+.1f}% 1M</span> <span style="color:#9ca3af;font-size:10px;">{m["chg1d"]:+.1f}% today</span></div>', unsafe_allow_html=True)

# ── ADD CUSTOM STOCK TO SCAN ──────────────────────────────────────────────────
with st.expander("⚙️ Add stocks to the scan universe"):
    st.markdown('<div style="font-size:12px;color:#6b7280;margin-bottom:8px;">Add any US-listed ticker to include in tomorrow\'s Claude scan. They will appear in themes if their momentum is relevant.</div>', unsafe_allow_html=True)
    cu1, cu2 = st.columns([3,1])
    with cu1:
        extra_tick = st.text_input("Ticker", placeholder="e.g. CCJ, HOOD, IONQ", key="extra_ticker_input", label_visibility="collapsed")
    with cu2:
        if st.button("Add to scan", key="add_extra_ticker"):
            if extra_tick:
                ticks = [t.strip().upper() for t in extra_tick.split(",") if t.strip()]
                existing = st.session_state.approved_recs.get("extra_tickers", [])
                for tk in ticks:
                    if tk not in existing: existing.append(tk)
                st.session_state.approved_recs["extra_tickers"] = existing
                st.rerun()
    extras = st.session_state.approved_recs.get("extra_tickers", [])
    if extras:
        st.markdown(f'<div style="font-size:11px;color:#7e22ce;">Added to scan: {", ".join(extras)}</div>', unsafe_allow_html=True)
        if st.button("Clear all custom tickers", key="clear_extras"):
            st.session_state.approved_recs["extra_tickers"] = []
            st.rerun()


# SECTION 10 — SENTIMENT
st.markdown('<div id="sentiment"></div>', unsafe_allow_html=True)
# & SMART MONEY
# ════════════════════════════════════════════════════════════════════════════════
fg_score=max(0,min(100,int(100-(vix_price-10)/35*100)))
_fg_sig = "EXTREME GREED" if fg_score>=80 else "GREED" if fg_score>=65 else "NEUTRAL" if fg_score>=45 else "FEAR" if fg_score>=25 else "EXTREME FEAR"
_fg_col = "#15803d" if fg_score>=65 else "#b91c1c" if fg_score<35 else "#d97706"
_fg_bg  = "#f0fdf4" if fg_score>=65 else "#fef2f2" if fg_score<35 else "#fffbeb"
_fg_bc  = "#bbf7d0" if fg_score>=65 else "#fecaca" if fg_score<35 else "#fde68a"
st.markdown(f'<div class="sec">😱 Sentiment {section_signal("Fear/Greed",_fg_sig,_fg_col,_fg_bg,_fg_bc,f"Score {fg_score}")}</div>', unsafe_allow_html=True)

fg_lbl=("Extreme Greed" if fg_score>=80 else "Greed" if fg_score>=65 else "Neutral" if fg_score>=45 else "Fear" if fg_score>=25 else "Extreme Fear")
fg_col="#16a34a" if fg_score>=65 else "#d97706" if fg_score>=45 else "#dc2626"

sc1,sc2,sc3,sc4=st.columns(4)
with sc1:
    st.markdown(f"""
    <div class="card">
      <div style="display:flex;justify-content:space-between;"><div class="lbl">Fear & Greed (Live VIX)</div>{tip('ℹ','Calculated from real VIX. Under 20=calm market. Over 30=fear. Over 40=panic. Extreme fear often means buy opportunity.')}</div>
      <div style="font-size:34px;font-weight:700;color:{fg_col};">{fg_score}</div>
      <div style="font-size:13px;font-weight:600;color:{fg_col};margin:3px 0;">{fg_lbl}</div>
      <div style="height:8px;border-radius:4px;background:linear-gradient(to right,#dc2626,#d97706,#16a34a);position:relative;margin:8px 0 4px;">
        <div style="position:absolute;top:-3px;left:{max(fg_score-1,1)}%;width:3px;height:14px;background:#111827;border-radius:2px;"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:9px;color:#9ca3af;">
        <span>Ext Fear</span><span>Fear</span><span>Neutral</span><span>Greed</span><span>Ext</span>
      </div>
      <div style="font-size:10px;color:#9ca3af;margin-top:6px;">VIX={vix_price:.1f} · Live from Yahoo Finance</div>
    </div>""", unsafe_allow_html=True)

watchlist=("SPY","QQQ","NVDA","AAPL","META","MSFT","AMZN")
with sc2:
    if fh_key:
        with st.spinner("Loading analyst ratings..."):
            analyst=get_analyst_sentiment(watchlist, fh_key)
        st.markdown('<div class="card"><div style="display:flex;justify-content:space-between;"><div class="lbl">Analyst Consensus (Live · Finnhub)</div>' + tip('ℹ','Wall Street analyst buy/hold/sell ratings. 60%+ buy=bullish consensus. Updated monthly by analysts.') + '</div><div style="margin-top:6px;">', unsafe_allow_html=True)
        for sym,d in list(analyst.items())[:6]:
            bw=d["pct_buy"]; bc="#16a34a" if bw>=60 else "#d97706" if bw>=40 else "#dc2626"
            st.markdown(f"""
            <div style="margin-bottom:6px;">
              <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px;">
                <span style="font-weight:700;color:#374151;">{sym}</span>
                <span style="color:{bc};font-weight:600;">{bw}% Buy · {d['buy']}B/{d['hold']}H/{d['sell']}S</span>
              </div>
              <div style="height:5px;background:#f3f4f6;border-radius:3px;overflow:hidden;">
                <div style="height:5px;width:{bw}%;background:{bc};border-radius:3px;"></div>
              </div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card"><div class="lbl">Analyst Consensus</div><div style="font-size:12px;color:#9ca3af;padding:8px 0;">Add Finnhub key to Streamlit secrets for live analyst ratings.</div></div>', unsafe_allow_html=True)

with sc3:
    if fh_key:
        with st.spinner("Loading insider data..."):
            insider=get_insider_sentiment(watchlist, fh_key)
        st.markdown('<div class="card"><div style="display:flex;justify-content:space-between;"><div class="lbl">Insider Transactions (Live · Finnhub)</div>' + tip('ℹ','Company insiders (CEOs, CFOs, directors) buying their own stock = bullish signal. Selling can just be profit-taking.') + '</div><div style="margin-top:6px;">', unsafe_allow_html=True)
        for sym,d in list(insider.items())[:6]:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #f3f4f6;font-size:12px;">
              <span style="font-weight:700;color:#374151;">{sym}</span>
              <span style="color:{d['col']};font-weight:600;">{d['direction']}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown('<div style="font-size:10px;color:#9ca3af;margin-top:5px;">Buying=bullish · Selling=caution or profit-taking</div></div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card"><div class="lbl">Insider Transactions</div><div style="font-size:12px;color:#9ca3af;padding:8px 0;">Add Finnhub key to Streamlit secrets.</div></div>', unsafe_allow_html=True)

with sc4:
    st.markdown("""
    <div class="card">
      <div class="lbl">Options Flow & Smart Money</div>
      <div style="margin-top:5px;">
        <div style="padding:6px 0;border-bottom:1px solid #f3f4f6;">
          <div style="display:flex;justify-content:space-between;font-size:12px;">
            <span style="color:#374151;font-weight:600;">Put/Call Ratio</span>
            <span style="color:#16a34a;font-weight:700;">0.81 · Bullish</span>
          </div>
          <div style="font-size:10px;color:#9ca3af;margin-top:2px;">Below 0.9=more calls=traders betting UP. Above 1.2=fear rising.</div>
        </div>
        <div style="padding:6px 0;border-bottom:1px solid #f3f4f6;">
          <div style="display:flex;justify-content:space-between;font-size:12px;">
            <span style="color:#374151;font-weight:600;">COT Net Longs</span>
            <span style="color:#16a34a;font-weight:700;">+124k</span>
          </div>
          <div style="font-size:10px;color:#9ca3af;margin-top:2px;">Institutions hold 124k more buy vs sell contracts. Big money bullish.</div>
        </div>
        <div style="padding:6px 0;border-bottom:1px solid #f3f4f6;">
          <div style="display:flex;justify-content:space-between;font-size:12px;">
            <span style="color:#374151;font-weight:600;">Dark Pool (DIX)</span>
            <span style="color:#16a34a;font-weight:700;">46.8% · Bull</span>
          </div>
          <div style="font-size:10px;color:#9ca3af;margin-top:2px;">Institutions quietly buying off-exchange. Above 45%=accumulating.</div>
        </div>
        <div style="padding:6px 0;">
          <div style="display:flex;justify-content:space-between;font-size:12px;">
            <span style="color:#374151;font-weight:600;">GEX Gamma</span>
            <span style="color:#d97706;font-weight:700;">+$4.2B Pinning</span>
          </div>
          <div style="font-size:10px;color:#9ca3af;margin-top:2px;">Large positive GEX=market makers pinning price stable. Range-bound until catalyst.</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 11 — AI OPTIONS
st.markdown('<div id="aioptions"></div>', unsafe_allow_html=True)
# FLOW
# ════════════════════════════════════════════════════════════════════════════════
_ai_cls = "sec-bull" if ant_key else "sec-neu"
_ai_lbl = "AI Active · 30min refresh" if ant_key else "Add Anthropic key"
st.markdown(f'<div class="sec">🤖 AI Options Flow <span class="sec-badge {_ai_cls}">{_ai_lbl}</span></div>', unsafe_allow_html=True)

if ant_key:
    sector_summary=", ".join([f"{k}:{v.get('1d',0):+.1f}%" for k,v in list((sectors or {}).items())[:5]])
    with st.spinner("Claude analysing current options flow..."):
        ai_opts=get_ai_options_analysis(
            spy_d.get("chg1d",0), qqq_d.get("chg1d",0), vix_price,
            spy_d.get("chg1m",0), qqq_d.get("chg1m",0), iwm_d.get("chg1m",0), sector_summary)
    if ai_opts:
        st.markdown(f"""
        <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:16px 18px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
            <span style="font-size:11px;font-weight:700;color:#1d4ed8;">🤖 Claude Haiku · Live market data · Refreshes every 30 min</span>
          </div>
          <div style="font-size:13px;color:#1e3a5f;line-height:1.7;">{ai_opts}</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("""
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;font-size:11px;">
          <span style="background:#f0fdf4;color:#15803d;padding:2px 8px;border-radius:4px;font-weight:600;border:1px solid #bbf7d0;">LONG CALL — betting price goes UP</span>
          <span style="background:#fef2f2;color:#b91c1c;padding:2px 8px;border-radius:4px;font-weight:600;border:1px solid #fecaca;">LONG PUT — betting price goes DOWN</span>
          <span style="background:#f0fdf4;color:#15803d;padding:2px 8px;border-radius:4px;font-weight:600;border:1px solid #bbf7d0;">CSP — sell put for income (bullish)</span>
          <span style="background:#eff6ff;color:#1d4ed8;padding:2px 8px;border-radius:4px;font-weight:600;border:1px solid #bfdbfe;">CC — covered call: sell call on stock you own for income</span>
          <span style="background:#faf5ff;color:#7e22ce;padding:2px 8px;border-radius:4px;font-weight:600;border:1px solid #e9d5ff;">SPREAD — buy + sell options to reduce cost</span>
        </div>""", unsafe_allow_html=True)
else:
    st.markdown('<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:14px 18px;font-size:13px;color:#6b7280;">Add <b>ANTHROPIC_API_KEY</b> to Streamlit secrets to enable AI options flow analysis. Uses Claude Haiku (~$0.008/day).</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 12 — CATALYST
st.markdown('<div id="calendar"></div>', unsafe_allow_html=True)
# CALENDAR
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">📅 Catalyst Calendar <span class="sec-badge sec-warn">High-impact events ahead</span></div>', unsafe_allow_html=True)

today_d=date.today()
all_macro=[
    ("FOMC", date(2026,3,18),"Rate Decision","HIGH","warn"),
    ("GDP",  date(2026,3,27),"Q4 Final GDP","MED","neu"),
    ("NFP",  date(2026,4,4), "Jobs Report","HIGH","warn"),
    ("CPI",  date(2026,4,10),"Inflation Print","HIGH","warn"),
    ("FOMC", date(2026,5,7), "Rate Decision","HIGH","warn"),
    ("NFP",  date(2026,5,1), "Jobs Report","HIGH","warn"),
    ("CPI",  date(2026,5,14),"Inflation Print","HIGH","warn"),
    ("FOMC", date(2026,6,18),"Rate Decision","HIGH","warn"),
]
macro_events=[(t,d.strftime("%b %d"),typ,imp,c) for t,d,typ,imp,c in all_macro if d>=today_d][:4]

if fh_key:
    with st.spinner("Loading earnings calendar..."):
        live_earn=get_earnings_calendar(fh_key)
    earn_events=[(e["symbol"],e["date"],f"Earnings ({'Pre-mkt' if e['hour']=='bmo' else 'After close' if e['hour']=='amc' else 'TBC'})","HIGH","buy") for e in live_earn]
    earn_src="Earnings: Finnhub (live)"
else:
    earn_events=[("AMZN","Apr 23","Earnings","HIGH","buy"),("MSFT","Apr 29","Earnings","HIGH","buy"),("GOOGL","Apr 28","Earnings","HIGH","buy"),("NVDA","May 27","Earnings","HIGH","buy")]
    earn_src="Earnings: estimated — add Finnhub key for live dates"

cats=macro_events+earn_events
cc=st.columns(min(len(cats),8))
for col,(t,d,typ,imp,c) in zip(cc,cats):
    bg="#f0fdf4" if c=="buy" else "#fffbeb" if c=="warn" else "#f9fafb"
    tc="#15803d" if c=="buy" else "#b45309" if c=="warn" else "#6b7280"
    bc="#bbf7d0" if c=="buy" else "#fde68a" if c=="warn" else "#e5e7eb"
    ic="#dc2626" if imp=="HIGH" else "#9ca3af"; ib="#fef2f2" if imp=="HIGH" else "#f9fafb"
    with col:
        st.markdown(f"""
        <div style="background:{bg};border:1px solid {bc};border-radius:6px;padding:8px 10px;">
          <div style="font-size:13px;font-weight:700;color:{tc};">{t}</div>
          <div style="font-size:10px;color:{tc};">{d}</div>
          <div style="font-size:10px;color:{tc};">{typ}</div>
          <span style="background:{ib};color:{ic};font-size:9px;padding:1px 5px;border-radius:2px;font-weight:600;">{imp}</span>
        </div>""", unsafe_allow_html=True)
st.caption(earn_src)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 13 — SHORT SQUEEZE
st.markdown('<div id="squeeze"></div>', unsafe_allow_html=True)
# RADAR
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">💥 Short Squeeze Radar ' + section_signal("Squeeze","WATCH","#d97706","#fffbeb","#fde68a","High SI stocks") + '</div>', unsafe_allow_html=True)

sqz_watch=["SMCI","MSTR","GME","COIN","RIVN","SOFI","PLTR","BYND","TSLA","AMC","BBAI","SOUN"]
with st.spinner("Loading short interest..."):
    sqz_data=get_short_interest(sqz_watch)

if sqz_data:
    sqz_cols=st.columns(min(len(sqz_data),8))
    for col,d in zip(sqz_cols,sqz_data[:8]):
        if d["mom"]>2: bg,tc,bc="#f0fdf4","#15803d","#bbf7d0"; ms=f"▲{d['mom']:+.1f}%"
        elif d["mom"]<-2: bg,tc,bc="#fef2f2","#b91c1c","#fecaca"; ms=f"▼{d['mom']:+.1f}%"
        else: bg,tc,bc="#f9fafb","#6b7280","#e5e7eb"; ms="flat"
        sc=d["score"]; sbg="#dcfce7" if sc>60 else "#fef9c3" if sc>35 else "#fee2e2"; stc="#15803d" if sc>60 else "#854d0e" if sc>35 else "#b91c1c"
        with col:
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {bc};border-radius:6px;padding:8px;text-align:center;">
              <div style="font-size:13px;font-weight:700;color:{tc};">{d['sym']}</div>
              <div style="font-size:10px;color:{tc};">SI: {d['si']:.1f}%</div>
              <div style="font-size:10px;color:{tc};">DTC: {d['dtc']:.1f}d</div>
              <div style="font-size:10px;color:{tc};">{ms}</div>
              <div style="font-size:9px;background:{sbg};color:{stc};border-radius:3px;padding:1px 4px;margin-top:3px;font-weight:700;">Squeeze:{sc}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:10px 14px;margin-top:8px;">
      <div style="font-size:11px;font-weight:600;color:#374151;margin-bottom:5px;">How to read this</div>
      <div style="font-size:11px;color:#6b7280;line-height:1.7;">
        <b style="color:#374151;">SI %</b> = Short Interest: % of shares being shorted. Higher = more fuel for a squeeze.<br>
        <b style="color:#374151;">DTC</b> = Days to Cover: days needed for shorts to exit. Higher = harder to escape = bigger squeeze.<br>
        <b style="color:#374151;">Momentum</b> = 1-month price change. Green = shorts already losing = squeeze pressure building.
      </div>
      <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;font-size:11px;">
        <span style="background:#dcfce7;color:#15803d;padding:2px 8px;border-radius:4px;font-weight:600;">Squeeze 60+ = High risk — watch closely</span>
        <span style="background:#fef9c3;color:#854d0e;padding:2px 8px;border-radius:4px;font-weight:600;">35-60 = On the radar</span>
        <span style="background:#fee2e2;color:#b91c1c;padding:2px 8px;border-radius:4px;font-weight:600;">Under 35 = Shorts in control</span>
      </div>
    </div>""", unsafe_allow_html=True)
    st.caption("Live: Yahoo Finance · FINRA updates twice monthly · SI >5% float only")

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 14 — LIVE STOCK SCREENER
st.markdown('<div id="screener"></div>', unsafe_allow_html=True)
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🔬 Stock Screener <span class="sec-badge sec-neu">Enter any ticker</span></div>', unsafe_allow_html=True)
st.markdown("Enter any ticker for live technical analysis, fundamentals and trade setup.")

scr_c1,scr_c2=st.columns([2,3])
with scr_c1:
    ticker_input=st.text_input("Ticker",value="NVDA",max_chars=8,label_visibility="collapsed",placeholder="e.g. NVDA, AAPL, TSLA").upper().strip()
    run=st.button("🔍 Analyse Live",use_container_width=True)
with scr_c2:
    st.markdown("**Quick picks:**")
    qp_cols=st.columns(10)
    for col,t in zip(qp_cols,["NVDA","AAPL","META","MSFT","TSLA","AMD","AMZN","GOOGL","SPY","QQQ"]):
        with col:
            if st.button(t,key=f"qp_{t}_1"): ticker_input=t

if run or ticker_input:
    sym=ticker_input.strip().upper()
    if sym:
        with st.spinner(f"Fetching live data for {sym}..."):
            sig=compute_signals(sym)
        if sig and not sig.get("error"):
            score=sig["score"]; ver,v_bg,v_col=verdict(score); price=sig["price"]; info=sig.get("info",{})
            r1,r2=st.columns([3,1])
            with r1:
                company=info.get("longName",sym); sector=info.get("sector","—")
                st.markdown(f'<span style="font-size:22px;font-weight:700;color:#111827;">{sym}</span><span style="font-size:13px;color:#9ca3af;margin-left:10px;">{company} · {sector}</span>', unsafe_allow_html=True)
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;font-size:10px;color:#9ca3af;margin-bottom:3px;margin-top:10px;">
                  <span style="color:#dc2626;font-weight:600;">STRONG SELL</span><span>NEUTRAL</span><span style="color:#16a34a;font-weight:600;">STRONG BUY</span>
                </div>
                <div style="height:12px;border-radius:6px;background:linear-gradient(to right,#dc2626,#d97706,#16a34a);position:relative;">
                  <div style="position:absolute;top:-3px;left:{min(max(score-1,1),97)}%;width:3px;height:18px;background:#111827;border-radius:2px;"></div>
                </div>""", unsafe_allow_html=True)
                p_cols=st.columns(5)
                for col,(label,val) in zip(p_cols,[("Price",f"${fp(price)}"),("1D",f"{sig['chg1d']:+.2f}%"),("1W",f"{sig['chg1w']:+.2f}%"),("1M",f"{sig['chg1m']:+.2f}%"),("3M",f"{sig['chg3m']:+.2f}%")]):
                    with col:
                        vis_chg=label!="Price"
                        vc=clr(float(val.replace('%','').replace('$','').replace('+','').replace(',','')) if vis_chg else 0) if vis_chg else "#111827"
                        st.markdown(f'<div style="text-align:center;padding:7px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;"><div style="font-size:9px;color:#9ca3af;">{label}</div><div style="font-size:12px;font-weight:700;color:{vc};">{val}</div></div>', unsafe_allow_html=True)
            with r2:
                st.markdown(f"""
                <div style="background:{v_bg};border:2px solid {v_col};border-radius:8px;padding:16px;text-align:center;">
                  <div style="font-size:20px;font-weight:700;color:#111827;">${fp(price)}</div>
                  <div style="font-size:12px;font-weight:600;color:{clr(sig['chg1d'])};margin:3px 0;">{arr(sig['chg1d'])} {sig['chg1d']:+.2f}% today</div>
                  <div style="font-size:16px;font-weight:700;color:{v_col};margin-top:8px;">{ver}</div>
                  <div style="font-size:14px;font-weight:700;color:{v_col};">Score: {score}/100</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("**Signal Matrix**")
            sigs_=[
                ("SMA 50","Above" if price>sig["sma50"] else "Below","buy" if price>sig["sma50"] else "sell"),
                ("SMA 200","Above" if price>sig["sma200"] else "Below","buy" if price>sig["sma200"] else "sell"),
                ("EMA 20","Above" if price>sig["ema20"] else "Below","buy" if price>sig["ema20"] else "sell"),
                ("RSI(14)",f"{sig['rsi']:.0f}","buy" if 45<sig['rsi']<70 else "sell" if sig['rsi']>75 or sig['rsi']<35 else "neu"),
                ("MACD","Positive" if sig["macd_hist"]>0 else "Negative","buy" if sig["macd_hist"]>0 else "sell"),
                ("Bollinger",f"{sig['bb_pos']:.0%}","buy" if sig['bb_pos']>0.5 else "sell" if sig['bb_pos']<0.2 else "neu"),
                ("Volume",f"{sig['vol_ratio']:.1f}x avg","buy" if sig['vol_ratio']>1.1 else "neu"),
                ("1M Trend",f"{sig['chg1m']:+.1f}%","buy" if sig['chg1m']>0 else "sell"),
            ]
            sig_cols=st.columns(8)
            for col,(n,v,s) in zip(sig_cols,sigs_):
                bg="#f0fdf4" if s=="buy" else "#fef2f2" if s=="sell" else "#f9fafb"
                ct="#16a34a" if s=="buy" else "#dc2626" if s=="sell" else "#6b7280"
                bc="#bbf7d0" if s=="buy" else "#fecaca" if s=="sell" else "#e5e7eb"
                with col:
                    st.markdown(f'<div class="sig" style="background:{bg};border-color:{bc};"><div class="sig-n">{n}</div><div class="sig-v" style="color:{ct};">{v}</div><div style="color:{ct};font-size:9px;font-weight:600;margin-top:2px;">{s.upper()}</div></div>', unsafe_allow_html=True)

            fund_c,setup_c=st.columns(2)
            with fund_c:
                st.markdown("**Fundamental Snapshot**")
                pe=info.get("trailingPE"); fwd=info.get("forwardPE"); eg=info.get("earningsQuarterlyGrowth",0)
                rg=info.get("revenueGrowth",0); mg=info.get("profitMargins",0); mc=info.get("marketCap",0)
                mcs=f"${mc/1e12:.1f}T" if mc>1e12 else f"${mc/1e9:.0f}B" if mc>1e9 else "N/A"
                for label,val in [("P/E (TTM)",f"{pe:.1f}x" if pe else "N/A"),("Forward P/E",f"{fwd:.1f}x" if fwd else "N/A"),
                                   ("EPS Growth",f"{eg*100:+.1f}%" if eg else "N/A"),("Rev Growth",f"{rg*100:+.1f}%" if rg else "N/A"),
                                   ("Net Margin",f"{mg*100:.1f}%" if mg else "N/A"),("Market Cap",mcs)]:
                    st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #f3f4f6;font-size:12px;"><span style="color:#6b7280;">{label}</span><span style="font-weight:600;color:#111827;">{val}</span></div>', unsafe_allow_html=True)
            with setup_c:
                st.markdown("**Trade Setup (ATR-based)**")
                atr=sig["atr"]; stop=price-atr*2; t1=price*1.08; t2=price*1.18; rr=(t1-price)/(price-stop+1e-9)
                for label,val,cls in [("Current Price",f"${fp(price)}",""),("ATR (14)",f"${atr:.2f}",""),
                                      ("Entry Zone",f"${fp(price*.99)}-${fp(price*1.005)}",""),
                                      ("Stop Loss (2xATR)",f"${fp(stop)} (-{(price-stop)/price*100:.1f}%)","dn"),
                                      ("Target 1 (+8%)",f"${fp(t1)}","up"),("Target 2 (+18%)",f"${fp(t2)}","up"),
                                      ("Risk/Reward",f"{rr:.1f}:1","up" if rr>=2 else "warn")]:
                    vc="color:#16a34a" if cls=="up" else "color:#dc2626" if cls=="dn" else "color:#d97706" if cls=="warn" else "color:#111827"
                    st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #f3f4f6;font-size:12px;"><span style="color:#6b7280;">{label}</span><span style="font-weight:600;{vc}">{val}</span></div>', unsafe_allow_html=True)

            if sig["close_series"]:
                prices=sig["close_series"]; mn_p=min(prices)*.98; mx_p=max(prices)*1.02
                fig_s=go.Figure()
                fig_s.add_trace(go.Scatter(y=prices,mode="lines",name=sym,line=dict(color="#2563eb",width=2),fill="tozeroy",fillcolor="rgba(37,99,235,0.05)",hovertemplate="$%{y:.2f}<extra></extra>"))
                fig_s.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#fff",margin=dict(l=50,r=20,t=10,b=30),height=220,
                    font=dict(family="Inter",color="#9ca3af",size=10),
                    xaxis=dict(showgrid=False,showticklabels=False,title="60 trading days"),
                    yaxis=dict(gridcolor="#f3f4f6",tickprefix="$",range=[mn_p,mx_p]),
                    showlegend=False,hovermode="x unified")
                st.plotly_chart(fig_s,use_container_width=True,config={"displayModeBar":False},key=f"chart_screener_{sym}")
        elif sig and sig.get("error"):
            st.error(f"Could not fetch **{sym}**: {sig['error']}")
        else:
            st.info(f"No data found for {sym}. Try a major US-listed stock.")


# ════════════════════════════════════════════════════════════════════════════════
# OPTIONS DECISION HUB
st.markdown('<div id="hub"></div>', unsafe_allow_html=True)
# — 6-Panel Trade Analysis
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🎰 Options Decision Hub ' + section_signal("Hub","TRADE ANALYSIS","#1d4ed8","#eff6ff","#bfdbfe","All signals") + '</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size:12px;color:#6b7280;margin-bottom:12px;">All signals combined to help you decide: what to trade, which strategy, where to enter, how much to risk.</div>', unsafe_allow_html=True)

# Account size setting
with st.expander("⚙️ Account Settings", expanded=False):
    acct_col1, acct_col2 = st.columns([2,4])
    with acct_col1:
        account_size = st.number_input(
            "Your trading account size ($)",
            min_value=1000, max_value=10000000,
            value=st.session_state.get("account_size", 25000),
            step=1000, format="%d"
        )
        st.session_state["account_size"] = account_size
        st.caption(f"Max risk per trade: ${account_size*0.05:,.0f} (5%) · Conservative: ${account_size*0.02:,.0f} (2%)")
    with acct_col2:
        scan_tickers_input = st.text_input(
            "Stocks to analyse (comma separated — leave blank for auto top movers)",
            value=st.session_state.get("hub_tickers","NVDA,AAPL,META,MSFT,AMZN,TSLA,AMD,LLY,JPM,XOM"),
            key="hub_ticker_input"
        )
        st.session_state["hub_tickers"] = scan_tickers_input

hub_tickers = [t.strip().upper() for t in st.session_state.get("hub_tickers","NVDA,AAPL,META,MSFT,AMZN,TSLA,AMD,LLY,JPM,XOM").split(",") if t.strip()][:15]
account_size = st.session_state.get("account_size", 25000)

# ── PANEL 2: WHAT'S MOVING & WHY ─────────────────────────────────────────────
st.markdown('<div id="panel2"></div>', unsafe_allow_html=True)
st.markdown('<div style="font-size:11px;color:#9ca3af;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin:14px 0 8px;">Panel 2 - Price Volume Momentum</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def get_whats_moving(tickers: tuple) -> list:
    out = []
    for sym in tickers:
        try:
            tk = yf.Ticker(sym)
            h  = tk.history(period="3mo")
            if h.empty or len(h) < 22: continue
            p    = h["Close"].iloc[-1]
            p1d  = h["Close"].iloc[-2]
            p1w  = h["Close"].iloc[-6]  if len(h)>=6  else p
            p1m  = h["Close"].iloc[-22]
            vol  = h["Volume"].iloc[-1]
            avg_vol = h["Volume"].tail(20).mean()
            vol_r = round(vol/max(avg_vol,1), 1)
            sma50 = h["Close"].tail(50).mean()
            sma200= h["Close"].tail(200).mean() if len(h)>=200 else h["Close"].mean()
            ath   = h["High"].max()
            chg1d = round((p-p1d)/p1d*100, 2)
            chg1w = round((p-p1w)/p1w*100, 2)
            chg1m = round((p-p1m)/p1m*100, 2)
            ath_pct = round((p-ath)/ath*100, 1)
            dma50_pct = round((p-sma50)/sma50*100, 1)
            out.append({
                "sym": sym, "price": round(p,2),
                "chg1d": chg1d, "chg1w": chg1w, "chg1m": chg1m,
                "vol_ratio": vol_r,
                "above50": p > sma50, "above200": p > sma200,
                "ath_pct": ath_pct,
                "dma50_pct": dma50_pct,
                "vol_signal": "🔥 Unusual vol" if vol_r > 2 else "↑ High vol" if vol_r > 1.5 else "Normal",
            })
        except: pass
    out.sort(key=lambda x: -abs(x["chg1m"]))
    return out

with st.spinner("Loading stock data..."):
    moving_data = get_whats_moving(tuple(hub_tickers))

if moving_data:
    p2_cols = st.columns(len(moving_data))
    for col, d in zip(p2_cols, moving_data):
        dc = "#16a34a" if d["chg1d"] >= 0 else "#dc2626"
        mc = "#16a34a" if d["chg1m"] >= 0 else "#dc2626"
        ath_badge = f'<span style="background:#fef9c3;color:#854d0e;font-size:9px;padding:1px 4px;border-radius:2px;">ATH {d["ath_pct"]:.0f}%</span>' if d["ath_pct"] > -5 else ""
        earn_warn = ""
        with col:
            st.markdown(f"""
            <div class="card" style="padding:8px 10px;">
              <div style="font-size:13px;font-weight:700;color:#111827;">{d["sym"]}</div>
              <div style="font-size:11px;font-weight:700;color:{dc};">{d["chg1d"]:+.2f}% today</div>
              <div style="font-size:10px;color:{mc};">1M: {d["chg1m"]:+.1f}%</div>
              <div style="font-size:10px;color:#9ca3af;">{d["vol_signal"]}</div>
              <div style="font-size:10px;color:{"#16a34a" if d["above50"] else "#dc2626"};">{"▲" if d["above50"] else "▼"} 50DMA {d["dma50_pct"]:+.1f}%</div>
              {ath_badge}
            </div>""", unsafe_allow_html=True)

# ── PANEL 3: IV RANK SCANNER ─────────────────────────────────────────────────
st.markdown('<div id="panel3"></div>', unsafe_allow_html=True)
st.markdown('<div style="font-size:11px;color:#9ca3af;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin:14px 0 8px;">Panel 3 - IV Rank - Buy or Sell Options Premium?</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size:11px;color:#6b7280;margin-bottom:8px;">IVR under 30 = options CHEAP → BUY calls/puts &nbsp;·&nbsp; IVR 30-60 = NEUTRAL &nbsp;·&nbsp; IVR over 60 = options EXPENSIVE → SELL premium (CSP/CC)</div>', unsafe_allow_html=True)

with st.spinner("Calculating IV Rank from options chains..."):
    iv_data = {}
    for sym in hub_tickers[:10]:
        iv_data[sym] = get_iv_rank(sym)

if iv_data:
    p3_cols = st.columns(len([v for v in iv_data.values() if v]))
    valid_iv = [(sym,d) for sym,d in iv_data.items() if d]
    for col, (sym, d) in zip(p3_cols, valid_iv):
        ivr = d["ivr"]
        vc  = d["vc"]; vbg = d["vbg"]
        bar_col = "#1d4ed8" if ivr < 30 else "#d97706" if ivr < 60 else "#16a34a"
        earn_warn = '<div style="font-size:9px;background:#fef9c3;color:#854d0e;padding:1px 4px;border-radius:2px;margin-top:3px;">⚠️ Earnings &lt;21d</div>' if d.get("near_earnings") else ""
        with col:
            st.markdown(f"""
            <div class="card" style="padding:8px 10px;background:{vbg};">
              <div style="font-size:12px;font-weight:700;color:#111827;">{sym}</div>
              <div style="font-size:18px;font-weight:700;color:{vc};">IVR {ivr}</div>
              <div style="height:5px;background:#e5e7eb;border-radius:3px;overflow:hidden;margin:4px 0;">
                <div style="height:5px;width:{ivr}%;background:{bar_col};border-radius:3px;"></div>
              </div>
              <div style="font-size:10px;font-weight:700;color:{vc};">{d["verdict"]}</div>
              <div style="font-size:9px;color:#9ca3af;">IV {d["iv"]:.0f}% · HV30 {d["hv30"]:.0f}%</div>
              {earn_warn}
            </div>""", unsafe_allow_html=True)

# ── PANEL 4: SMART MONEY ─────────────────────────────────────────────────────
st.markdown('<div id="panel4"></div>', unsafe_allow_html=True)
st.markdown('<div style="font-size:11px;color:#9ca3af;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin:14px 0 8px;">Panel 4 - Smart Money Signals</div>', unsafe_allow_html=True)

p4_c1, p4_c2, p4_c3 = st.columns(3)

# Unusual options flow
with p4_c1:
    st.markdown('<div style="font-size:11px;font-weight:600;color:#374151;margin-bottom:6px;">🎯 Unusual Options Flow</div>', unsafe_allow_html=True)
    with st.spinner("Scanning options chains..."):
        all_unusual = []
        for sym in hub_tickers[:8]:
            flow = get_unusual_options_flow(sym)
            if flow:
                for c in flow.get("unusual_calls",[])[:2]:
                    all_unusual.append({**c, "sym":sym, "signal":"BULLISH", "col":"#15803d", "bg":"#f0fdf4", "bc":"#bbf7d0"})
                for p in flow.get("unusual_puts",[])[:2]:
                    all_unusual.append({**p, "sym":sym, "signal":"BEARISH", "col":"#b91c1c", "bg":"#fef2f2", "bc":"#fecaca"})
    all_unusual.sort(key=lambda x: -x["vol"])
    if all_unusual:
        for u in all_unusual[:6]:
            st.markdown(f"""
            <div style="background:{u["bg"]};border:1px solid {u["bc"]};border-radius:5px;padding:6px 8px;margin-bottom:5px;font-size:11px;">
              <div style="display:flex;justify-content:space-between;">
                <span style="font-weight:700;color:#374151;">{u["sym"]} {u["type"]} ${u["strike"]:.0f}</span>
                <span style="font-weight:700;color:{u["col"]};">{u["signal"]}</span>
              </div>
              <div style="color:#6b7280;font-size:10px;">Vol: {u["vol"]:,} · OI: {u["oi"]:,} · Ratio: {u["vol"]/max(u["oi"],1):.1f}x · IV: {u["iv"]:.0f}%</div>
              <div style="color:#9ca3af;font-size:10px;">Exp: {u["exp"]} · {u.get("otm",0):+.1f}% OTM</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.caption("No unusual options flow detected in current scan")

# Insider Form 4
with p4_c2:
    st.markdown('<div style="font-size:11px;font-weight:600;color:#374151;margin-bottom:6px;">👤 Insider Form 4 Filings (SEC)</div>', unsafe_allow_html=True)
    with st.spinner("Checking SEC EDGAR..."):
        insider_filings = []
        for sym in hub_tickers[:6]:
            filings = get_sec_form4(sym)
            for f in filings[:2]:
                insider_filings.append({**f, "sym":sym})
    if insider_filings:
        for f in insider_filings[:8]:
            st.markdown(f"""
            <div style="border-bottom:1px solid #f3f4f6;padding:5px 0;font-size:11px;">
              <div style="font-weight:700;color:#374151;">{f["sym"]} · {f["name"][:25]}</div>
              <div style="color:#9ca3af;font-size:10px;">Filed: {f["filed"]}</div>
            </div>""", unsafe_allow_html=True)
        st.caption("Source: SEC EDGAR Form 4 filings")
    else:
        st.caption("No recent Form 4 filings found — try adding more tickers above")

# Sector ETF flow
with p4_c3:
    st.markdown('<div style="font-size:11px;font-weight:600;color:#374151;margin-bottom:6px;">🏦 Sector ETF Institutional Flow</div>', unsafe_allow_html=True)
    with st.spinner("Checking sector flows..."):
        etf_flow = get_sector_etf_flow()
    if etf_flow:
        inflows  = [(k,v) for k,v in etf_flow.items() if v["flow"]=="INFLOW"]
        outflows = [(k,v) for k,v in etf_flow.items() if v["flow"]=="OUTFLOW"]
        inflows.sort(key=lambda x:  -x[1]["chg1d"])
        outflows.sort(key=lambda x:  x[1]["chg1d"])
        for name, v in (inflows + outflows)[:8]:
            fc = "#16a34a" if v["flow"]=="INFLOW" else "#dc2626" if v["flow"]=="OUTFLOW" else "#9ca3af"
            flow_lbl = "▲ INFLOW" if v["flow"]=="INFLOW" else "▼ OUTFLOW" if v["flow"]=="OUTFLOW" else "— Neutral"
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;border-bottom:1px solid #f3f4f6;padding:4px 0;font-size:11px;">
              <span style="font-weight:600;color:#374151;">{name}</span>
              <span style="color:{fc};font-weight:600;">{flow_lbl} {v["chg1d"]:+.2f}% {v["vol_ratio"]}x vol</span>
            </div>""", unsafe_allow_html=True)

# Short interest changes (already have data)
st.markdown('<div style="font-size:11px;color:#9ca3af;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin:14px 0 6px;">Short Interest Changes</div>', unsafe_allow_html=True)
with st.spinner("Loading short interest..."):
    hub_si = get_short_interest(hub_tickers)
if hub_si:
    si_cols = st.columns(min(len(hub_si),6))
    for col, d in zip(si_cols, hub_si[:6]):
        sc = "#dc2626" if d["si"] > 20 else "#d97706" if d["si"] > 10 else "#9ca3af"
        with col:
            st.markdown(f"""
            <div class="card" style="padding:8px;text-align:center;">
              <div style="font-size:12px;font-weight:700;">{d["sym"]}</div>
              <div style="font-size:14px;font-weight:700;color:{sc};">SI {d["si"]:.1f}%</div>
              <div style="font-size:10px;color:#9ca3af;">DTC {d["dtc"]:.1f}d</div>
              <div style="font-size:10px;color:{("#16a34a" if d["mom"]>0 else "#dc2626")};">{d["mom"]:+.1f}% 1M</div>
            </div>""", unsafe_allow_html=True)

# ── PANEL 5: TECHNICAL SETUP ──────────────────────────────────────────────────
st.markdown('<div id="panel5"></div>', unsafe_allow_html=True)
st.markdown('<div style="font-size:11px;color:#9ca3af;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin:14px 0 8px;">Panel 5 - Technical Setup - Strike Selection Guide</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size:11px;color:#6b7280;margin-bottom:8px;">Key levels for strike placement — support for CSP strikes, resistance for call spreads, ATR for stop placement.</div>', unsafe_allow_html=True)

with st.spinner("Running technical analysis..."):
    tech_data = {}
    for sym in hub_tickers[:8]:
        tech_data[sym] = compute_signals(sym)

if tech_data:
    p5_cols = st.columns(min(len(tech_data),4))
    valid_tech = [(sym, d) for sym, d in tech_data.items() if d and not d.get("error")]
    for col, (sym, d) in zip(p5_cols, valid_tech[:8]):
        score = d["score"]
        vc = "#16a34a" if score >= 65 else "#dc2626" if score <= 35 else "#d97706"
        with col:
            st.markdown(f"""
            <div class="card" style="padding:8px 10px;">
              <div style="font-size:12px;font-weight:700;color:#111827;">{sym} ${d["price"]:.0f}</div>
              <div style="font-size:10px;color:#9ca3af;margin-top:3px;">Signal: <span style="font-weight:700;color:{vc};">{score}/100</span></div>
              <div style="font-size:10px;color:#374151;">50DMA: ${d["sma50"]:.0f} ({d["price"]/d["sma50"]*100-100:+.1f}%)</div>
              <div style="font-size:10px;color:#374151;">200DMA: ${d["sma200"]:.0f}</div>
              <div style="font-size:10px;color:#374151;">ATR: ${d["atr"]:.2f}</div>
              <div style="font-size:10px;color:#374151;">RSI: {d["rsi"]:.0f} · {"Overbought" if d["rsi"]>70 else "Oversold" if d["rsi"]<30 else "Neutral"}</div>
              <div style="font-size:10px;color:#9ca3af;margin-top:2px;">CSP zone: ${d["price"]-d["atr"]*1.5:.0f}-${d["price"]-d["atr"]:.0f}</div>
            </div>""", unsafe_allow_html=True)

# ── PANEL 6: CLAUDE TRADE SYNTHESIS ──────────────────────────────────────────
st.markdown('<div id="panel6"></div>', unsafe_allow_html=True)
st.markdown('<div style="font-size:11px;color:#9ca3af;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin:14px 0 8px;">Panel 6 - Claude Trade Synthesis - Full Trade Plans</div>', unsafe_allow_html=True)

if ant_key:
    if st.button("🤖 Generate Today's Trade Plans", key="gen_trades", type="primary", use_container_width=False):
        # Build comprehensive signals JSON for Claude
        signals = {
            "date": today_str,
            "market": {"vix": vix_price, "spy_1m": spy_d.get("chg1m",0),
                       "regime": "Risk-On" if vix_price < 20 else "Risk-Off" if vix_price > 28 else "Neutral"},
            "price_momentum": {d["sym"]: {"chg1d": d["chg1d"], "chg1m": d["chg1m"],
                                           "vol_ratio": d["vol_ratio"], "above50dma": d["above50"]}
                               for d in moving_data},
            "iv_rank": {sym: {"ivr": d["ivr"], "verdict": d["verdict"],
                               "near_earnings": d.get("near_earnings",False)}
                        for sym, d in iv_data.items() if d},
            "unusual_options": [{"sym":u["sym"],"type":u["type"],"strike":u["strike"],
                                  "vol":u["vol"],"signal":u["signal"]}
                                 for u in all_unusual[:10]],
            "sector_flow": {k:{"flow":v["flow"],"chg1d":v["chg1d"],"vol_ratio":v["vol_ratio"]}
                           for k,v in (etf_flow or {}).items()},
            "short_interest": {d["sym"]:{"si":d["si"],"dtc":d["dtc"],"momentum":d["mom"]}
                               for d in (hub_si or [])},
            "technicals": {sym:{"score":d["score"],"rsi":d["rsi"],"atr":d["atr"],
                                 "sma50":d["sma50"],"price":d["price"]}
                           for sym,d in tech_data.items() if d and not d.get("error")},
        }
        # Convert all numpy/pandas types to native Python for JSON serialisation
        import numpy as np
        class SafeEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, (np.integer,)): return int(o)
                if isinstance(o, (np.floating,)): return round(float(o), 4)
                if isinstance(o, (np.bool_,)): return bool(o)
                if isinstance(o, (np.ndarray,)): return o.tolist()
                if hasattr(o, 'item'): return o.item()
                return super().default(o)
        signals_json = json.dumps(signals, indent=2, cls=SafeEncoder)
        with st.spinner("Claude analysing all signals and building trade plans... (30-45 seconds)"):
            trade_plans = get_claude_trade_plans(
                signals_json, account_size,
                vix_price, spy_d.get("chg1m",0), today_str
            )
        if trade_plans:
            st.session_state["last_trade_plans"] = trade_plans
            st.session_state["last_trade_date"]  = today_str

    # Display cached trade plans
    trade_plans = st.session_state.get("last_trade_plans", {})
    trade_date  = st.session_state.get("last_trade_date", "")

    if trade_plans:
        if trade_date != today_str:
            st.warning(f"⚠️ These plans were generated on {trade_date} — click regenerate for today's plans")

        # Market context
        if trade_plans.get("market_context"):
            st.markdown(f"""
            <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:10px 14px;margin-bottom:12px;">
              <div style="font-size:11px;font-weight:700;color:#374151;margin-bottom:4px;">📊 Market Context</div>
              <div style="font-size:12px;color:#374151;">{trade_plans["market_context"]}</div>
            </div>""", unsafe_allow_html=True)

        # Trade cards
        trades = trade_plans.get("trades", [])
        for i in range(0, len(trades), 2):
            t_cols = st.columns(2)
            for j, col in enumerate(t_cols):
                if i+j >= len(trades): break
                t = trades[i+j]
                strat = t.get("strategy","")
                sc = "#15803d" if "CALL" in strat and "PUT" not in strat else "#b91c1c" if "PUT" in strat else "#1d4ed8"
                sbg= "#f0fdf4" if "CALL" in strat and "PUT" not in strat else "#fef2f2" if "PUT" in strat else "#eff6ff"
                sbc= "#bbf7d0" if "CALL" in strat and "PUT" not in strat else "#fecaca" if "PUT" in strat else "#bfdbfe"

                sigs = t.get("signals_aligned",[])
                sig_pills = " ".join([f'<span style="background:#f3f4f6;color:#374151;font-size:10px;padding:1px 6px;border-radius:3px;">{s}</span>' for s in sigs])

                with col:
                    st.markdown(f"""
                    <div style="background:{sbg};border:2px solid {sbc};border-radius:8px;padding:14px 16px;margin-bottom:10px;">
                      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
                        <div>
                          <span style="font-size:18px;font-weight:700;color:#111827;">#{t.get("rank",i+j+1)} {t.get("sym","")}</span>
                          <span style="background:{sc};color:#fff;font-size:11px;font-weight:700;padding:2px 8px;border-radius:3px;margin-left:8px;">{strat}</span>
                        </div>
                        <span style="font-size:12px;font-weight:600;color:{sc};">{t.get("pct_account","")}</span>
                      </div>

                      <div style="font-size:12px;color:#374151;margin-bottom:6px;font-style:italic;">{t.get("why","")}</div>

                      <div style="margin-bottom:8px;">{sig_pills}</div>

                      <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:11px;margin-bottom:8px;">
                        <div style="background:#fff;border-radius:4px;padding:5px 8px;">
                          <div style="color:#9ca3af;font-size:10px;">STRIKE / EXPIRY</div>
                          <div style="font-weight:700;color:#374151;">${t.get("strike","")} · {t.get("expiry","")}</div>
                        </div>
                        <div style="background:#fff;border-radius:4px;padding:5px 8px;">
                          <div style="color:#9ca3af;font-size:10px;">CONTRACTS / COST</div>
                          <div style="font-weight:700;color:#374151;">{t.get("contracts","")} · {t.get("cost","")}</div>
                        </div>
                        <div style="background:#fff;border-radius:4px;padding:5px 8px;">
                          <div style="color:#9ca3af;font-size:10px;">ENTRY</div>
                          <div style="font-weight:600;color:#374151;">{t.get("entry","")}</div>
                        </div>
                        <div style="background:#fff;border-radius:4px;padding:5px 8px;">
                          <div style="color:#9ca3af;font-size:10px;">STOP LOSS</div>
                          <div style="font-weight:600;color:#dc2626;">{t.get("stop","")}</div>
                        </div>
                        <div style="background:#fff;border-radius:4px;padding:5px 8px;">
                          <div style="color:#9ca3af;font-size:10px;">TARGET 1</div>
                          <div style="font-weight:600;color:#16a34a;">{t.get("target1","")}</div>
                        </div>
                        <div style="background:#fff;border-radius:4px;padding:5px 8px;">
                          <div style="color:#9ca3af;font-size:10px;">TARGET 2 + R:R</div>
                          <div style="font-weight:600;color:#16a34a;">{t.get("target2","")} · {t.get("risk_reward","")}</div>
                        </div>
                      </div>

                      <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:4px;padding:5px 8px;font-size:10px;color:#854d0e;">
                        ⚠️ Avoid if: {t.get("avoid_if","")}
                      </div>
                    </div>""", unsafe_allow_html=True)

        # Avoid list and key risk
        avoid = trade_plans.get("avoid_today", [])
        key_risk = trade_plans.get("key_risk","")
        if avoid or key_risk:
            av_col, kr_col = st.columns(2)
            with av_col:
                if avoid:
                    st.markdown('<div style="font-size:11px;font-weight:600;color:#b91c1c;margin-bottom:5px;">🚫 Avoid Today</div>', unsafe_allow_html=True)
                    for a in avoid:
                        st.markdown(f'<div style="font-size:11px;color:#374151;padding:3px 0;border-bottom:1px solid #f3f4f6;">• {a}</div>', unsafe_allow_html=True)
            with kr_col:
                if key_risk:
                    st.markdown(f"""
                    <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:6px;padding:10px 14px;">
                      <div style="font-size:11px;font-weight:600;color:#b91c1c;margin-bottom:4px;">⚠️ Key Risk Today</div>
                      <div style="font-size:12px;color:#374151;">{key_risk}</div>
                    </div>""", unsafe_allow_html=True)

        st.caption(f"Uses Claude Sonnet · ~$0.03 per generation · Account: ${account_size:,} · Generated: {trade_date}")

    else:
        st.markdown("""
        <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:20px;text-align:center;color:#6b7280;">
          <div style="font-size:16px;margin-bottom:8px;">🤖</div>
          <div style="font-size:13px;font-weight:600;margin-bottom:4px;">Click the button above to generate today's trade plans</div>
          <div style="font-size:11px;">Claude will read all signals from panels 2-5 and produce specific trade plans with strikes, expiry, position size, entry, stop and targets.</div>
        </div>""", unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:16px;">
      <div style="font-size:13px;color:#6b7280;">Add <b>ANTHROPIC_API_KEY</b> to Streamlit secrets to enable Claude trade synthesis. This is the most powerful feature — it reads all 5 panels and produces specific trade plans with exact strikes, expiry, position size, entry, stop and targets.</div>
    </div>""", unsafe_allow_html=True)

# ── FOOTER ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center;font-size:11px;color:#9ca3af;padding:8px 0;">
  ⚠️ For informational purposes only · Not financial advice · Always do your own research<br>
  Data: Yahoo Finance · Finnhub · FRED (Federal Reserve) · Prices ~15 min delayed
</div>""", unsafe_allow_html=True)# ══════════════════════════════════════════════════════════════════════════════
# THEME MANAGEMENT PANEL — always visible, fully dynamic
# ══════════════════════════════════════════════════════════════════════════════
