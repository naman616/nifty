"""
Stock Candle and Graph Analysis Tool
Analyzes stock data with candlestick charts and technical indicators
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
from datetime import datetime, timedelta

class StockAnalyzer:
    def __init__(self, ticker, period='1y', interval='1d'):
        """
        Initialize stock analyzer
        
        Parameters:
        ticker (str): Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        period (str): Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval (str): Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        """
        self.ticker = ticker
        self.period = period
        self.interval = interval
        self.data = None
        self.load_data()
        
    def load_data(self):
        """Download stock data from Yahoo Finance"""
        print(f"Loading data for {self.ticker}...")
        stock = yf.Ticker(self.ticker)
        self.data = stock.history(period=self.period, interval=self.interval)
        
        if self.data.empty:
            raise ValueError(f"No data found for {self.ticker}")
        
        print(f"Loaded {len(self.data)} candles")
        return self.data
    
    def calculate_sma(self, period=20):
        """Calculate Simple Moving Average"""
        self.data[f'SMA_{period}'] = self.data['Close'].rolling(window=period).mean()
        return self.data[f'SMA_{period}']
    
    def calculate_ema(self, period=20):
        """Calculate Exponential Moving Average"""
        self.data[f'EMA_{period}'] = self.data['Close'].ewm(span=period, adjust=False).mean()
        return self.data[f'EMA_{period}']
    
    def calculate_rsi(self, period=14):
        """Calculate Relative Strength Index"""
        delta = self.data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        self.data['RSI'] = 100 - (100 / (1 + rs))
        return self.data['RSI']
    
    def calculate_macd(self, fast=12, slow=26, signal=9):
        """Calculate MACD (Moving Average Convergence Divergence)"""
        exp1 = self.data['Close'].ewm(span=fast, adjust=False).mean()
        exp2 = self.data['Close'].ewm(span=slow, adjust=False).mean()
        
        self.data['MACD'] = exp1 - exp2
        self.data['MACD_Signal'] = self.data['MACD'].ewm(span=signal, adjust=False).mean()
        self.data['MACD_Hist'] = self.data['MACD'] - self.data['MACD_Signal']
        
        return self.data['MACD'], self.data['MACD_Signal'], self.data['MACD_Hist']
    
    def calculate_bollinger_bands(self, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        sma = self.data['Close'].rolling(window=period).mean()
        std = self.data['Close'].rolling(window=period).std()
        
        self.data['BB_Upper'] = sma + (std * std_dev)
        self.data['BB_Middle'] = sma
        self.data['BB_Lower'] = sma - (std * std_dev)
        
        return self.data['BB_Upper'], self.data['BB_Middle'], self.data['BB_Lower']
    
    def calculate_atr(self, period=14):
        """Calculate Average True Range"""
        high_low = self.data['High'] - self.data['Low']
        high_close = np.abs(self.data['High'] - self.data['Close'].shift())
        low_close = np.abs(self.data['Low'] - self.data['Close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        
        self.data['ATR'] = true_range.rolling(period).mean()
        return self.data['ATR']
    
    def plot_candlestick(self, show_volume=True, indicators=None):
        """
        Plot candlestick chart with optional indicators
        
        Parameters:
        show_volume (bool): Show volume bars
        indicators (list): List of indicators to plot ['SMA_20', 'EMA_50', 'BB', 'RSI', 'MACD']
        """
        if indicators is None:
            indicators = []
        
        # Calculate requested indicators
        if 'SMA_20' in indicators or 'SMA_50' in indicators:
            self.calculate_sma(20)
            self.calculate_sma(50)
        if 'EMA_20' in indicators or 'EMA_50' in indicators:
            self.calculate_ema(20)
            self.calculate_ema(50)
        if 'BB' in indicators:
            self.calculate_bollinger_bands()
        if 'RSI' in indicators:
            self.calculate_rsi()
        if 'MACD' in indicators:
            self.calculate_macd()
        
        # Determine number of subplots
        num_plots = 1
        if show_volume:
            num_plots += 1
        if 'RSI' in indicators:
            num_plots += 1
        if 'MACD' in indicators:
            num_plots += 1
        
        # Create figure and subplots
        fig = plt.figure(figsize=(14, 4 * num_plots))
        plot_num = 1
        
        # Main candlestick chart
        ax1 = plt.subplot(num_plots, 1, plot_num)
        plot_num += 1
        
        # Plot candlesticks
        up = self.data[self.data['Close'] >= self.data['Open']]
        down = self.data[self.data['Close'] < self.data['Open']]
        
        width = 0.6
        width2 = 0.05
        
        # Up candles (green)
        ax1.bar(up.index, up['Close'] - up['Open'], width, bottom=up['Open'], color='green', alpha=0.8)
        ax1.bar(up.index, up['High'] - up['Close'], width2, bottom=up['Close'], color='green')
        ax1.bar(up.index, up['Open'] - up['Low'], width2, bottom=up['Low'], color='green')
        
        # Down candles (red)
        ax1.bar(down.index, down['Close'] - down['Open'], width, bottom=down['Open'], color='red', alpha=0.8)
        ax1.bar(down.index, down['High'] - down['Open'], width2, bottom=down['Open'], color='red')
        ax1.bar(down.index, down['Close'] - down['Low'], width2, bottom=down['Low'], color='red')
        
        # Plot moving averages
        if 'SMA_20' in indicators:
            ax1.plot(self.data.index, self.data['SMA_20'], label='SMA 20', linewidth=1.5, alpha=0.7)
        if 'SMA_50' in indicators:
            ax1.plot(self.data.index, self.data['SMA_50'], label='SMA 50', linewidth=1.5, alpha=0.7)
        if 'EMA_20' in indicators:
            ax1.plot(self.data.index, self.data['EMA_20'], label='EMA 20', linewidth=1.5, alpha=0.7)
        if 'EMA_50' in indicators:
            ax1.plot(self.data.index, self.data['EMA_50'], label='EMA 50', linewidth=1.5, alpha=0.7)
        
        # Plot Bollinger Bands
        if 'BB' in indicators:
            ax1.plot(self.data.index, self.data['BB_Upper'], label='BB Upper', linewidth=1, linestyle='--', alpha=0.5)
            ax1.plot(self.data.index, self.data['BB_Middle'], label='BB Middle', linewidth=1, alpha=0.5)
            ax1.plot(self.data.index, self.data['BB_Lower'], label='BB Lower', linewidth=1, linestyle='--', alpha=0.5)
            ax1.fill_between(self.data.index, self.data['BB_Upper'], self.data['BB_Lower'], alpha=0.1)
        
        ax1.set_title(f'{self.ticker} - Candlestick Chart', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Price ($)', fontsize=12)
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        # Volume subplot
        if show_volume:
            ax2 = plt.subplot(num_plots, 1, plot_num, sharex=ax1)
            plot_num += 1
            
            colors = ['green' if close >= open_ else 'red' 
                     for close, open_ in zip(self.data['Close'], self.data['Open'])]
            ax2.bar(self.data.index, self.data['Volume'], color=colors, alpha=0.6)
            ax2.set_ylabel('Volume', fontsize=12)
            ax2.grid(True, alpha=0.3)
        
        # RSI subplot
        if 'RSI' in indicators:
            ax3 = plt.subplot(num_plots, 1, plot_num, sharex=ax1)
            plot_num += 1
            
            ax3.plot(self.data.index, self.data['RSI'], color='purple', linewidth=1.5)
            ax3.axhline(70, color='red', linestyle='--', alpha=0.5, label='Overbought (70)')
            ax3.axhline(30, color='green', linestyle='--', alpha=0.5, label='Oversold (30)')
            ax3.fill_between(self.data.index, 30, 70, alpha=0.1, color='gray')
            ax3.set_ylabel('RSI', fontsize=12)
            ax3.set_ylim(0, 100)
            ax3.legend(loc='best')
            ax3.grid(True, alpha=0.3)
        
        # MACD subplot
        if 'MACD' in indicators:
            ax4 = plt.subplot(num_plots, 1, plot_num, sharex=ax1)
            plot_num += 1
            
            ax4.plot(self.data.index, self.data['MACD'], label='MACD', linewidth=1.5)
            ax4.plot(self.data.index, self.data['MACD_Signal'], label='Signal', linewidth=1.5)
            
            colors = ['green' if val >= 0 else 'red' for val in self.data['MACD_Hist']]
            ax4.bar(self.data.index, self.data['MACD_Hist'], label='Histogram', color=colors, alpha=0.4)
            
            ax4.set_ylabel('MACD', fontsize=12)
            ax4.legend(loc='best')
            ax4.grid(True, alpha=0.3)
        
        # Format x-axis
        plt.xlabel('Date', fontsize=12)
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        return fig
    
    def get_summary(self):
        """Get summary statistics of the stock"""
        latest = self.data.iloc[-1]
        
        summary = {
            'Ticker': self.ticker,
            'Latest Close': f"${latest['Close']:.2f}",
            'Open': f"${latest['Open']:.2f}",
            'High': f"${latest['High']:.2f}",
            'Low': f"${latest['Low']:.2f}",
            'Volume': f"{latest['Volume']:,.0f}",
            'Period High': f"${self.data['High'].max():.2f}",
            'Period Low': f"${self.data['Low'].min():.2f}",
            'Average Volume': f"{self.data['Volume'].mean():,.0f}",
        }
        
        return summary
    
    def identify_patterns(self):
        """Identify candlestick patterns"""
        patterns = []
        
        # Get last few candles
        df = self.data.tail(5).copy()
        
        for i in range(len(df)-1, 0, -1):
            curr = df.iloc[i]
            prev = df.iloc[i-1]
            
            body = abs(curr['Close'] - curr['Open'])
            range_ = curr['High'] - curr['Low']
            
            # Doji
            if body < range_ * 0.1:
                patterns.append(f"Doji at {curr.name.date()}")
            
            # Hammer/Hanging Man
            lower_wick = min(curr['Open'], curr['Close']) - curr['Low']
            upper_wick = curr['High'] - max(curr['Open'], curr['Close'])
            
            if lower_wick > body * 2 and upper_wick < body * 0.3:
                if curr['Close'] > curr['Open']:
                    patterns.append(f"Hammer at {curr.name.date()} (Bullish)")
                else:
                    patterns.append(f"Hanging Man at {curr.name.date()} (Bearish)")
            
            # Engulfing patterns
            if i > 0:
                curr_body = abs(curr['Close'] - curr['Open'])
                prev_body = abs(prev['Close'] - prev['Open'])
                
                if (curr['Close'] > curr['Open'] and prev['Close'] < prev['Open'] and
                    curr['Open'] < prev['Close'] and curr['Close'] > prev['Open']):
                    patterns.append(f"Bullish Engulfing at {curr.name.date()}")
                
                if (curr['Close'] < curr['Open'] and prev['Close'] > prev['Open'] and
                    curr['Open'] > prev['Close'] and curr['Close'] < prev['Open']):
                    patterns.append(f"Bearish Engulfing at {curr.name.date()}")
        
        return patterns if patterns else ["No significant patterns detected"]


# Example usage
if __name__ == "__main__":
    # Create analyzer for Apple stock
    ticker = "AAPL"
    analyzer = StockAnalyzer(ticker, period='6mo', interval='1d')
    
    # Get summary
    print("\n=== STOCK SUMMARY ===")
    summary = analyzer.get_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    # Identify patterns
    print("\n=== CANDLESTICK PATTERNS ===")
    patterns = analyzer.identify_patterns()
    for pattern in patterns:
        print(f"• {pattern}")
    
    # Plot with all indicators
    print("\n=== GENERATING CHART ===")
    fig = analyzer.plot_candlestick(
        show_volume=True,
        indicators=['SMA_20', 'SMA_50', 'BB', 'RSI', 'MACD']
    )
    
    # Save the chart
    output_file = f'/mnt/user-data/outputs/{ticker}_analysis.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Chart saved to {output_file}")
    
    # Show the plot
    plt.show()
