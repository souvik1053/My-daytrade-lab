# 📈 My-daytrade-lab – A Smart Backtesting Strategy with Streamlit

This project implements a backtesting tool for a high-probability trading strategy that enters trades at the **71% Fibonacci retracement level** after a **Break of Structure (BoS)** confirmation. It's designed for Forex and adaptable to other asset classes like crypto or indices.

Built with **Python, Streamlit, Plotly**, and **Pandas** — this tool lets you visualize all trades on real market data, see live equity curves, and test different R:R setups.

---

## 🔍 Strategy Overview

- **Trend Identification:** Based on 4H market structure (higher highs/lows or lower lows/highs).
- **Entry Logic:** Enter on 15-minute chart after a break of 2-candle structure and price retracement to 71% zone.
- **Stop Loss & Take Profit:** Dynamic SL/TP based on user-defined Risk:Reward ratio.
- **Capital Management:** 1% risk per trade.
- **Visuals:** All trades plotted on interactive 15-minute candlestick charts.

---

## 🚀 Features

- 📂 Upload your own 4H and 15m OHLCV `.csv` data
- 🎯 Simulate entries at 71% Fibonacci zone
- 📊 Visualize all trades with Plotly on real candlestick charts
- 💰 Customize initial balance and risk-to-reward ratio
- 🧠 Detects Bullish or Bearish BoS automatically
- ✅ Works with any asset (Forex, Crypto, Stocks) if in correct format

---

## 🌍 Try It Live
 Link: https://my-daytrade-lab.streamlit.app/
