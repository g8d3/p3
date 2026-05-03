import streamlit as st
import yfinance as yf

st.set_page_config(page_title="My Watchlist", layout="wide")
symbols = ["AAPL", "TSLA", "BTC-USD", "NVDA"] # Add your stocks here

st.title("🚀 Minimalist Watchlist")

for ticker in symbols:
    data = yf.Ticker(ticker).history(period="1d")
    price = data['Close'].iloc[-1]
    change = price - data['Open'].iloc[-1]
    
    col1, col2 = st.columns([1, 3])
    col1.metric(ticker, f"${price:.2f}", f"{change:.2f}")
