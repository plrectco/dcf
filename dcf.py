import yfinance as yf
import numpy as np
import argparse
import math

def get_risk_free_rate():
    treasury_yield10 = yf.Ticker("^TNX") 
    risk_free_rate = round(treasury_yield10.info['regularMarketPreviousClose']/100,2) 
    return risk_free_rate

def get_market_return():
    # Assume sp500 return 10% annually
    # Average S&P 500 return from 2013 to mid-2023 is 12.39% 
    # (9.48% adjusted for inflation), higher than the annual 
    # average of 10%.
    return 0.1

def get_wacc(stock):
    info = stock.info
    
    # Cost of equity
    risk_free_rate = get_risk_free_rate() 
    market_return = get_market_return()
    beta = info['beta']
    cost_of_equity = risk_free_rate + beta * (market_return - risk_free_rate)
    
    # Cost of debt
    stock_fin = stock.financials
    stock_bal = stock.balance_sheet
    total_debt = stock_bal.loc["Total Debt"].iloc[0]
    try:
        interest_expense = stock_fin.loc["Interest Expense"].iloc[0]
        if math.isnan(interest_expense):
            interest_expense = 0
    except:
        interest_expense = 0
    cost_of_debt = interest_expense / total_debt
    
    # Tax rate
    tax_provision = stock_fin.loc['Tax Provision'].iloc[0]
    pretax_income = stock_fin.loc['Pretax Income'].iloc[0]
    tax_rate = tax_provision / pretax_income
    
    # Weights
    market_cap = info['marketCap']
    total_value = market_cap + total_debt
    weight_equity = market_cap / total_value
    weight_debt = total_debt / total_value
    
    # WACC
    wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt * (1 - tax_rate))
    return wacc

def get_free_cash_flow(stock):
    fcf = stock.cashflow.loc['Free Cash Flow'].values[0]
    return fcf

def get_discount_rate(stock):
    return get_wacc(stock)

def get_growth_rate(stock, perpetual=False):
    # terminal growth rate is often 2-4% for mature companies
    return 0.03 if perpetual else stock.growth_estimates.loc['+1y']['stock']


def get_share_num(stock):
    return stock.info['sharesOutstanding']

def get_terminal_value(stock, years=10):
    fcf = get_free_cash_flow(stock)
    growth_rate = get_growth_rate(stock,perpetual=True)
    discount_rate = get_discount_rate(stock)
    
    terminal_value = fcf * (1 + growth_rate) ** years / (discount_rate - growth_rate)
    return terminal_value

def compute_dcf(ticker, years=10):
    stock = yf.Ticker(ticker)
    fcf = get_free_cash_flow(stock)
    discount_rate = get_discount_rate(stock)
    growth_rate = get_growth_rate(stock)
    print(f"Ticker: {ticker}")
    print(f"FCF: {fcf:.2f}, Discount Rate: {discount_rate:.2f}, Growth Rate: {growth_rate:.2f}")
    
    dcf_value = 0
    print("*" + "-"*7 + "*" + "-"*19 + "*")
    print(f"| {'Year':<5} | {'FCF (in millions)':<15} |")
    print("|" + "-"*7 + "|" + "-"*19 + "|")
    for year in range(1, years + 1):
        fcf_year = fcf * (1 + growth_rate) ** year
        print(f"| {year:<5} | {fcf_year/10**6:<17.2f} |")
        dcf_value += fcf_year / (1 + discount_rate) ** year
    print("*" + "-"*7 + "*" + "-"*19 + "*")
    terminal_value = get_terminal_value(stock, years)
    dcf_value += terminal_value
    cash = stock.balance_sheet.loc["Cash And Cash Equivalents"].iloc[0]
    total_debt = stock.balance_sheet.loc["Total Debt"].iloc[0]
    dcf_value = dcf_value + cash - total_debt
    print(f"Terminal Value: {terminal_value:.2f}, Cash: {cash:.2f}, Total Debt: {total_debt:.2f}")
    print(f"DCF Value (adjusted): {dcf_value:.2f}")
    share_num = get_share_num(stock)
    print(f"Number of Share: {share_num}")
    dcf_value_per_share = dcf_value / share_num
    print(f"The DCF per share value: {dcf_value_per_share:.2f}")
    print()
    return dcf_value_per_share

def current_sure_value(stock):
    price = stock.info['currentPrice']
    return price

def calculate_margin(ticker, years=10):
    stock = yf.Ticker(ticker)
    dcf_val = compute_dcf(ticker, years)
    current_val = current_sure_value(stock)
    return (current_val, round(dcf_val, 2).item(), round((dcf_val - current_val) / current_val, 2).item())

if __name__ == "__main__":
    # calculate_margin("INTA")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "years", 
        nargs=1,  
        help="Number of years to project cash flows"
    )
    parser.add_argument(
        "tickers",  # Positional argument name
        nargs="*",  # Accepts zero or more arguments
        help="A list of ticker symbols"
    )
    args = parser.parse_args()
    dcf = [(ticker, calculate_margin(ticker, int(args.years[0]))) for ticker in args.tickers]
    sorted_dcf = sorted(dcf, key=lambda x: x[1][2], reverse=True)
    print("*" + "-"*12 + "*" + "-"*17 + "*" + "-"*17 + "*"+ "-"*17 + "*")
    print(f"| {'Ticker':<10} | {'Current Value':<15} | {'DCF Value':<15} | {'Margin':<15} |")
    print("*" + "-"*12 + "*" + "-"*17 + "*" + "-"*17 + "*" + "-"*17 + "*")
    for ticker, (current_val, dcf_val, margin) in sorted_dcf:
        print(f"| {ticker:<10} | {current_val:<15.2f} | {dcf_val:<15.2f} | {margin:<15.2f} |")
    print("*" + "-"*12 + "*" + "-"*17 + "*" + "-"*17 + "*" + "-"*17 + "*")