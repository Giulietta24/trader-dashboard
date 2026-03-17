# 📊 Trader Intelligence Dashboard

A Bloomberg-terminal-style trading dashboard built with Streamlit and Yahoo Finance. Includes market conditions, index comparison (SPY/QQQ/DIA/IWM), commodities, energy, inflation signals, sector heatmap, market themes, sentiment, short squeeze radar, catalyst calendar, and a live stock screener.

## 🚀 Features

- **Live Data** — All prices via Yahoo Finance (yfinance), auto-cached every 5 minutes
- **4 Index Comparison** — SPY, QQQ, DIA, IWM with cap-size divergence alerts
- **Market Conditions** — VIX, 10Y/5Y/3M yields, DXY, yield curve
- **Commodities & Energy** — Gold, Silver, Copper, WTI, Brent, Nat Gas, Wheat, Corn
- **Inflation Dashboard** — CPI, Core CPI, PCE, PPI, breakevens, Fed path
- **Sector Heatmap** — All 11 GICS sectors, 1D/1W/1M view
- **Market Themes** — Hot, Fading, Emerging themes with momentum scores
- **Sentiment** — Fear/Greed, AAII Bull/Bear, options flow
- **Short Squeeze Radar** — High SI + DTC candidates
- **Catalyst Calendar** — Earnings, FOMC, CPI, NFP dates
- **Live Stock Screener** — Enter any ticker → full signal breakdown, ATR trade setup, 60-day chart

---

## 🛠️ Local Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/trader-dashboard.git
cd trader-dashboard
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
streamlit run dashboard.py
```

The app will open at `http://localhost:8501`

---

## ☁️ Deploy to Streamlit Cloud (Free)

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit — Trader Intelligence Dashboard"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/trader-dashboard.git
   git push -u origin main
   ```

2. **Go to** [share.streamlit.io](https://share.streamlit.io)

3. **Sign in** with your GitHub account

4. Click **"New app"** → Select your repo → Set:
   - **Repository:** `YOUR_USERNAME/trader-dashboard`
   - **Branch:** `main`
   - **Main file path:** `dashboard.py`

5. Click **Deploy** — your app goes live in ~2 minutes at:
   `https://YOUR_USERNAME-trader-dashboard.streamlit.app`

---

## 📁 File Structure

```
trader-dashboard/
├── dashboard.py        # Main Streamlit app
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## ⚙️ Configuration

No API keys required — Yahoo Finance is used via `yfinance` (free, no auth).

### Optional: Add to `.streamlit/config.toml` for theme settings
```toml
[theme]
base = "dark"
backgroundColor = "#0a0a0f"
secondaryBackgroundColor = "#0d0d14"
textColor = "#e2e8f0"
font = "monospace"
```

Create this file:
```bash
mkdir -p .streamlit
cat > .streamlit/config.toml << 'EOF'
[theme]
base = "dark"
backgroundColor = "#0a0a0f"
secondaryBackgroundColor = "#0d0d14"
textColor = "#e2e8f0"
font = "monospace"
EOF
```

---

## 📈 Data Sources

| Data | Source | Refresh |
|------|--------|---------|
| Stock prices | Yahoo Finance | 5 min |
| Index data | Yahoo Finance | 5 min |
| Commodity futures | Yahoo Finance | 5 min |
| Bond yields / VIX | Yahoo Finance | 5 min |
| Sector ETFs | Yahoo Finance | 10 min |
| Technicals | Computed from price history | 10 min |
| Themes / Sentiment | Static (curated weekly) | Manual |
| Options flow | Static (illustrative) | Manual |

> **Note:** Prices are delayed ~15 minutes. For real-time data, upgrade to a paid provider (Polygon.io, Finnhub, or Interactive Brokers).

---

## 🔌 Upgrading to Real-Time Data (Optional)

To get real-time prices, replace `yfinance` calls with a paid API:

### Finnhub (free tier available)
```python
import requests
FINNHUB_KEY = "your_api_key"

def get_quote_finnhub(sym):
    r = requests.get(f"https://finnhub.io/api/v1/quote?symbol={sym}&token={FINNHUB_KEY}")
    return r.json()  # {"c": current, "d": change, "dp": change_pct, ...}
```

Add your API key to Streamlit Cloud secrets:
1. Go to your app → Settings → Secrets
2. Add: `FINNHUB_KEY = "your_key_here"`
3. Access in code: `st.secrets["FINNHUB_KEY"]`

---

## ⚠️ Disclaimer

This dashboard is for **informational and educational purposes only**. It is **not financial advice**. Always do your own research before making any investment decisions. Past performance does not guarantee future results.

---

## 📝 License

MIT License — free to use, modify, and distribute.
