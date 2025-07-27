
import openai

def gpt_3_5_scan(stocks):
    top_50 = sorted(stocks, key=lambda x: x['momentum'], reverse=True)[:50]
    return top_50

def gpt_4o_score(stock):
    # Simulated GPT-4o scoring logic
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a trading assistant scoring breakout stocks."},
            {"role": "user", "content": f"Score this stock for breakout trading: {stock}"}
        ]
    )
    score = int(response['choices'][0]['message']['content'].strip().split()[0])  # Expected format: "95 - Good setup"
    return score

def process_trades_with_gpt(stocks):
    top_50 = gpt_3_5_scan(stocks)
    top_10 = top_50[:10]
    trades = []

    for stock in top_10:
        score = gpt_4o_score(stock)
        stock['gpt_4o_score'] = score
        if score >= 95:
            trades.append(stock)

    return trades
