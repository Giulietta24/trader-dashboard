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
                   layout="wide", initial_sidebar_state="collapsed")

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.block-container{padding:1rem 1.5rem 2rem;max-width:1600px;}
[data-testid="collapsedControl"]{display:none!important;}
section[data-testid="stSidebar"]{display:none!important;}
.sec{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
     color:#9ca3af;margin:1.4rem 0 .7rem;border-bottom:1px solid #e5e7eb;padding-bottom:5px;}
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
</style>
""", unsafe_allow_html=True)

# ── COLOUR HELPERS ─────────────────────────────────────────────────────────────
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
                      "above50":p>sma50,"spark":h["Close"].tail(30).tolist(),"hist":h}
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
        "HYG/LQD": ("HYG","LQD","Junk vs Inv Grade","Falling=credit stress building. Best leading recession indicator."),
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
                r_1w =h1["Close"].iloc[-6]/h2["Close"].iloc[-6] if len(h1)>=6 else r_now
                r_1m =h1["Close"].iloc[-22]/h2["Close"].iloc[-22] if len(h1)>=22 else r_now
                r_3m =h1["Close"].iloc[0]/h2["Close"].iloc[0]
                out[key]={"label":label,"desc":desc,
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

@st.cache_data(ttl=86400)
def get_daily_theme_intel(scores_summary,sector_perf,spy_1m,vix,date_str):
    key=_anthropic_key()
    if not key: return None
    try:
        prompt=f"""You are a senior market strategist. Review theme momentum data.
DATE:{date_str} SPY 1M:{spy_1m:+.1f}% VIX:{vix:.1f}
SECTORS:{sector_perf}
THEME SCORES:{scores_summary}

Return ONLY valid JSON (no markdown backticks):
{{"upgrades":[{{"name":"ThemeName","reason":"one sentence"}}],"downgrades":[{{"name":"ThemeName","reason":"one sentence"}}],"new_theme":{{"name":"Name","category":"hot","subsectors":["S1","S2"],"tickers":["T1","T2","T3","T4"],"desc":"One sentence.","reason":"Why now"}},"daily_note":"2-3 sentence market theme summary"}}
Set new_theme to null if nothing genuinely new. Only list upgrades/downgrades if something actually changed."""
        r=requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={"model":"claude-haiku-4-5-20251001","max_tokens":500,"messages":[{"role":"user","content":prompt}]},
            timeout=20)
        text=r.json().get("content",[{}])[0].get("text","").strip()
        return json.loads(text)
    except: return None

THEME_UNIVERSE={
    "hot":[
        {"name":"AI Infrastructure","subsectors":["Semiconductors","Data Centres","AI Power Grid","Networking"],"tickers":["NVDA","AMD","SMCI","AVGO","ARM","CEG","VST","DELL","ANET","MRVL"],"desc":"AI buildout driving demand for chips, servers, power and cooling."},
        {"name":"Defense & Aerospace","subsectors":["Weapons Systems","Cyber Defense","Space","NATO Rearmament"],"tickers":["LMT","RTX","NOC","BA","GD","PLTR","KTOS","HII","LDOS","L3H"],"desc":"Global rearmament cycle. NATO raising spend. Cyber threats driving software defense."},
        {"name":"Energy & Power Grid","subsectors":["Nuclear","LNG Exports","Grid Infrastructure","Natural Gas"],"tickers":["CEG","VST","CCJ","ETN","LNG","OKE","NEE","FSLR","GEV","NRG"],"desc":"AI power demand + energy security driving nuclear revival and grid upgrades."},
        {"name":"Reshoring & Industrials","subsectors":["Factory Automation","Construction","Machinery","Supply Chain"],"tickers":["GE","ETN","CAT","DE","HON","EMR","ROK","PWR","FLR","MTZ"],"desc":"US manufacturing returning home. Massive capex into factories and automation."},
        {"name":"Biotech & GLP-1","subsectors":["Obesity Drugs","Oncology","Gene Therapy","Medical Devices"],"tickers":["NVO","LLY","VRTX","REGN","AMGN","ISRG","DXCM","MRNA","EDIT","CRSP"],"desc":"GLP-1 obesity drugs reshaping pharma. Gene editing creating new categories."},
    ],
    "fading":[
        {"name":"ESG & Clean Energy","subsectors":["Solar","Wind","EV Charging","Carbon Credits"],"tickers":["ENPH","SEDG","RUN","PLUG","FCEL","BLNK","CHPT","NOVA","ARRY","BE"],"desc":"Policy headwinds, high rates hurting project financing. Solar oversupply from China."},
        {"name":"China Consumer","subsectors":["E-commerce","EV","Internet","Consumer Tech"],"tickers":["BABA","JD","PDD","NIO","BIDU","LI","XPEV","BILI","TME","IQ"],"desc":"Geopolitical risk, weak consumer confidence, regulatory pressure and earnings misses."},
        {"name":"Office REITs","subsectors":["Office Space","Commercial Property","Urban Core"],"tickers":["SLG","BXP","VNO","HIW","PDM","DEA","PGRE","OPI","ESRT","CXW"],"desc":"Structural shift to hybrid work. High vacancy rates. Rate sensitivity hurting valuations."},
        {"name":"Speculative Tech","subsectors":["Unprofitable Growth","SPACs","Meme Stocks"],"tickers":["SOFI","OPEN","CLOV","UWMC","SPCE","PTON","BARK","LAZR","OUST","VLDR"],"desc":"Rate-sensitive cash-burning companies. Higher for longer = capital dries up."},
    ],
    "emerging":[
        {"name":"Quantum Computing","subsectors":["Quantum Hardware","Quantum Software","Error Correction"],"tickers":["IONQ","RGTI","QUBT","IBM","GOOGL","MSFT","QBTS","ARQQ","HON","NVDA"],"desc":"Early-stage race for quantum supremacy. Hardware breakthroughs accelerating."},
        {"name":"Humanoid Robotics","subsectors":["Robot Hardware","AI Control Systems","Factory Automation"],"tickers":["TSLA","NVDA","ABB","HON","PATH","FANUC","KDLY","MTTR","AI","BRZE"],"desc":"Labor shortage + AI convergence. Tesla Optimus, Figure AI driving investor excitement."},
        {"name":"Rare Earths & Minerals","subsectors":["Lithium","Cobalt","Rare Earth Mining","Copper"],"tickers":["MP","UUUU","ALB","LAC","FCX","NEM","VALE","RIO","BHP","TECK"],"desc":"EV batteries, defense and chips all need critical minerals. Supply chains being secured."},
        {"name":"Longevity & Health Tech","subsectors":["Anti-aging","Diagnostics","Digital Health","Wearables"],"tickers":["ISRG","DXCM","TDOC","VEEV","HIMS","DOCS","NARI","OMCL","PHR","ACMR"],"desc":"Ageing demographics driving preventative health. AI diagnostics cutting costs."},
    ],
}

@st.cache_data(ttl=3600)
def compute_theme_momentum(universe):
    results={}
    for cat,themes in universe.items():
        results[cat]=[]
        for theme in themes:
            td=[]
            for sym in theme["tickers"][:6]:
                try:
                    h=yf.Ticker(sym).history(period="3mo")
                    if not h.empty and len(h)>=5:
                        p=h["Close"].iloc[-1]
                        w1=(p-h["Close"].iloc[-6])/h["Close"].iloc[-6]*100 if len(h)>=6 else 0
                        m1=(p-h["Close"].iloc[-22])/h["Close"].iloc[-22]*100 if len(h)>=22 else 0
                        m3=(p-h["Close"].iloc[0])/h["Close"].iloc[0]*100
                        wt=w1*.3+m1*.5+m3*.2
                        td.append({"sym":sym,"price":p,"chg1w":w1,"chg1m":m1,"chg3m":m3,"weighted":wt})
                except: pass
            if td:
                avg=sum(t["weighted"] for t in td)/len(td)
                score=max(0,min(100,int(50+avg*2)))
                td.sort(key=lambda x:-x["weighted"])
                results[cat].append({**theme,"score":score,"ticker_data":td,"avg_mom":avg})
            else:
                results[cat].append({**theme,"score":50,"ticker_data":[],"avg_mom":0})
        results[cat].sort(key=lambda x:-x["score"])
    return results

# ════════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════════════════════════
if "custom_tickers" not in st.session_state: st.session_state.custom_tickers={}
if "approved_recs"  not in st.session_state: st.session_state.approved_recs={}
if "heat_period"    not in st.session_state: st.session_state.heat_period="1d"

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

# ════════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════════
st.title("📊 Trader Intelligence Dashboard")
fh_key = _finnhub_key()
ant_key = _anthropic_key()
badge = '<span class="badge b-buy" style="font-size:12px;padding:5px 12px;">● REAL-TIME · FINNHUB</span>' if fh_key else '<span class="badge b-hold" style="font-size:12px;padding:5px 12px;">◐ 15-MIN DELAY · YFINANCE</span>'
ai_badge = '&nbsp;<span class="badge b-neu" style="font-size:12px;padding:5px 12px;">🤖 AI ACTIVE</span>' if ant_key else '&nbsp;<span class="badge b-sell" style="font-size:12px;padding:5px 12px;">⚠️ NO AI KEY</span>'
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:4px;">
  <span style="font-size:12px;color:#9ca3af;">Live market data · {datetime.now().strftime('%A %d %B %Y · %H:%M')} · Yahoo Finance + Finnhub + FRED</span>
  <div style="display:flex;gap:6px;align-items:center;">{badge}{ai_badge}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 1 — MARKET REGIME BAR
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🎯 Market Regime — Instant Read</div>', unsafe_allow_html=True)

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
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">📊 Index Comparison — Full Cap Size & Style Picture</div>', unsafe_allow_html=True)

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
                tlbl = "Above 50D" if d["above50"] else "Below 50D"
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
    st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar":False})

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
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 3 — CROSS-MARKET RELATIONSHIPS
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🔗 Cross-Market Relationships</div>', unsafe_allow_html=True)
cm_period = st.radio("Cross-market period", ["1W","1M","3M"], horizontal=True, label_visibility="collapsed", key="cm_period")

with st.spinner("Loading cross-market data..."):
    cross = get_cross_market()

if cross:
    cm_cols = st.columns(len(cross))
    for col,(key,d) in zip(cm_cols, cross.items()):
        period_key = {"1W":"chg_1w","1M":"chg_1m","3M":"chg_3m"}.get(cm_period,"chg_1m")
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
    st.caption("1-month ratio change · Green=first asset outperforming · Red=second asset outperforming · Hover ℹ for what it means")

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 4 — BREADTH & INTERNALS
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🩺 Market Breadth & Internals</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def get_breadth_extended():
    out = {}
    for sym, key in [("RSP","rsp"),("SPY","spy"),("HYG","hyg"),("LQD","lqd"),
                     ("TLT","tlt"),("IWM","iwm"),("XLK","xlk"),("XLP","xlp"),
                     ("GLD","gld"),("UUP","uup")]:
        try:
            h = yf.Ticker(sym).history(period="3mo")
            if not h.empty and len(h) >= 22:
                p=h["Close"].iloc[-1]; p1d=h["Close"].iloc[-2]
                p1m=h["Close"].iloc[-22]; p3m=h["Close"].iloc[0]
                out[key]={"price":round(p,2),"chg1d":round((p-p1d)/p1d*100,2),
                          "chg1m":round((p-p1m)/p1m*100,2)}
        except: pass
    if "rsp" in out and "spy" in out:
        out["breadth_1m"]=round(out["rsp"]["chg1m"]-out["spy"]["chg1m"],2)
    if "hyg" in out and "lqd" in out:
        out["credit_chg"]=round(out["hyg"]["chg1m"]-out["lqd"]["chg1m"],2)
    if "iwm" in out and "spy" in out:
        out["small_vs_large"]=round(out["iwm"]["chg1m"]-out["spy"]["chg1m"],2)
    if "xlp" in out and "xlk" in out:
        out["def_rotation"]=round(out["xlp"]["chg1m"]-out["xlk"]["chg1m"],2)
    if "gld" in out and "uup" in out:
        out["gold_vs_dollar"]=round(out["gld"]["chg1m"]-out["uup"]["chg1m"],2)
    return out

with st.spinner("Loading breadth data..."):
    bxt = get_breadth_extended()

bm = [
    ("RSP vs SPY (Breadth)",
     f"{bxt['breadth_1m']:+.2f}pp" if "breadth_1m" in bxt else "Loading...",
     clr(bxt.get("breadth_1m",0)),
     "RSP (equal weight) vs SPY (cap weight). Positive=ALL stocks rising=broad healthy rally. Negative=only mega caps moving=narrow market=warning sign."),
    ("HYG vs LQD (Credit)",
     f"{bxt['credit_chg']:+.2f}pp" if "credit_chg" in bxt else "Loading...",
     clr(bxt.get("credit_chg",0)),
     "Junk bonds vs investment grade. Falling=credit stress building=recession warning. Most important leading indicator for market health."),
    ("Small vs Large Cap",
     f"{bxt['small_vs_large']:+.2f}pp" if "small_vs_large" in bxt else "Loading...",
     clr(bxt.get("small_vs_large",0)),
     "IWM vs SPY 1-month. Positive=small caps leading=risk-on, economy healthy. Negative=only large caps working=narrow market."),
    ("Defensive Rotation",
     f"{bxt['def_rotation']:+.2f}pp" if "def_rotation" in bxt else "Loading...",
     clr(bxt.get("def_rotation",0), good_pos=False),
     "Staples (XLP) vs Tech (XLK). Negative=tech leading=risk-on. Positive=defensives leading=investors getting cautious=potential slowdown."),
    ("TLT (20Y Treasury)",
     f"${bxt.get('tlt',{}).get('price',0):.2f}  {bxt.get('tlt',{}).get('chg1d',0):+.2f}%" if "tlt" in bxt else "Loading...",
     clr(bxt.get("tlt",{}).get("chg1d",0)),
     "20-year Treasury ETF. Rising=flight to safety, stocks may fall. Falling=inflation fears or strong economy."),
    ("Gold vs Dollar",
     f"{bxt['gold_vs_dollar']:+.2f}pp" if "gold_vs_dollar" in bxt else "Loading...",
     clr(bxt.get("gold_vs_dollar",0)),
     "Gold (GLD) vs Dollar (UUP). Positive=gold outperforming=inflation/stress. Negative=dollar strong=risk-off, commodities pressured."),
]

br_cols = st.columns(3)
for i,(label,val,vc,desc) in enumerate(bm):
    with br_cols[i%3]:
        st.markdown(f"""
        <div class="card" style="margin-bottom:8px;">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <div class="lbl">{label}</div>
            {tip('ℹ',desc)}
          </div>
          <div style="font-size:20px;font-weight:700;color:{vc};margin-top:4px;">{val}</div>
        </div>""", unsafe_allow_html=True)

# Count how many indicators are positive (not a sum of +1/-1)
pos_count = 0
total_count = 0
if "breadth_1m" in bxt:
    total_count+=1
    if bxt["breadth_1m"]>0: pos_count+=1
if "credit_chg" in bxt:
    total_count+=1
    if bxt["credit_chg"]>0: pos_count+=1
if "small_vs_large" in bxt:
    total_count+=1
    if bxt["small_vs_large"]>0: pos_count+=1
if "def_rotation" in bxt:
    total_count+=1
    if bxt["def_rotation"]<0: pos_count+=1  # negative defensive rotation = good (tech leading)

bsc_col="#16a34a" if pos_count>=3 else "#dc2626" if pos_count<=1 else "#d97706"
bsc_lbl="Strong breadth — broad rally confirmed" if pos_count>=3 else "Weak breadth — narrow or deteriorating" if pos_count<=1 else "Mixed — selective conditions"
bsc_bg="#f0fdf4" if pos_count>=3 else "#fef2f2" if pos_count<=1 else "#fffbeb"
bsc_bc="#bbf7d0" if pos_count>=3 else "#fecaca" if pos_count<=1 else "#fde68a"

# Explain each indicator's reading
explain = []
if "breadth_1m" in bxt: explain.append(f"RSP-SPY: {'✓ Broad' if bxt['breadth_1m']>0 else '✗ Narrow'}")
if "credit_chg" in bxt: explain.append(f"Credit: {'✓ Healthy' if bxt['credit_chg']>0 else '✗ Stress'}")
if "small_vs_large" in bxt: explain.append(f"Small caps: {'✓ Leading' if bxt['small_vs_large']>0 else '✗ Lagging'}")
if "def_rotation" in bxt: explain.append(f"Defensives: {'✓ Not leading' if bxt['def_rotation']<0 else '✗ Rotating in'}")

st.markdown(f'''<div style="background:{bsc_bg};border:1px solid {bsc_bc};border-radius:6px;padding:10px 14px;margin-top:4px;">
  <div style="font-size:12px;"><span style="font-weight:700;color:{bsc_col};">Overall Breadth: {bsc_lbl}</span>
  <span style="color:#9ca3af;font-size:11px;margin-left:8px;">({pos_count}/{total_count} indicators positive)</span></div>
  <div style="font-size:11px;color:#6b7280;margin-top:5px;">{" &nbsp;·&nbsp; ".join(explain)}</div>
</div>''', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 5 — SECTOR HEATMAP
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🔥 Sector Momentum Heatmap</div>', unsafe_allow_html=True)
hp = st.radio("Period", ["1d","1w","1m"], horizontal=True, label_visibility="collapsed")

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
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🌐 Market Conditions — Rates · Volatility · FX</div>', unsafe_allow_html=True)

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
# SECTION 7 — COMMODITIES & ENERGY
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🛢️ Commodities & Energy</div>', unsafe_allow_html=True)

with st.spinner("Loading commodities..."):
    comms = get_commodities()

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
# SECTION 8 — INFLATION SIGNALS
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">📈 Inflation Signals</div>', unsafe_allow_html=True)

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
# SECTION 9 — MARKET THEMES (3-layer system)
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🎯 Market Themes & Momentum</div>', unsafe_allow_html=True)

# Build universe with custom tickers
universe_merged={}
for cat,themes in THEME_UNIVERSE.items():
    universe_merged[cat]=[]
    for t in themes:
        t2=copy.deepcopy(t)
        extras=st.session_state.custom_tickers.get(t2["name"],[])
        t2["tickers"]=list(dict.fromkeys(t2["tickers"]+extras))
        universe_merged[cat].append(t2)
for cat in ["hot","fading","emerging"]:
    for nt in st.session_state.approved_recs.get(f"new_{cat}",[]):
        universe_merged[cat].append(nt)

with st.spinner("Computing live theme momentum..."):
    live_themes = compute_theme_momentum(universe_merged)

# Daily Claude intelligence
sector_perf_str=", ".join([f"{k}:{v.get('1d',0):+.1f}%" for k,v in list((sectors or {}).items())[:6]])
scores_str=" | ".join([f"{t['name']}:{t['score']}" for cat in ["hot","fading","emerging"] for t in live_themes.get(cat,[])])

if ant_key:
    with st.spinner("Claude reviewing daily theme intelligence..."):
        intel = get_daily_theme_intel(scores_str, sector_perf_str, spy_d.get("chg1m",0), vix_price, today_str)
else:
    intel = None

if intel and intel.get("daily_note"):
    st.markdown(f"""
    <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:12px 16px;margin-bottom:10px;">
      <div style="font-size:11px;font-weight:700;color:#1d4ed8;margin-bottom:5px;">🤖 Daily Theme Intelligence · Claude Haiku · {today_str}</div>
      <div style="font-size:12px;color:#1e3a5f;line-height:1.6;">{intel['daily_note']}</div>
    </div>""", unsafe_allow_html=True)

# Recommendations
upgrades=intel.get("upgrades",[]) if intel else []
downgrades=intel.get("downgrades",[]) if intel else []
new_theme=intel.get("new_theme") if intel else None
pending=[]
if upgrades:
    for u in upgrades: pending.append(("⬆️ Upgrade",u["name"],u["reason"],"up"))
if downgrades:
    for d in downgrades: pending.append(("⬇️ Downgrade",d["name"],d["reason"],"dn"))
if new_theme and isinstance(new_theme,dict):
    pending.append(("✨ New Theme",new_theme["name"],new_theme.get("reason",""),"new"))

if pending:
    st.markdown('<div style="font-size:11px;font-weight:700;color:#374151;margin-bottom:6px;">📋 Daily recommendations - click to approve</div>', unsafe_allow_html=True)
    rec_cols=st.columns(len(pending))
    for col,(label,name,reason,kind) in zip(rec_cols,pending):
        bg="#f0fdf4" if kind=="up" else "#fef2f2" if kind=="dn" else "#faf5ff"
        bc="#bbf7d0" if kind=="up" else "#fecaca" if kind=="dn" else "#e9d5ff"
        tc="#15803d" if kind=="up" else "#b91c1c" if kind=="dn" else "#7e22ce"
        with col:
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {bc};border-radius:6px;padding:8px 10px;margin-bottom:6px;">
              <div style="font-size:10px;font-weight:700;color:{tc};">{label}</div>
              <div style="font-size:12px;font-weight:700;color:#374151;margin:3px 0;">{name}</div>
              <div style="font-size:10px;color:#6b7280;">{reason}</div>
            </div>""", unsafe_allow_html=True)
            if st.button("✓ Approve", key=f"ap_{name}_{kind}"):
                if kind=="new" and isinstance(new_theme,dict):
                    cat=new_theme.get("category","emerging")
                    existing=st.session_state.approved_recs.get(f"new_{cat}",[])
                    existing.append({"name":new_theme["name"],"subsectors":new_theme.get("subsectors",[]),"tickers":new_theme.get("tickers",[]),"desc":new_theme.get("desc","")})
                    st.session_state.approved_recs[f"new_{cat}"]=existing
                st.rerun()

# Theme tabs
tab_labels=["🔥 Hot","📉 Fading","🌱 Emerging"]
tab_keys=["hot","fading","emerging"]
tabs_th=st.tabs(tab_labels)
for tab,key in zip(tabs_th,tab_keys):
    with tab:
        for t in live_themes.get(key,[]):
            score=t["score"]; avg_m=t.get("avg_mom",0)
            sc="#16a34a" if score>=65 else "#d97706" if score>=45 else "#dc2626"
            flag=""
            if intel:
                if any(u["name"]==t["name"] for u in upgrades): flag=" ⬆️"
                if any(d["name"]==t["name"] for d in downgrades): flag=" ⬇️"
            with st.expander(f"**{t['name']}**{flag}  —  Score: {score}/100  ·  {avg_m:+.1f}%"):
                cl,cr=st.columns([2,1])
                with cl:
                    st.markdown(f'<div style="font-size:12px;color:#6b7280;margin-bottom:8px;">{t["desc"]}</div>', unsafe_allow_html=True)
                    st.markdown('<div style="font-size:10px;color:#9ca3af;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:5px;">Sub-sectors</div>', unsafe_allow_html=True)
                    pills=" ".join([f'<span style="background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;padding:2px 8px;border-radius:12px;font-size:10px;font-weight:600;">{s}</span>' for s in t.get("subsectors",[])])
                    st.markdown(pills, unsafe_allow_html=True)
                    st.markdown(f'''<div style="margin-top:8px;">
                      <div style="display:flex;justify-content:space-between;font-size:10px;color:#9ca3af;margin-bottom:3px;"><span>Momentum Score</span><span style="font-weight:700;color:{sc};">{score}/100</span></div>
                      <div style="height:7px;background:#f3f4f6;border-radius:4px;overflow:hidden;"><div style="height:7px;width:{score}%;background:{sc};border-radius:4px;"></div></div>
                    </div>''', unsafe_allow_html=True)
                    ni=st.text_input(f"Add ticker to {t['name']}",key=f"ni_{t['name']}",placeholder="e.g. SOUN",max_chars=8,label_visibility="collapsed").upper().strip()
                    if st.button("+ Add ticker",key=f"ab_{t['name']}") and ni:
                        ex=st.session_state.custom_tickers.get(t["name"],[])
                        if ni not in ex: ex.append(ni); st.session_state.custom_tickers[t["name"]]=ex; st.rerun()
                    customs=st.session_state.custom_tickers.get(t["name"],[])
                    if customs: st.caption(f"Your additions: {', '.join(customs)}")
                with cr:
                    st.markdown('<div style="font-size:10px;color:#9ca3af;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:5px;">Top stocks by momentum</div>', unsafe_allow_html=True)
                    for td in t.get("ticker_data",[])[:5]:
                        tc=clr(td["chg1m"]); is_c=td["sym"] in st.session_state.custom_tickers.get(t["name"],[])
                        cb=' <span style="background:#faf5ff;color:#7e22ce;font-size:9px;padding:1px 4px;border-radius:2px;">+</span>' if is_c else ""
                        st.markdown(f"""
                        <div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid #f3f4f6;font-size:11px;">
                          <span style="font-weight:700;color:#374151;">{td["sym"]}{cb}</span>
                          <span style="color:{tc};font-weight:600;">{td["chg1m"]:+.1f}%</span>
                          <span style="color:{clr(td['chg1w'])};font-size:10px;">{td['chg1w']:+.1f}%</span>
                        </div>""", unsafe_allow_html=True)

st.caption(f"Layer 1: Yahoo Finance price momentum (hourly) · Layer 2: Claude daily intel (~$0.008/day) · Layer 3: Your custom tickers · {today_str}")

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 10 — SENTIMENT & SMART MONEY
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">😱 Sentiment · Fear/Greed · Analyst Consensus · Insider Activity</div>', unsafe_allow_html=True)

fg_score=max(0,min(100,int(100-(vix_price-10)/35*100)))
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
# SECTION 11 — AI OPTIONS FLOW
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🤖 AI Options Flow Analysis — Powered by Claude</div>', unsafe_allow_html=True)

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
# SECTION 12 — CATALYST CALENDAR
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">📅 Catalyst Calendar</div>', unsafe_allow_html=True)

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
# SECTION 13 — SHORT SQUEEZE RADAR
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">💥 Short Squeeze Radar — Live (Yahoo Finance)</div>', unsafe_allow_html=True)

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
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec">🔬 Live Stock Screener — Real-Time Signal Breakdown</div>', unsafe_allow_html=True)
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
            if st.button(t,key=f"qp_{t}"): ticker_input=t

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
                st.plotly_chart(fig_s,use_container_width=True,config={"displayModeBar":False})
        elif sig and sig.get("error"):
            st.error(f"Could not fetch **{sym}**: {sig['error']}")
        else:
            st.info(f"No data found for {sym}. Try a major US-listed stock.")

# ── FOOTER ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center;font-size:11px;color:#9ca3af;padding:8px 0;">
  ⚠️ For informational purposes only · Not financial advice · Always do your own research<br>
  Data: Yahoo Finance · Finnhub · FRED (Federal Reserve) · Prices ~15 min delayed
</div>""", unsafe_allow_html=True)
