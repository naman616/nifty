"""
Simple Stock Analysis Example
Shows how to use the StockAnalyzer class
"""

from stock_analyzer import StockAnalyzer
import matplotlib.pyplot as plt

# ============================================
# EXAMPLE 1: Basic Analysis
# ============================================
print("EXAMPLE 1: Analyzing AAPL stock")
print("="*50)

analyzer = StockAnalyzer('AAPL', period='3mo', interval='1d')

# Get summary statistics
summary = analyzer.get_summary()
for key, value in summary.items():
    print(f"{key}: {value}")

# ============================================
# EXAMPLE 2: Chart with Moving Averages
# ============================================
print("\n\nEXAMPLE 2: Chart with moving averages")
print("="*50)

fig = analyzer.plot_candlestick(
    show_volume=True,
    indicators=['SMA_20', 'SMA_50']
)
plt.savefig('/mnt/user-data/outputs/example2_ma.png', dpi=300, bbox_inches='tight')
print("Chart saved: example2_ma.png")
plt.close()

# ============================================
# EXAMPLE 3: Full Technical Analysis
# ============================================
print("\n\nEXAMPLE 3: Full technical analysis with all indicators")
print("="*50)

fig = analyzer.plot_candlestick(
    show_volume=True,
    indicators=['SMA_20', 'SMA_50', 'BB', 'RSI', 'MACD']
)
plt.savefig('/mnt/user-data/outputs/example3_full.png', dpi=300, bbox_inches='tight')
print("Chart saved: example3_full.png")
plt.close()

# ============================================
# EXAMPLE 4: Pattern Recognition
# ============================================
print("\n\nEXAMPLE 4: Candlestick pattern detection")
print("="*50)

patterns = analyzer.identify_patterns()
for pattern in patterns:
    print(f"• {pattern}")

# ============================================
# EXAMPLE 5: Different Stocks
# ============================================
print("\n\nEXAMPLE 5: Analyzing multiple stocks")
print("="*50)

tickers = ['MSFT', 'GOOGL', 'TSLA']

for ticker in tickers:
    print(f"\n{ticker}:")
    analyzer = StockAnalyzer(ticker, period='1mo', interval='1d')
    summary = analyzer.get_summary()
    print(f"  Latest Close: {summary['Latest Close']}")
    print(f"  Volume: {summary['Volume']}")

# ============================================
# EXAMPLE 6: Intraday Analysis (if available)
# ============================================
print("\n\nEXAMPLE 6: Intraday analysis (5-minute intervals)")
print("="*50)

try:
    intraday = StockAnalyzer('AAPL', period='1d', interval='5m')
    fig = intraday.plot_candlestick(show_volume=True, indicators=['EMA_20'])
    plt.savefig('/mnt/user-data/outputs/example6_intraday.png', dpi=300, bbox_inches='tight')
    print("Intraday chart saved: example6_intraday.png")
    plt.close()
except Exception as e:
    print(f"Intraday data not available: {e}")

print("\n" + "="*50)
print("All examples completed!")
print("="*50)
