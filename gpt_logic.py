import openai

def gpt_3_5_scan(stocks):
    top_50 = sorted(stocks, key=lambda x: x['momentum'], reverse=True)[:50]
    return top_50


def process_trades_with_gpt(stocks):
    top_50 = gpt_3_5_scan(stocks)
    top_10 = top_50[:10]
    trades = []

    for stock in top_10:
        score = enhanced_gpt_4o_score(stock)
        stock['gpt_4o_score'] = score
        if score >= 95:
            trades.append(stock)

    return trades


def enhanced_gpt_4o_score(stock):
    import openai

    # Compose full context with multiple criteria
    context = f"""
    Stock Symbol: {stock['symbol']}
    Price: {stock['price']}
    Volume: {stock['volume']}
    Avg Volume: {stock['avg_volume']}
    Float: {stock['float']}
    News: {stock.get('news', '')}
    Market Sentiment (SPY): {stock.get('spy_sentiment', 'neutral')}
    Market Sentiment (QQQ): {stock.get('qqq_sentiment', 'neutral')}
    Pattern Match (1m): {stock.get('pattern_1m', 'unknown')}
    Pattern Match (5m): {stock.get('pattern_5m', 'unknown')}
    Pattern Match (Daily): {stock.get('pattern_daily', 'unknown')}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an elite intraday trading assistant scoring stocks for breakout potential. Score from 0–100."},
            {"role": "user", "content": context}
        ]
    )

    score_text = response['choices'][0]['message']['content'].strip()
    score = int(score_text.split()[0]) if score_text.split()[0].isdigit() else 0
    return score
