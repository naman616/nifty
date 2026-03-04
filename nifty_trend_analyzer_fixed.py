import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


def fetch_nifty_data(days=100):
    """
    Fetch Nifty 50 historical data from Yahoo Finance
    """
    print("Fetching real Nifty 50 data...")
    df = yf.download('^NSEI', period=f'{days}d', progress=False)
    
    # Ensure column names are standardized (yfinance might return multi-index)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    return df


def calculate_moving_averages(df):
    """Calculate various moving averages"""
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    return df


def calculate_rsi(df, period=14):
    """Calculate Relative Strength Index"""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df


def calculate_macd(df):
    """Calculate MACD indicator"""
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Histogram'] = df['MACD'] - df['Signal_Line']
    return df


def calculate_bollinger_bands(df, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    df['BB_Middle'] = df['Close'].rolling(window=period).mean()
    df['BB_Std'] = df['Close'].rolling(window=period).std()
    df['BB_Upper'] = df['BB_Middle'] + (std_dev * df['BB_Std'])
    df['BB_Lower'] = df['BB_Middle'] - (std_dev * df['BB_Std'])
    return df


def identify_trend(df):
    """Identify current market trend"""
    latest = df.iloc[-1]
    
    # Extract scalar values from Series
    price = float(latest['Close'])
    sma_20 = float(latest['SMA_20'])
    sma_50 = float(latest['SMA_50'])
    
    if price > sma_20 > sma_50:
        trend = "Strong Uptrend"
        trend_strength = "Strong"
    elif price > sma_20 and price > sma_50:
        trend = "Uptrend"
        trend_strength = "Moderate"
    elif price < sma_20 < sma_50:
        trend = "Strong Downtrend"
        trend_strength = "Strong"
    elif price < sma_20 and price < sma_50:
        trend = "Downtrend"
        trend_strength = "Moderate"
    else:
        trend = "Sideways/Consolidation"
        trend_strength = "Weak"
    
    return trend, trend_strength


def analyze_momentum(df):
    """Analyze momentum indicators"""
    latest = df.iloc[-1]
    rsi = float(latest['RSI'])
    macd = float(latest['MACD'])
    signal = float(latest['Signal_Line'])
    
    momentum = {}
    
    # RSI Analysis
    if rsi > 70:
        momentum['RSI'] = f"Overbought ({rsi:.2f})"
        momentum['RSI_signal'] = "Bearish"
    elif rsi < 30:
        momentum['RSI'] = f"Oversold ({rsi:.2f})"
        momentum['RSI_signal'] = "Bullish"
    else:
        momentum['RSI'] = f"Neutral ({rsi:.2f})"
        momentum['RSI_signal'] = "Neutral"
    
    # MACD Analysis
    if macd > signal and macd > 0:
        momentum['MACD'] = "Bullish Crossover"
        momentum['MACD_signal'] = "Bullish"
    elif macd < signal and macd < 0:
        momentum['MACD'] = "Bearish Crossover"
        momentum['MACD_signal'] = "Bearish"
    else:
        momentum['MACD'] = "Neutral"
        momentum['MACD_signal'] = "Neutral"
    
    return momentum


def analyze_volatility(df):
    """Analyze market volatility using Bollinger Bands"""
    latest = df.iloc[-1]
    price = float(latest['Close'])
    bb_upper = float(latest['BB_Upper'])
    bb_lower = float(latest['BB_Lower'])
    bb_middle = float(latest['BB_Middle'])
    
    bb_position = (price - bb_lower) / (bb_upper - bb_lower) * 100
    
    if price > bb_upper:
        volatility_status = "High - Price above upper band (Overbought)"
    elif price < bb_lower:
        volatility_status = "High - Price below lower band (Oversold)"
    elif bb_position > 80:
        volatility_status = "Moderate-High - Near upper band"
    elif bb_position < 20:
        volatility_status = "Moderate-High - Near lower band"
    else:
        volatility_status = "Normal - Within bands"
    
    return volatility_status, bb_position


def calculate_support_resistance(df, window=20):
    """Calculate support and resistance levels"""
    recent_data = df.tail(window)
    
    resistance = float(recent_data['High'].max())
    support = float(recent_data['Low'].min())
    current_price = float(df['Close'].iloc[-1])
    
    return support, resistance, current_price


def generate_suggestions(df):
    """Generate investment suggestions based on technical analysis"""
    trend, trend_strength = identify_trend(df)
    momentum = analyze_momentum(df)
    volatility, bb_position = analyze_volatility(df)
    support, resistance, current_price = calculate_support_resistance(df)
    
    suggestions = []
    risk_level = "Medium"
    action = "HOLD"
    
    # Bullish signals
    bullish_count = 0
    bearish_count = 0
    
    if "Uptrend" in trend:
        bullish_count += 2
    elif "Downtrend" in trend:
        bearish_count += 2
    
    if momentum['RSI_signal'] == "Bullish":
        bullish_count += 1
    elif momentum['RSI_signal'] == "Bearish":
        bearish_count += 1
    
    if momentum['MACD_signal'] == "Bullish":
        bullish_count += 1
    elif momentum['MACD_signal'] == "Bearish":
        bearish_count += 1
    
    # Generate action based on signals
    if bullish_count >= 3:
        action = "BUY"
        suggestions.append("[+] Strong bullish signals detected")
        suggestions.append("[*] Consider buying near support level: Rs. {:.2f}".format(support))
        suggestions.append("[>] Target resistance: Rs. {:.2f}".format(resistance))
        risk_level = "Low-Medium"
    elif bearish_count >= 3:
        action = "SELL"
        suggestions.append("[!] Strong bearish signals detected")
        suggestions.append("[*] Consider booking profits or avoiding new positions")
        suggestions.append("[>] Watch support level: Rs. {:.2f}".format(support))
        risk_level = "High"
    else:
        action = "HOLD"
        suggestions.append("[-] Mixed signals - Market in consolidation")
        suggestions.append("[*] Wait for clearer trend confirmation")
        suggestions.append("[>] Range: Rs. {:.2f} - Rs. {:.2f}".format(support, resistance))
        risk_level = "Medium"
    
    # Add specific recommendations based on indicators
    if "Oversold" in momentum['RSI']:
        suggestions.append("[i] RSI indicates oversold conditions - potential buying opportunity")
    elif "Overbought" in momentum['RSI']:
        suggestions.append("[i] RSI indicates overbought conditions - consider profit booking")
    
    if bb_position < 20:
        suggestions.append("[v] Price near lower Bollinger Band - potential bounce expected")
    elif bb_position > 80:
        suggestions.append("[^] Price near upper Bollinger Band - resistance expected")
    
    return {
        'action': action,
        'risk_level': risk_level,
        'suggestions': suggestions,
        'trend': trend,
        'trend_strength': trend_strength,
        'support': support,
        'resistance': resistance,
        'current_price': current_price
    }


def print_analysis_report(df, analysis):
    """Print comprehensive analysis report"""
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    print("\n" + "="*70)
    print("NIFTY 50 TREND ANALYSIS REPORT")
    print("="*70)
    print("Analysis Date: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    print("Current Price: Rs. {:.2f}".format(analysis['current_price']))
    print("Previous Close: Rs. {:.2f}".format(float(prev['Close'])))
    
    change = analysis['current_price'] - float(prev['Close'])
    change_pct = (change / float(prev['Close'])) * 100
    print("Change: Rs. {:.2f} ({:+.2f}%)".format(change, change_pct))
    
    print("\n" + "-"*70)
    print("TECHNICAL INDICATORS")
    print("-"*70)
    print("Trend: {} ({})".format(analysis['trend'], analysis['trend_strength']))
    print("RSI (14): {:.2f}".format(float(latest['RSI'])))
    print("MACD: {:.2f}".format(float(latest['MACD'])))
    print("Signal Line: {:.2f}".format(float(latest['Signal_Line'])))
    print("SMA 20: Rs. {:.2f}".format(float(latest['SMA_20'])))
    print("SMA 50: Rs. {:.2f}".format(float(latest['SMA_50'])))
    
    print("\n" + "-"*70)
    print("SUPPORT & RESISTANCE")
    print("-"*70)
    print("Resistance: Rs. {:.2f}".format(analysis['resistance']))
    print("Current:    Rs. {:.2f}".format(analysis['current_price']))
    print("Support:    Rs. {:.2f}".format(analysis['support']))
    
    print("\n" + "-"*70)
    print("RECOMMENDATION: {}".format(analysis['action']))
    print("Risk Level: {}".format(analysis['risk_level']))
    print("-"*70)
    
    for suggestion in analysis['suggestions']:
        print(suggestion)
    
    print("\n" + "="*70)
    print("DISCLAIMER: This is for educational purposes only.")
    print("Always consult a financial advisor before making investment decisions.")
    print("="*70 + "\n")


def main():
    """Main function to run the analysis"""
    print("Starting Nifty 50 Trend Analysis...\n")
    
    # Fetch data
    df = fetch_nifty_data(days=100)
    
    # Calculate all indicators
    print("Calculating technical indicators...")
    df = calculate_moving_averages(df)
    df = calculate_rsi(df)
    df = calculate_macd(df)
    df = calculate_bollinger_bands(df)
    
    # Generate analysis and suggestions
    print("Analyzing trends...\n")
    analysis = generate_suggestions(df)
    
    # Print report
    print_analysis_report(df, analysis)
    
    # Export to CSV (optional)
    output_file = 'nifty_analysis.csv'
    df.to_csv(output_file)
    print("Full data exported to: {}".format(output_file))
    
    return df, analysis


if __name__ == "__main__":
    df, analysis = main()
    
    # Additional: Show last 5 days data
    print("\nLast 5 Days Summary:")
    print(df[['Open', 'High', 'Low', 'Close', 'RSI', 'MACD']].tail())