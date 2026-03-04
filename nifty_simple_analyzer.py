import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def fetch_nifty_data(days=100):
    """Get Nifty 50 stock market data"""
    print("\nGetting Nifty 50 data from the stock market...")
    print("Please wait...\n")
    df = yf.download('^NSEI', period=f'{days}d', progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    return df


def calculate_indicators(df):
    """Calculate all the technical indicators"""
    # Simple Moving Averages (average prices)
    df['SMA_20'] = df['Close'].rolling(window=20).mean()  # 20-day average
    df['SMA_50'] = df['Close'].rolling(window=50).mean()  # 50-day average
    
    # RSI (shows if stock is expensive or cheap)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df


def get_simple_recommendation(df):
    """Generate easy-to-understand recommendation"""
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Get current values
    current_price = float(latest['Close'])
    yesterday_price = float(prev['Close'])
    sma_20 = float(latest['SMA_20'])
    sma_50 = float(latest['SMA_50'])
    rsi = float(latest['RSI'])
    
    # Calculate price change
    price_change = current_price - yesterday_price
    price_change_percent = (price_change / yesterday_price) * 100
    
    # Calculate support and resistance (last 20 days)
    recent_data = df.tail(20)
    highest_price = float(recent_data['High'].max())
    lowest_price = float(recent_data['Low'].min())
    
    # Determine market status
    if price_change > 0:
        today_status = "UP"
        status_emoji = "[+]"
    else:
        today_status = "DOWN"
        status_emoji = "[-]"
    
    # Determine trend (is market going up or down?)
    if current_price > sma_20 > sma_50:
        trend = "STRONG UPWARD TREND"
        trend_explanation = "Market is moving UP strongly"
        trend_color = "GREEN"
    elif current_price > sma_20 and current_price > sma_50:
        trend = "UPWARD TREND"
        trend_explanation = "Market is moving UP"
        trend_color = "GREEN"
    elif current_price < sma_20 < sma_50:
        trend = "STRONG DOWNWARD TREND"
        trend_explanation = "Market is moving DOWN strongly"
        trend_color = "RED"
    elif current_price < sma_20 and current_price < sma_50:
        trend = "DOWNWARD TREND"
        trend_explanation = "Market is moving DOWN"
        trend_color = "RED"
    else:
        trend = "SIDEWAYS"
        trend_explanation = "Market is NOT moving much (stable)"
        trend_color = "YELLOW"
    
    # Determine if expensive or cheap
    if rsi > 70:
        price_status = "EXPENSIVE"
        price_advice = "Market might be too high - be careful!"
    elif rsi < 30:
        price_status = "CHEAP"
        price_advice = "Market might be low - could be a good time to buy"
    else:
        price_status = "FAIR PRICE"
        price_advice = "Market is at normal levels"
    
    # Simple recommendation
    if trend_color == "GREEN" and rsi < 70:
        action = "BUY"
        simple_advice = "Good time to invest"
        risk = "LOW TO MEDIUM"
    elif trend_color == "RED" or rsi > 70:
        action = "SELL or WAIT"
        simple_advice = "Not a good time to invest, or book profits"
        risk = "MEDIUM TO HIGH"
    else:
        action = "WAIT AND WATCH"
        simple_advice = "Better to wait for clearer signals"
        risk = "MEDIUM"
    
    return {
        'current_price': current_price,
        'yesterday_price': yesterday_price,
        'price_change': price_change,
        'price_change_percent': price_change_percent,
        'today_status': today_status,
        'status_emoji': status_emoji,
        'trend': trend,
        'trend_explanation': trend_explanation,
        'trend_color': trend_color,
        'rsi': rsi,
        'price_status': price_status,
        'price_advice': price_advice,
        'action': action,
        'simple_advice': simple_advice,
        'risk': risk,
        'highest_price': highest_price,
        'lowest_price': lowest_price,
        'sma_20': sma_20,
        'sma_50': sma_50
    }


def print_simple_report(result):
    """Print an easy-to-understand report"""
    
    print("\n" + "="*70)
    print("           NIFTY 50 ANALYSIS - SIMPLE REPORT")
    print("="*70)
    print("Date: {}".format(datetime.now().strftime('%d %B %Y, %I:%M %p')))
    print("="*70)
    
    # TODAY'S PRICE
    print("\n>>> TODAY'S PRICE <<<")
    print("-" * 70)
    print("Current Price:  Rs. {:,.2f}".format(result['current_price']))
    print("Yesterday:      Rs. {:,.2f}".format(result['yesterday_price']))
    print("Change:         Rs. {:+,.2f} ({:+.2f}%) {}".format(
        result['price_change'], 
        result['price_change_percent'],
        result['status_emoji']
    ))
    print("\nToday market is: {}".format(result['today_status']))
    
    # MARKET TREND
    print("\n>>> MARKET TREND (Direction) <<<")
    print("-" * 70)
    print("Status: {}".format(result['trend']))
    print("What this means: {}".format(result['trend_explanation']))
    print("Signal Color: {}".format(result['trend_color']))
    
    # PRICE LEVELS
    print("\n>>> PRICE LEVELS (Last 20 days) <<<")
    print("-" * 70)
    print("Highest Price:  Rs. {:,.2f}  <-- RESISTANCE (hard to cross)".format(result['highest_price']))
    print("Current Price:  Rs. {:,.2f}".format(result['current_price']))
    print("Lowest Price:   Rs. {:,.2f}  <-- SUPPORT (strong base)".format(result['lowest_price']))
    
    # IS IT EXPENSIVE OR CHEAP?
    print("\n>>> IS NIFTY EXPENSIVE OR CHEAP? <<<")
    print("-" * 70)
    print("RSI Value: {:.1f}".format(result['rsi']))
    print("Status: {}".format(result['price_status']))
    print("Explanation: {}".format(result['price_advice']))
    print("\nNote: RSI above 70 = Expensive | RSI below 30 = Cheap")
    
    # RECOMMENDATION
    print("\n>>> RECOMMENDATION <<<")
    print("=" * 70)
    print("ACTION: {}".format(result['action']))
    print("ADVICE: {}".format(result['simple_advice']))
    print("RISK LEVEL: {}".format(result['risk']))
    print("=" * 70)
    
    # DETAILED SUGGESTIONS
    print("\n>>> WHAT SHOULD YOU DO? <<<")
    print("-" * 70)
    
    if result['action'] == "BUY":
        print("1. This could be a good time to invest in Nifty")
        print("2. Market trend is positive")
        print("3. Consider buying in small amounts (SIP method)")
        print("4. Set a target near Rs. {:,.2f}".format(result['highest_price']))
    elif "SELL" in result['action']:
        print("1. Market might go down soon")
        print("2. If you have invested, consider booking some profit")
        print("3. Don't invest new money right now")
        print("4. Wait for market to become cheaper")
    else:
        print("1. Market is confused - no clear direction")
        print("2. Better to wait and watch")
        print("3. Don't rush to invest")
        print("4. Wait for clearer signals")
    
    # AVERAGES (Simple Explanation)
    print("\n>>> AVERAGE PRICES (Moving Averages) <<<")
    print("-" * 70)
    print("20-Day Average: Rs. {:,.2f}".format(result['sma_20']))
    print("50-Day Average: Rs. {:,.2f}".format(result['sma_50']))
    print("\nWhat this means:")
    if result['current_price'] > result['sma_20']:
        print("  Current price is ABOVE short-term average (Positive sign)")
    else:
        print("  Current price is BELOW short-term average (Negative sign)")
    
    # IMPORTANT NOTES
    print("\n" + "="*70)
    print("IMPORTANT THINGS TO REMEMBER:")
    print("="*70)
    print("1. Stock market can be risky - never invest money you can't afford to lose")
    print("2. This is just analysis - always talk to a financial expert")
    print("3. Don't invest all your money at once - invest in small parts (SIP)")
    print("4. Past performance doesn't guarantee future results")
    print("5. Do your own research before investing")
    print("="*70)
    
    # GLOSSARY
    print("\n>>> WORD MEANINGS (Glossary) <<<")
    print("-" * 70)
    print("NIFTY 50     = Top 50 companies in Indian stock market")
    print("RSI          = Shows if market is expensive or cheap")
    print("TREND        = Direction where market is moving")
    print("SUPPORT      = Price level where market usually doesn't fall below")
    print("RESISTANCE   = Price level where market usually struggles to cross")
    print("SMA          = Simple Moving Average (average price over days)")
    print("="*70 + "\n")


def main():
    """Main function"""
    print("\n" + "="*70)
    print("      WELCOME TO SIMPLE NIFTY 50 ANALYZER")
    print("      Easy to understand for everyone!")
    print("="*70)
    
    # Get data
    df = fetch_nifty_data(days=100)
    
    # Calculate indicators
    print("Analyzing the market...")
    df = calculate_indicators(df)
    
    # Get recommendation
    print("Creating simple report...\n")
    result = get_simple_recommendation(df)
    
    # Print report
    print_simple_report(result)
    
    # Save data
    output_file = 'nifty_simple_report.txt'
    
    # Save report to file
    import sys
    original_stdout = sys.stdout
    with open(output_file, 'w', encoding='utf-8') as f:
        sys.stdout = f
        print_simple_report(result)
    sys.stdout = original_stdout
    
    print("\n[SUCCESS] Report saved to: {}".format(output_file))
    print("[INFO] You can open this file to read the report anytime!")
    print("\nThank you for using Simple Nifty Analyzer!\n")
    
    return df, result


if __name__ == "__main__":
    df, result = main()
