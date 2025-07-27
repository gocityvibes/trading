


def passes_pre_filters(stock):
    # Example structure of stock: {'symbol': 'AAPL', 'price': 170, 'volume': 30000000, 'avg_volume': 15000000, 'float': 90000000, 'news': ''}

    # Price range check
    if stock['price'] < 1 or stock['price'] > 100:
        return False

    # Float filter (hard rule)
    if stock['float'] > 100_000_000:
        return False

    # Volume surge filter (1.5x average volume)
    if stock['volume'] < 1.5 * stock['avg_volume']:
        return False

    # No dilution/lawsuit/downgrade via news (simple keyword match)
    landmine_keywords = ['dilution', 'lawsuit', 'downgrade']
    news = stock.get('news', '').lower()
    if any(keyword in news for keyword in landmine_keywords):
        return False

    return True
