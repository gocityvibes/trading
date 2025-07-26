
import os
import openai
import requests

openai.api_key = os.getenv("OPENAI_API_KEY")

def fetch_ohlc(symbol):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/5/minute/1/day?adjusted=true&sort=desc&limit=20&apiKey=" + os.getenv("POLYGON_API_KEY")
    res = requests.get(url)
    bars = res.json().get("results", [])
    return bars

def fetch_float(symbol):
    url = f"https://api.polygon.io/v3/reference/tickers/{symbol}?apiKey=" + os.getenv("POLYGON_API_KEY")
    res = requests.get(url)
    return int(res.json()["results"].get("share_class_shares_outstanding", 0))

def fetch_news_headlines(symbol):
    url = f"https://api.polygon.io/v2/reference/news?ticker={symbol}&limit=3&apiKey=" + os.getenv("POLYGON_API_KEY")
    res = requests.get(url)
    headlines = [article["title"] for article in res.json().get("results", [])]
    return headlines

def analyze_symbol(symbol):
    bars = fetch_ohlc(symbol)
    float_size = fetch_float(symbol)
    news = fetch_news_headlines(symbol)

    chart_prompt = f"""
You are a trading analyst. Given the OHLC data below and news headlines, analyze whether this stock shows a bullish chart pattern like bull flag, breakout, etc. Return score (0-100), sentiment (bullish/bearish/neutral), and if a strong pattern is confirmed.

OHLC:
{bars}

News:
{news}
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert trading assistant."},
            {"role": "user", "content": chart_prompt}
        ]
    )

    text = response["choices"][0]["message"]["content"]
    # Naive parse (we can improve with stricter formatting later)
    score = int([s for s in text.split() if s.isdigit()][0])
    sentiment = "bullish" if "bullish" in text else "bearish" if "bearish" in text else "neutral"
    pattern_confirmed = "yes" in text.lower() or "confirmed" in text.lower()

    return {
        "symbol": symbol,
        "score": score,
        "float": float_size,
        "sentiment": sentiment,
        "pattern_confirmed": pattern_confirmed,
        "gpt_notes": text.strip()
    }
