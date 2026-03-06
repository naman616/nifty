import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sys

def format_large_number(num):
    """Format large numbers in readable format (B for billions, M for millions)"""
    if num is None or pd.isna(num):
        return "N/A"
    
    if abs(num) >= 1e12:
        return f"${num/1e12:.2f}T"
    elif abs(num) >= 1e9:
        return f"${num/1e9:.2f}B"
    elif abs(num) >= 1e6:
        return f"${num/1e6:.2f}M"
    elif abs(num) >= 1e3:
        return f"${num/1e3:.2f}K"
    else:
        return f"${num:.2f}"

def get_stock_data(company_name):
    """Fetch stock data for the given company"""
    try:
        stock = yf.Ticker(company_name)
        info = stock.info
        
        # Check if we got valid data
        if not info or 'symbol' not in info:
            return None, "Could not find stock data. Please check the ticker symbol."
        
        return stock, None
    except Exception as e:
        return None, f"Error fetching data: {str(e)}"

def calculate_revenue_growth(stock):
    """Calculate revenue growth rate"""
    try:
        financials = stock.financials
        if financials is None or financials.empty:
            return None, None
        
        # Get revenue rows (Total Revenue or Revenue)
        revenue_row = None
        for index in financials.index:
            if 'Total Revenue' in str(index) or 'Revenue' in str(index):
                revenue_row = financials.loc[index]
                break
        
        if revenue_row is None or len(revenue_row) < 2:
            return None, None
        
        # Calculate year-over-year growth
        revenue_values = revenue_row.sort_index()
        if len(revenue_values) >= 2:
            latest_revenue = revenue_values.iloc[-1]
            previous_revenue = revenue_values.iloc[-2]
            
            if previous_revenue != 0:
                growth_rate = ((latest_revenue - previous_revenue) / abs(previous_revenue)) * 100
                return growth_rate, latest_revenue
        
        return None, revenue_values.iloc[-1] if len(revenue_values) > 0 else None
    except Exception as e:
        return None, None

def analyze_stock(company_ticker):
    """Main function to analyze stock"""
    print("\n" + "="*70)
    print(f"📊 STOCK ANALYSIS REPORT")
    print("="*70)
    
    # Fetch stock data
    stock, error = get_stock_data(company_ticker)
    
    if error:
        print(f"\n❌ {error}")
        print("\nTip: Use the stock ticker symbol (e.g., AAPL for Apple, MSFT for Microsoft)")
        return
    
    info = stock.info
    
    # Company Information
    print(f"\n🏢 COMPANY: {info.get('longName', company_ticker.upper())}")
    print(f"📍 Sector: {info.get('sector', 'N/A')}")
    print(f"🏭 Industry: {info.get('industry', 'N/A')}")
    print(f"🌍 Country: {info.get('country', 'N/A')}")
    
    # Current Price
    current_price = info.get('currentPrice') or info.get('regularMarketPrice')
    print(f"\n💵 Current Price: ${current_price:.2f}" if current_price else "\n💵 Current Price: N/A")
    
    # Market Cap
    market_cap = info.get('marketCap')
    if market_cap:
        print(f"📈 Market Cap: {format_large_number(market_cap)}")
    
    print("\n" + "-"*70)
    print("📊 KEY FINANCIAL METRICS")
    print("-"*70)
    
    # 1. Revenue Growth
    revenue_growth, latest_revenue = calculate_revenue_growth(stock)
    print(f"\n1️⃣  REVENUE GROWTH:")
    if latest_revenue:
        print(f"    Latest Revenue: {format_large_number(latest_revenue)}")
    if revenue_growth is not None:
        print(f"    YoY Growth: {revenue_growth:+.2f}%")
        if revenue_growth > 15:
            print(f"    ✅ Strong growth - Very Positive")
        elif revenue_growth > 5:
            print(f"    ✓ Moderate growth - Positive")
        elif revenue_growth > 0:
            print(f"    ⚠️ Slow growth - Neutral")
        else:
            print(f"    ❌ Declining revenue - Negative")
    else:
        print(f"    Data not available")
    
    # 2. Profit Margins
    print(f"\n2️⃣  PROFIT MARGINS:")
    gross_margin = info.get('grossMargins')
    operating_margin = info.get('operatingMargins')
    profit_margin = info.get('profitMargins')
    
    if gross_margin:
        print(f"    Gross Margin: {gross_margin*100:.2f}%")
    if operating_margin:
        print(f"    Operating Margin: {operating_margin*100:.2f}%")
    if profit_margin:
        print(f"    Net Profit Margin: {profit_margin*100:.2f}%")
        if profit_margin > 0.20:
            print(f"    ✅ Excellent profitability")
        elif profit_margin > 0.10:
            print(f"    ✓ Good profitability")
        elif profit_margin > 0:
            print(f"    ⚠️ Low profitability")
        else:
            print(f"    ❌ Not profitable")
    
    # 3. Debt Levels
    print(f"\n3️⃣  DEBT LEVELS:")
    debt_to_equity = info.get('debtToEquity')
    total_debt = info.get('totalDebt')
    total_cash = info.get('totalCash')
    
    if debt_to_equity is not None:
        print(f"    Debt-to-Equity Ratio: {debt_to_equity:.2f}")
        if debt_to_equity < 50:
            print(f"    ✅ Low debt - Very healthy")
        elif debt_to_equity < 100:
            print(f"    ✓ Moderate debt - Acceptable")
        elif debt_to_equity < 200:
            print(f"    ⚠️ High debt - Caution advised")
        else:
            print(f"    ❌ Very high debt - Risky")
    
    if total_debt:
        print(f"    Total Debt: {format_large_number(total_debt)}")
    if total_cash:
        print(f"    Total Cash: {format_large_number(total_cash)}")
        net_debt = (total_debt or 0) - total_cash
        print(f"    Net Debt: {format_large_number(net_debt)}")
    
    # 4. Return on Equity (ROE)
    print(f"\n4️⃣  RETURN ON EQUITY (ROE):")
    roe = info.get('returnOnEquity')
    if roe is not None:
        print(f"    ROE: {roe*100:.2f}%")
        if roe > 0.20:
            print(f"    ✅ Excellent returns - Management is efficient")
        elif roe > 0.15:
            print(f"    ✓ Good returns - Above average")
        elif roe > 0.10:
            print(f"    ⚠️ Average returns")
        else:
            print(f"    ❌ Poor returns - Below average")
    else:
        print(f"    Data not available")
    
    # 5. P/E Ratio
    print(f"\n5️⃣  PRICE-TO-EARNINGS (P/E) RATIO:")
    pe_ratio = info.get('trailingPE') or info.get('forwardPE')
    if pe_ratio is not None:
        print(f"    P/E Ratio: {pe_ratio:.2f}")
        if pe_ratio < 15:
            print(f"    ✅ Potentially undervalued")
        elif pe_ratio < 25:
            print(f"    ✓ Fair valuation")
        elif pe_ratio < 40:
            print(f"    ⚠️ Premium valuation - growth expected")
        else:
            print(f"    ❌ Very high valuation - speculative")
    else:
        print(f"    Data not available")
    
    # Additional Metrics
    print(f"\n📌 ADDITIONAL METRICS:")
    
    beta = info.get('beta')
    if beta is not None:
        print(f"    Beta (Volatility): {beta:.2f}")
        if beta > 1.5:
            print(f"      (High volatility - Very risky)")
        elif beta > 1:
            print(f"      (More volatile than market)")
        else:
            print(f"      (Less volatile than market)")
    
    dividend_yield = info.get('dividendYield')
    if dividend_yield:
        print(f"    Dividend Yield: {dividend_yield*100:.2f}%")
    
    # 52-week range
    fifty_two_week_low = info.get('fiftyTwoWeekLow')
    fifty_two_week_high = info.get('fiftyTwoWeekHigh')
    if current_price and fifty_two_week_low and fifty_two_week_high:
        range_position = ((current_price - fifty_two_week_low) / (fifty_two_week_high - fifty_two_week_low)) * 100
        print(f"    52-Week Range: ${fifty_two_week_low:.2f} - ${fifty_two_week_high:.2f}")
        print(f"    Current position: {range_position:.1f}% of range")
    
    # Investment Recommendation
    print("\n" + "="*70)
    print("🎯 INVESTMENT ANALYSIS & RECOMMENDATION")
    print("="*70)
    
    # Calculate risk score
    risk_score = 0
    positive_factors = []
    negative_factors = []
    
    # Revenue growth check
    if revenue_growth is not None:
        if revenue_growth > 10:
            positive_factors.append("Strong revenue growth")
        elif revenue_growth < 0:
            negative_factors.append("Declining revenue")
            risk_score += 1
    
    # Profitability check
    if profit_margin is not None:
        if profit_margin > 0.15:
            positive_factors.append("High profit margins")
        elif profit_margin < 0:
            negative_factors.append("Company is not profitable")
            risk_score += 2
    
    # Debt check
    if debt_to_equity is not None:
        if debt_to_equity < 50:
            positive_factors.append("Low debt levels")
        elif debt_to_equity > 150:
            negative_factors.append("High debt burden")
            risk_score += 1
    
    # ROE check
    if roe is not None:
        if roe > 0.15:
            positive_factors.append("Strong return on equity")
        elif roe < 0.05:
            negative_factors.append("Weak return on equity")
            risk_score += 1
    
    # P/E check
    if pe_ratio is not None:
        if pe_ratio < 20:
            positive_factors.append("Reasonable valuation")
        elif pe_ratio > 50:
            negative_factors.append("Very high valuation - speculative")
            risk_score += 1
    
    # Beta check
    if beta is not None and beta > 1.5:
        negative_factors.append("High volatility")
        risk_score += 1
    
    print("\n✅ POSITIVE FACTORS:")
    if positive_factors:
        for factor in positive_factors:
            print(f"    • {factor}")
    else:
        print("    • Limited positive indicators found")
    
    print("\n⚠️ RISK FACTORS:")
    if negative_factors:
        for factor in negative_factors:
            print(f"    • {factor}")
    else:
        print("    • No major risk factors identified")
    
    # Overall recommendation
    print("\n🎖️ OVERALL RECOMMENDATION:")
    
    if risk_score == 0:
        risk_level = "LOW RISK"
        recommendation = "BUY"
        color = "🟢"
    elif risk_score <= 2:
        risk_level = "MODERATE RISK"
        recommendation = "HOLD / CAUTIOUS BUY"
        color = "🟡"
    else:
        risk_level = "HIGH RISK"
        recommendation = "AVOID / WAIT"
        color = "🔴"
    
    print(f"\n    {color} Risk Level: {risk_level}")
    print(f"    {color} Recommendation: {recommendation}")
    
    print("\n📝 INVESTMENT TIPS:")
    print("    • Diversify your portfolio - don't put all eggs in one basket")
    print("    • Consider your investment timeline (long-term vs short-term)")
    print("    • Stay updated on company news and market conditions")
    print("    • This analysis is based on historical data - past performance")
    print("      doesn't guarantee future results")
    print("    • Consult with a financial advisor for personalized advice")
    
    print("\n" + "="*70)
    print(f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")

def main():
    print("\n" + "="*70)
    print("🚀 WELCOME TO STOCK ANALYZER")
    print("="*70)
    print("\nThis tool provides comprehensive stock analysis including:")
    print("  • Revenue growth trends")
    print("  • Profit margins")
    print("  • Debt levels")
    print("  • Return on Equity (ROE)")
    print("  • Price-to-Earnings (P/E) ratio")
    print("  • Investment recommendations")
    
    while True:
        print("\n" + "-"*70)
        company_ticker = input("\n📝 Enter company ticker symbol (e.g., AAPL, MSFT, GOOGL) or 'quit' to exit: ").strip().upper()
        
        if company_ticker.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Thank you for using Stock Analyzer!")
            break
        
        if not company_ticker:
            print("❌ Please enter a valid ticker symbol")
            continue
        
        analyze_stock(company_ticker)
        
        print("\n" + "-"*70)
        another = input("Would you like to analyze another stock? (yes/no): ").strip().lower()
        if another not in ['yes', 'y']:
            print("\n👋 Thank you for using Stock Analyzer!")
            break

if __name__ == "__main__":
    main()
