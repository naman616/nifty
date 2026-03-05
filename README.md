# Nifty 50 Trend Analyzer

A simple Python tool that analyzes Nifty 50 stock market trends and provides easy-to-understand investment suggestions. Perfect for beginners and experienced traders alike!

## What Does This Do?

This tool fetches real-time Nifty 50 data from Yahoo Finance, analyzes it using professional technical indicators, and tells you in simple language whether you should:
- **BUY** - Good time to invest
- **SELL** - Book profits or avoid investing
- **WAIT** - Market is unclear, better to wait

## Features

- Real-time Nifty 50 data from Yahoo Finance
- Technical analysis using RSI, MACD, Moving Averages, and Bollinger Bands
- Simple, easy-to-understand recommendations
- Automatic support and resistance level calculation
- Risk assessment for each recommendation
- Exports analysis to CSV and text files
- Works on Windows, Mac, and Linux

## Two Versions Available

### 1. **Technical Version** (`nifty_trend_analyzer_final.py`)
- Complete technical analysis with all indicators
- Detailed charts and metrics
- For users who understand stock market terminology
- Shows: RSI, MACD, Bollinger Bands, Moving Averages

### 2. **Simple Version** (`nifty_simple_analyzer.py`)
- Extremely easy to understand
- No technical jargon
- Perfect for beginners and all age groups
- Includes glossary of terms
- Step-by-step advice

## Installation

### Step 1: Install Python
Make sure you have Python 3.7 or higher installed on your computer.
Check by running:
```bash
python --version
```

### Step 2: Install Required Libraries
Open your terminal/command prompt and run:
```bash
pip install yfinance pandas numpy
```

Or if you're using Anaconda:
```bash
conda install -c conda-forge yfinance pandas numpy
```

## How to Use

### Method 1: Run from Terminal/Command Prompt

1. Download the Python file to your computer
2. Open terminal/command prompt
3. Navigate to the folder where you saved the file
4. Run the command:

**For Technical Version:**
```bash
python nifty_trend_analyzer_final.py
```

**For Simple Version:**
```bash
python nifty_simple_analyzer.py
```

### Method 2: Run from VS Code or Any Python IDE

1. Open the file in your IDE
2. Press the Run button or F5
3. View the output in the terminal

## Sample Output

### Technical Version Output:
```
======================================================================
NIFTY 50 TREND ANALYSIS REPORT
======================================================================
Analysis Date: 2024-03-05 10:30:00
Current Price: Rs. 22,150.50
Previous Close: Rs. 22,100.25
Change: Rs. +50.25 (+0.23%)

----------------------------------------------------------------------
TECHNICAL INDICATORS
----------------------------------------------------------------------
Trend: Strong Uptrend (Strong)
RSI (14): 58.45
MACD: 125.30
Signal Line: 110.20
SMA 20: Rs. 21,950.80
SMA 50: Rs. 21,750.40

----------------------------------------------------------------------
SUPPORT & RESISTANCE
----------------------------------------------------------------------
Resistance: Rs. 22,500.00
Current:    Rs. 22,150.50
Support:    Rs. 21,800.00

----------------------------------------------------------------------
RECOMMENDATION: BUY
Risk Level: Low-Medium
----------------------------------------------------------------------
[+] Strong bullish signals detected
[*] Consider buying near support level: Rs. 21,800.00
[>] Target resistance: Rs. 22,500.00
```

### Simple Version Output:
```
>>> TODAY'S PRICE <<<
Current Price:  Rs. 22,150.50
Yesterday:      Rs. 22,100.25
Change:         Rs. +50.25 (+0.23%) [+]

Today market is: UP

>>> MARKET TREND (Direction) <<<
Status: UPWARD TREND
What this means: Market is moving UP
Signal Color: GREEN

>>> RECOMMENDATION <<<
ACTION: BUY
ADVICE: Good time to invest
RISK LEVEL: LOW TO MEDIUM

>>> WHAT SHOULD YOU DO? <<<
1. This could be a good time to invest in Nifty
2. Market trend is positive
3. Consider buying in small amounts (SIP method)
4. Set a target near Rs. 22,500.00
```

## Understanding the Indicators

### RSI (Relative Strength Index)
- **Above 70**: Market is overbought (expensive) - might fall soon
- **Below 30**: Market is oversold (cheap) - might rise soon
- **30-70**: Normal price range

### Moving Averages (SMA)
- **SMA 20**: Average price over last 20 days (short-term trend)
- **SMA 50**: Average price over last 50 days (long-term trend)
- **Price above both**: Bullish (upward) trend
- **Price below both**: Bearish (downward) trend

### MACD (Moving Average Convergence Divergence)
- Shows momentum and trend strength
- **Positive MACD**: Bullish signal
- **Negative MACD**: Bearish signal

### Support & Resistance
- **Support**: Price level where market usually doesn't fall below
- **Resistance**: Price level where market struggles to cross

## Files Generated

After running the script, you'll get:

1. **nifty_analysis.csv** - Complete data with all indicators
2. **nifty_simple_report.txt** - Easy-to-read text report (Simple version only)

## Important Disclaimer

**THIS TOOL IS FOR EDUCATIONAL PURPOSES ONLY**

- Stock markets are risky - never invest money you can't afford to lose
- Past performance doesn't guarantee future results
- Always consult a certified financial advisor before making investment decisions
- This tool provides analysis, not financial advice
- Do your own research before investing

## Troubleshooting

### Error: "No module named 'yfinance'"
**Solution:** Install yfinance
```bash
pip install yfinance
```

### Error: "Can only compare identically-labeled Series objects"
**Solution:** Use the `nifty_trend_analyzer_final.py` file (this error is fixed in the final version)

### Error: Unicode encoding issues on Windows
**Solution:** All our files are Windows-compatible with no emoji characters

### Data not loading
**Solution:** 
- Check your internet connection
- Yahoo Finance might be temporarily down - try again after a few minutes

## System Requirements

- **Python**: 3.7 or higher
- **Internet**: Required to fetch real-time data
- **RAM**: 512 MB minimum
- **Storage**: 50 MB for libraries
- **OS**: Windows, macOS, or Linux

## Technical Details

### Data Source
- Yahoo Finance API via yfinance library
- Symbol: ^NSEI (Nifty 50)
- Historical data: Last 100 days

### Indicators Used
1. Simple Moving Average (20-day and 50-day)
2. Exponential Moving Average (12-day and 26-day)
3. Relative Strength Index (14-period)
4. MACD (Moving Average Convergence Divergence)
5. Bollinger Bands (20-period, 2 standard deviations)

### Recommendation Logic
- **BUY**: Bullish trend + RSI < 70 + Positive momentum
- **SELL**: Bearish trend OR RSI > 70 + Negative momentum
- **HOLD**: Mixed signals or sideways market

## Future Enhancements

Planned features for future versions:
- [ ] GUI interface
- [ ] Multiple stock support (not just Nifty)
- [ ] Email/SMS alerts
- [ ] Historical backtesting
- [ ] Machine learning predictions
- [ ] Mobile app version

## Contributing

Feel free to contribute to this project! You can:
- Report bugs
- Suggest new features
- Improve documentation
- Add new indicators

## License

This project is free to use for educational and personal purposes.

## Contact & Support

If you face any issues or have questions:
1. Check the Troubleshooting section above
2. Read the code comments for detailed explanations
3. Verify you're using the latest version

## Version History

- **v1.0** - Initial release with basic indicators
- **v1.1** - Fixed Windows Unicode issues
- **v1.2** - Fixed yfinance compatibility
- **v2.0** - Added Simple Version for beginners
- **v2.1** - Current version with enhanced error handling

## Credits

- Data provided by Yahoo Finance
- Built with Python, pandas, numpy
- Technical analysis based on standard trading indicators

---

**Remember: Smart investing comes from knowledge, not luck. Always learn, always research, and never invest blindly!**

---

Made with ❤️ for investors and traders
