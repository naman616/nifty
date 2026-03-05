import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


def fetch_stock_data(ticker, period='5y'):
    """
    Fetch historical stock data
    ticker: Stock symbol (e.g., 'AAPL', 'MSFT', '^NSEI', 'BTC-USD')
    period: '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'max'
    """
    print(f"Fetching data for {ticker}...")
    df = yf.download(ticker, period=period, progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    return df


def calculate_technical_indicators(df):
    """Calculate all technical indicators for ML features"""
    
    print("Calculating technical indicators...")
    
    # Moving Averages
    df['SMA_5'] = df['Close'].rolling(window=5).mean()
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    # RSI (Relative Strength Index)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
    
    # Bollinger Bands
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (2 * df['BB_Std'])
    df['BB_Lower'] = df['BB_Middle'] - (2 * df['BB_Std'])
    df['BB_Width'] = df['BB_Upper'] - df['BB_Lower']
    df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
    
    # Stochastic Oscillator
    low_14 = df['Low'].rolling(window=14).min()
    high_14 = df['High'].rolling(window=14).max()
    df['Stochastic_K'] = 100 * (df['Close'] - low_14) / (high_14 - low_14)
    df['Stochastic_D'] = df['Stochastic_K'].rolling(window=3).mean()
    
    # ATR (Average True Range) - Volatility
    df['TR'] = np.maximum(
        df['High'] - df['Low'],
        np.maximum(
            abs(df['High'] - df['Close'].shift(1)),
            abs(df['Low'] - df['Close'].shift(1))
        )
    )
    df['ATR'] = df['TR'].rolling(window=14).mean()
    
    # Price Rate of Change
    df['ROC'] = ((df['Close'] - df['Close'].shift(10)) / df['Close'].shift(10)) * 100
    
    # On-Balance Volume (OBV)
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    
    # Volume Moving Average
    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
    
    return df


def calculate_price_features(df):
    """Calculate price-based features"""
    
    print("Calculating price features...")
    
    # Price changes
    df['Price_Change'] = df['Close'].diff()
    df['Price_Change_Pct'] = df['Close'].pct_change() * 100
    
    # High-Low spread
    df['HL_Spread'] = df['High'] - df['Low']
    df['HL_Spread_Pct'] = (df['HL_Spread'] / df['Close']) * 100
    
    # Open-Close relationship
    df['OC_Spread'] = df['Close'] - df['Open']
    df['OC_Spread_Pct'] = (df['OC_Spread'] / df['Open']) * 100
    
    # Gap (difference between today's open and yesterday's close)
    df['Gap'] = df['Open'] - df['Close'].shift(1)
    df['Gap_Pct'] = (df['Gap'] / df['Close'].shift(1)) * 100
    
    # Price momentum
    df['Momentum_5'] = df['Close'] - df['Close'].shift(5)
    df['Momentum_10'] = df['Close'] - df['Close'].shift(10)
    df['Momentum_20'] = df['Close'] - df['Close'].shift(20)
    
    # Volatility (standard deviation of returns)
    df['Volatility_5'] = df['Close'].pct_change().rolling(window=5).std()
    df['Volatility_20'] = df['Close'].pct_change().rolling(window=20).std()
    
    return df


def create_target_variables(df, prediction_days=1):
    """
    Create target variables for ML
    prediction_days: How many days ahead to predict
    """
    
    print(f"Creating target variables (predicting {prediction_days} days ahead)...")
    
    # Future price (shifted backwards)
    df['Future_Close'] = df['Close'].shift(-prediction_days)
    
    # Price will go up or down (Binary classification)
    df['Target_Up_Down'] = (df['Future_Close'] > df['Close']).astype(int)
    
    # Price change percentage (Regression)
    df['Target_Price_Change_Pct'] = ((df['Future_Close'] - df['Close']) / df['Close']) * 100
    
    # Multi-class classification (Strong Down, Down, Neutral, Up, Strong Up)
    def classify_movement(pct_change):
        if pd.isna(pct_change):
            return np.nan
        elif pct_change < -2:
            return 0  # Strong Down
        elif pct_change < -0.5:
            return 1  # Down
        elif pct_change < 0.5:
            return 2  # Neutral
        elif pct_change < 2:
            return 3  # Up
        else:
            return 4  # Strong Up
    
    df['Target_Movement_Class'] = df['Target_Price_Change_Pct'].apply(classify_movement)
    
    return df


def add_time_features(df):
    """Add time-based features"""
    
    print("Adding time features...")
    
    df['Day_of_Week'] = df.index.dayofweek  # Monday=0, Sunday=6
    df['Day_of_Month'] = df.index.day
    df['Week_of_Year'] = df.index.isocalendar().week
    df['Month'] = df.index.month
    df['Quarter'] = df.index.quarter
    df['Year'] = df.index.year
    
    # Is it beginning/end of month?
    df['Is_Month_Start'] = (df.index.day <= 5).astype(int)
    df['Is_Month_End'] = (df.index.day >= 25).astype(int)
    
    return df


def clean_dataset(df):
    """Clean the dataset - remove NaN values and infinities"""
    
    print("Cleaning dataset...")
    
    # Replace infinities with NaN
    df = df.replace([np.inf, -np.inf], np.nan)
    
    # Drop rows with NaN in target variables
    target_cols = ['Target_Up_Down', 'Target_Price_Change_Pct', 'Target_Movement_Class']
    df = df.dropna(subset=target_cols)
    
    # For feature columns, fill NaN with forward fill then backward fill
    df = df.fillna(method='ffill').fillna(method='bfill')
    
    # Drop any remaining rows with NaN
    df = df.dropna()
    
    return df


def generate_ml_dataset(ticker, period='5y', prediction_days=1, save_csv=True):
    """
    Main function to generate complete ML dataset
    
    Parameters:
    - ticker: Stock symbol (e.g., 'AAPL', '^NSEI', 'BTC-USD')
    - period: Time period ('1y', '2y', '5y', '10y', 'max')
    - prediction_days: Days ahead to predict (1, 5, 10, etc.)
    - save_csv: Whether to save as CSV file
    
    Returns:
    - DataFrame with all features and targets
    """
    
    print("\n" + "="*70)
    print("FINANCIAL DATASET GENERATOR FOR MACHINE LEARNING")
    print("="*70)
    print(f"Ticker: {ticker}")
    print(f"Period: {period}")
    print(f"Prediction Days: {prediction_days}")
    print("="*70 + "\n")
    
    # Step 1: Fetch data
    df = fetch_stock_data(ticker, period)
    
    if df.empty:
        print(f"Error: No data found for {ticker}")
        return None
    
    # Step 2: Calculate indicators
    df = calculate_technical_indicators(df)
    df = calculate_price_features(df)
    df = add_time_features(df)
    
    # Step 3: Create targets
    df = create_target_variables(df, prediction_days)
    
    # Step 4: Clean dataset
    df = clean_dataset(df)
    
    print("\n" + "="*70)
    print("DATASET SUMMARY")
    print("="*70)
    print(f"Total rows: {len(df)}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Date range: {df.index[0].date()} to {df.index[-1].date()}")
    print(f"Features: {len(df.columns) - 3} (excluding 3 target variables)")
    print("\nTarget Variables:")
    print("  1. Target_Up_Down (Binary: 0=Down, 1=Up)")
    print("  2. Target_Price_Change_Pct (Regression: % change)")
    print("  3. Target_Movement_Class (Multi-class: 0-4)")
    
    # Class distribution
    print("\nClass Distribution (Up/Down):")
    print(df['Target_Up_Down'].value_counts())
    
    print("\nMovement Class Distribution:")
    movement_labels = {0: 'Strong Down', 1: 'Down', 2: 'Neutral', 3: 'Up', 4: 'Strong Up'}
    for idx, label in movement_labels.items():
        count = (df['Target_Movement_Class'] == idx).sum()
        print(f"  {idx} ({label}): {count}")
    
    # Save to CSV
    if save_csv:
        filename = f'{ticker.replace("^", "").replace("-", "_")}_ml_dataset.csv'
        df.to_csv(filename)
        print(f"\n[SUCCESS] Dataset saved to: {filename}")
    
    print("="*70 + "\n")
    
    return df


def generate_multiple_stocks_dataset(tickers, period='5y', prediction_days=1):
    """Generate dataset for multiple stocks/assets"""
    
    print("Generating dataset for multiple assets...")
    
    all_data = []
    
    for ticker in tickers:
        print(f"\nProcessing {ticker}...")
        df = generate_ml_dataset(ticker, period, prediction_days, save_csv=False)
        if df is not None:
            df['Ticker'] = ticker  # Add ticker column
            all_data.append(df)
    
    # Combine all datasets
    combined_df = pd.concat(all_data, axis=0)
    
    # Save combined dataset
    filename = f'combined_stocks_ml_dataset.csv'
    combined_df.to_csv(filename)
    print(f"\n[SUCCESS] Combined dataset saved to: {filename}")
    print(f"Total rows: {len(combined_df)}")
    print(f"Total stocks: {len(tickers)}")
    
    return combined_df


# Example usage functions
def example_single_stock():
    """Example: Generate dataset for single stock"""
    df = generate_ml_dataset(
        ticker='AAPL',      # Apple stock
        period='5y',         # 5 years of data
        prediction_days=1    # Predict next day
    )
    return df


def example_nifty():
    """Example: Generate dataset for Nifty 50"""
    df = generate_ml_dataset(
        ticker='^NSEI',      # Nifty 50
        period='5y',
        prediction_days=1
    )
    return df


def example_bitcoin():
    """Example: Generate dataset for Bitcoin"""
    df = generate_ml_dataset(
        ticker='BTC-USD',    # Bitcoin
        period='5y',
        prediction_days=1
    )
    return df


def example_multiple_stocks():
    """Example: Generate combined dataset for multiple stocks"""
    tickers = [
        'AAPL',      # Apple
        'MSFT',      # Microsoft
        'GOOGL',     # Google
        'TSLA',      # Tesla
        '^NSEI',     # Nifty 50
        'BTC-USD'    # Bitcoin
    ]
    
    df = generate_multiple_stocks_dataset(
        tickers=tickers,
        period='5y',
        prediction_days=1
    )
    return df


if __name__ == "__main__":
    print("\nFINANCIAL DATASET GENERATOR")
    print("Choose an option:")
    print("1. Generate for single stock (Apple)")
    print("2. Generate for Nifty 50")
    print("3. Generate for Bitcoin")
    print("4. Generate for multiple assets")
    print("5. Custom ticker\n")
    
    choice = input("Enter choice (1-5): ").strip()
    
    if choice == '1':
        df = example_single_stock()
    elif choice == '2':
        df = example_nifty()
    elif choice == '3':
        df = example_bitcoin()
    elif choice == '4':
        df = example_multiple_stocks()
    elif choice == '5':
        ticker = input("Enter ticker symbol (e.g., AAPL, ^NSEI, BTC-USD): ").strip()
        df = generate_ml_dataset(ticker, period='5y', prediction_days=1)
    else:
        print("Invalid choice!")
        df = None
    
    if df is not None:
        print("\nDataset generated successfully!")
        print("\nFirst few rows:")
        print(df.head())
        print("\nColumn names:")
        print(df.columns.tolist())
