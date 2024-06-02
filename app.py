from flask import Flask, render_template, request, jsonify
import yfinance as yf
import os
import io
import base64
import matplotlib
from matplotlib.ticker import FuncFormatter

# Set the backend to Agg
matplotlib.use('agg')

# Importing pyplot after setting the backend
import matplotlib.pyplot as plt

app = Flask(__name__)


# Function to read stock tickers from a text file
def read_stock_list(filename):
    with open(filename, 'r') as file:
        stock_list = [line.strip() for line in file if line.strip()]
    return stock_list

# Read stock tickers from the text file
stock_list = read_stock_list('tickers.txt')

def fetch_stock_info(ticker):
    stock = yf.Ticker(ticker)
    return stock.info

def fetch_balance_sheet(ticker, ticker_folder):
    try:
        # Get the stock data for the ticker
        stock = yf.Ticker(ticker)
        
        # Get the balance_sheet
        balance_sheet = stock.get_balance_sheet().reset_index()

        # Save balance sheet to a file
        #balance_sheet_filename = os.path.join(ticker_folder, "balance_sheet.json")
        #balance_sheet.to_json(balance_sheet_filename, orient='records', date_format='iso')

        return balance_sheet

    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

def visualize_balance_sheet(balance_sheet, ticker):
    years = balance_sheet.columns[1:-1][::-1]  # Reverse the order of years

    # Prepare data for plotting
    plots = []
    for year in years:
        liabilities = balance_sheet.loc[balance_sheet['index'] == 'TotalLiabilitiesNetMinorityInterest', year].values[0]
        assets = balance_sheet.loc[balance_sheet['index'] == 'TotalAssets', year].values[0]
        equity = balance_sheet.loc[balance_sheet['index'] == 'StockholdersEquity', year].values[0]

        # Plot
        fig, ax = plt.subplots(figsize=(8, 6))
        assets_bar = ax.bar(0, assets, color='blue', label='Assets')
        liabilities_bar = ax.bar(1, liabilities, color='red', label='Liabilities')
        equity_bar = ax.bar(1, equity, bottom=liabilities, color='green', label='Equity')

        ax.set_xlabel('Category')
        ax.set_ylabel('Amount ($M)')  # Adjust axis label
        ax.set_title(f'Balance Sheet for {year} - Ticker: {ticker}'.replace('00:00:00',''))
        ax.set_xticks([0, 1])
        ax.set_xticklabels(['Assets', 'Liabilities + Equity'])
        ax.legend()

        # Add numbers inside the bars
        plt.text(0, assets / 2, '${:,.0f}M'.format(assets/1e6), ha='center', va='center', color='white', fontsize=20)
        plt.text(1, liabilities / 2, '${:,.0f}M'.format(liabilities/1e6), ha='center', va='center', color='white', fontsize=20)
        plt.text(1, liabilities + equity / 2, '${:,.0f}M'.format(equity/1e6), ha='center', va='center', color='white', fontsize=20)
        
        # Format y-axis tick labels as money in billions
        plt.gca().yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'${x/1e6:,.1f}M'))
        plt.tight_layout()

        # Save the plot as a bytes object
        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
        plt.close()

        plots.append({'year': year, 'plot_url': plot_url, 'assets': f'${assets/1e6:,.1f}M', 'liabilities': f'${liabilities/1e6:,.1f}M'})

    return plots

@app.route('/suggestions')
def get_suggestions():
    ticker_prefix = request.args.get('ticker', '').upper()
    matching_tickers = [ticker for ticker in stock_list if ticker.startswith(ticker_prefix)]
    return jsonify(matching_tickers[:10])  # Return up to 10 matching tickers as suggestions

@app.route('/', methods=['GET', 'POST'])
def index():
    stock_info = {}
    if request.method == 'POST':
        ticker = request.form['ticker']

        try:
            ticker_folder = '.'  # Folder to save the balance sheet
            balance_sheet = fetch_balance_sheet(ticker, ticker_folder)
            stock_info = fetch_stock_info(ticker)
            if balance_sheet is not None:
                plots = visualize_balance_sheet(balance_sheet, ticker)
                return render_template('index.html', plots=plots, ticker=ticker, stock_list=stock_list, stock_info=stock_info)
            else:
                error_message = f"Error fetching balance sheet for {ticker}. Please try again."
                return render_template('index.html', error_message=error_message, stock_list=stock_list, stock_info=stock_info)
        except:
            print("exception")
    return render_template('index.html', stock_list=stock_list, stock_info=stock_info)

if __name__ == '__main__':
    app.run(debug=True)