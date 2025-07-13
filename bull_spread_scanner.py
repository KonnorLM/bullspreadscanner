import os, requests, time, pandas as pd
from datetime import datetime, timedelta
import pytz

API_KEY = os.getenv("POLYGON_API_KEY")
WEBHOOK = os.getenv("DISCORD_WEBHOOK")
EXPIRATION_DAYS = 14
MAX_DEBIT = 2.00
MIN_SCORE = 75
BATCH_SIZE = 10
SLEEP_BETWEEN_BATCHES = 600

def send_discord_startup():
    msg = "✅ **Bull Spread Scanner has started** and is monitoring the S&P 500..."
    requests.post(WEBHOOK, json={"content": msg})

def main():
    send_discord_startup()  # 🔹 SEND STARTUP MESSAGE
    tickers = get_sp500_tickers()

def get_sp500_tickers():
    r = requests.get("https://datahub.io/core/s-and-p-500-companies/r/constituents.csv")
    return pd.read_csv(pd.compat.StringIO(r.text))['Symbol'].tolist()

def get_latest_price(ticker):
    url = f"https://api.polygon.io/v2/last/trade/{ticker}?apiKey={API_KEY}"
    try:
        r = requests.get(url)
        r.raise_for_status()
        return r.json()["results"]["p"]
    except:
        return None

def get_options_chain(ticker, exp):
    url = f"https://api.polygon.io/v3/snapshot/options/{ticker}?apiKey={API_KEY}"
    try:
        r = requests.get(url)
        r.raise_for_status()
        options = r.json().get("results", {}).get("options", [])
        return [o for o in options if o["expiration_date"] == exp and o["option_type"] == "call"]
    except:
        return []

def score_spread(buy, sell):
    debit = buy["ask"] - sell["bid"]
    spread = sell["strike_price"] - buy["strike_price"]
    if debit <= 0 or spread <= 0: return 0
    rr = (spread - debit) / debit
    return round(rr * 100)

def screen_spreads(ticker):
    now = datetime.utcnow()
    exp = (now + timedelta(days=EXPIRATION_DAYS)).strftime('%Y-%m-%d')
    options = get_options_chain(ticker, exp)
    if not options: return []
    options = sorted(options, key=lambda x: x["strike_price"])
    signals = []
    for i in range(len(options)-1):
        buy = options[i]
        sell = options[i+1]
        score = score_spread(buy, sell)
        if score >= MIN_SCORE and (buy["ask"] - sell["bid"]) <= MAX_DEBIT:
            signals.append({
                "ticker": ticker,
                "buy": buy["strike_price"],
                "sell": sell["strike_price"],
                "debit": round(buy["ask"] - sell["bid"], 2),
                "score": score,
                "exp": exp
            })
    return signals

def send_discord_alert(signal):
    msg = f"📈 **{signal['ticker']}** Bull Call Spread\n"
    msg += f"Buy {signal['buy']} / Sell {signal['sell']} exp {signal['exp']}\n"
    msg += f"Max Debit: ${signal['debit']} | Score: {signal['score']}"
    requests.post(WEBHOOK, json={"content": msg})

def run_scanner():
    tickers = get_sp500_tickers()
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i+BATCH_SIZE]
        for ticker in batch:
            signals = screen_spreads(ticker)
            for s in signals:
                send_discord_alert(s)
        time.sleep(SLEEP_BETWEEN_BATCHES)

if __name__ == "__main__":
    while True:
        now = datetime.now(pytz.timezone("US/Eastern"))
        if now.weekday() < 5 and now.hour >= 9 and (now.hour < 16 or (now.hour == 16 and now.minute <= 0)):
            run_scanner()
        else:
            time.sleep(300)