import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- Upload Section ---
st.title("📊 Multi-timeframe + 71% Zone Backtester")

st.sidebar.header("📁 Upload CSV Files")
uploaded_4h = st.sidebar.file_uploader("Upload 4H Data (CSV)", type="csv")
uploaded_15m = st.sidebar.file_uploader("Upload 15m Data (CSV)", type="csv")

if not uploaded_4h or not uploaded_15m:
    st.warning("Please upload both 4H and 15m CSV files to begin.")
    st.stop()

# --- Load Data ---
@st.cache_data
def load_data(uploaded_4h, uploaded_15m):
    df_4h = pd.read_csv(uploaded_4h, sep="\t")
    df_15m = pd.read_csv(uploaded_15m, sep="\t")

    df_4h['Date'] = pd.to_datetime(df_4h['<DATE>'] + ' ' + df_4h['<TIME>'], format='%Y.%m.%d %H:%M:%S')
    df_15m['Date'] = pd.to_datetime(df_15m['<DATE>'] + ' ' + df_15m['<TIME>'], format='%Y.%m.%d %H:%M:%S')

    df_4h = df_4h.rename(columns={"<OPEN>": "Open", "<HIGH>": "High", "<LOW>": "Low", "<CLOSE>": "Close"})
    df_15m = df_15m.rename(columns={"<OPEN>": "Open", "<HIGH>": "High", "<LOW>": "Low", "<CLOSE>": "Close"})

    df_4h.sort_values("Date", inplace=True)
    df_15m.set_index("Date", inplace=True)
    
    return df_4h, df_15m

# --- Detect Market Structure ---
def detect_structure(df):
    trend = [None] * len(df)
    highs = df["High"].values
    lows = df["Low"].values
    for i in range(2, len(df)):
        if highs[i] > highs[i-1] > highs[i-2] and lows[i] > lows[i-1] > lows[i-2]:
            trend[i] = "Bullish"
        elif highs[i] < highs[i-1] < highs[i-2] and lows[i] < lows[i-1] < lows[i-2]:
            trend[i] = "Bearish"
    df["Trend"] = trend
    return df

# --- Sidebar Settings ---
rr_ratio = st.sidebar.slider("Risk-Reward Ratio", 1.0, 5.0, 2.45, 0.05)
initial_balance = st.sidebar.number_input("Initial Balance ($)", value=10000, step=500)

# --- Main Info ---
st.info("Backtesting strategy: Enter at 71% retracement after market structure shift (BoS).")

# --- Load and Process Data ---
df_4h, df_15m = load_data(uploaded_4h, uploaded_15m)
df_4h = detect_structure(df_4h)

balance = initial_balance
equity_curve = [balance]
positions = []

# --- Backtest Loop ---
for i in range(3, len(df_4h)):
    row = df_4h.iloc[i]
    bias = row["Trend"]
    if pd.isna(bias):
        continue

    fib_low, fib_high = (row["Low"], row["High"]) if bias == "Bullish" else (row["High"], row["Low"])
    fib_50 = fib_low + 0.5 * (fib_high - fib_low)
    current_price = row["Close"]
    
    if (bias == "Bullish" and current_price >= fib_50) or (bias == "Bearish" and current_price <= fib_50):
        equity_curve.append(balance)
        continue

    start_time = row["Date"]
    end_time = start_time + pd.Timedelta(hours=8)
    next_15m = df_15m.loc[start_time:end_time]

    closes = next_15m["Close"].values
    highs = next_15m["High"].values
    lows = next_15m["Low"].values
    dates = next_15m.index.to_numpy()

    for j in range(2, len(next_15m)):
        if (closes[j] > highs[j-2]) if bias == "Bullish" else (closes[j] < lows[j-2]):
            fib15_hl = lows[j-2]
            fib15_hh = highs[j]

            if bias == "Bullish":
                entry = fib15_hl + 0.71 * (fib15_hh - fib15_hl)
                sl_price = fib15_hl
                tp_price = entry + (entry - sl_price) * rr_ratio
            else:
                entry = fib15_hh - 0.71 * (fib15_hh - fib15_hl)
                sl_price = fib15_hh
                tp_price = entry - (sl_price - entry) * rr_ratio

            for k in range(j+1, min(j+100, len(next_15m))):
                if bias == "Bullish":
                    if lows[k] <= sl_price:
                        balance -= balance * 0.01
                        equity_curve.append(balance)
                        positions.append({
                            "time": str(dates[j]), "bias": bias, "entry": entry,
                            "tp": tp_price, "sl": sl_price, "result": "SL"
                        })
                        break
                    elif highs[k] >= tp_price:
                        balance += balance * 0.01 * rr_ratio
                        equity_curve.append(balance)
                        positions.append({
                            "time": str(dates[j]), "bias": bias, "entry": entry,
                            "tp": tp_price, "sl": sl_price, "result": "TP"
                        })
                        break
                else:
                    if highs[k] >= sl_price:
                        balance -= balance * 0.01
                        equity_curve.append(balance)
                        positions.append({
                            "time": str(dates[j]), "bias": bias, "entry": entry,
                            "tp": tp_price, "sl": sl_price, "result": "SL"
                        })
                        break
                    elif lows[k] <= tp_price:
                        balance += balance * 0.01 * rr_ratio
                        equity_curve.append(balance)
                        positions.append({
                            "time": str(dates[j]), "bias": bias, "entry": entry,
                            "tp": tp_price, "sl": sl_price, "result": "TP"
                        })
                        break
            break
    else:
        equity_curve.append(balance)

# --- Equity Curve ---
st.subheader("📈 Equity Curve")
fig = go.Figure()
fig.add_trace(go.Scatter(y=equity_curve, mode='lines', name='Balance'))
fig.update_layout(title="Equity Curve", xaxis_title="Trade #", yaxis_title="Balance")
st.plotly_chart(fig)

# --- Trade Log ---
st.subheader("📋 Trade Log")
st.dataframe(pd.DataFrame(positions))

# --- Trade Visualization ---
if positions:
    st.subheader("📌 All Trades Visualized on 15-Minute Candlesticks")

    for trade in positions:
        trade["entry_time"] = pd.to_datetime(trade["time"])
        trade["exit_time"] = trade["entry_time"] + pd.Timedelta(minutes=15)

    start = min(pd.to_datetime(p["entry_time"]) for p in positions)
    end = max(pd.to_datetime(p["exit_time"]) for p in positions)
    df_chart = df_15m.loc[start:end].copy()

    fig_trades = go.Figure()
    fig_trades.add_trace(go.Candlestick(
        x=df_chart.index,
        open=df_chart["Open"],
        high=df_chart["High"],
        low=df_chart["Low"],
        close=df_chart["Close"],
        name="15m Price"
    ))

    for trade in positions:
        color = "green" if trade["result"] == "TP" else "red"
        fig_trades.add_trace(go.Scatter(
            x=[trade["entry_time"]],
            y=[trade["entry"]],
            mode='markers',
            marker=dict(color=color, symbol="triangle-up", size=10),
            name=f'Entry ({trade["result"]})'
        ))
        exit_price = trade["tp"] if trade["result"] == "TP" else trade["sl"]
        fig_trades.add_trace(go.Scatter(
            x=[trade["exit_time"]],
            y=[exit_price],
            mode='markers',
            marker=dict(color=color, symbol="circle", size=8),
            name=f'Exit ({trade["result"]})'
        ))

    fig_trades.update_layout(
        title="All Trades Visualized on 15m Candles",
        xaxis_title="Time",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        height=700
    )
    st.plotly_chart(fig_trades, use_container_width=True)







# import streamlit as st
# import pandas as pd
# import numpy as np
# import plotly.graph_objects as go

# # Load Data
# @st.cache_data
# def load_data():
#     df_4h = pd.read_csv("AUDUSD_H4_202201030000_202506102000.csv", sep="\t")
#     df_15m = pd.read_csv("AUDUSD_M15_202201030000_202507042345.csv", sep="\t")

#     df_4h['Date'] = pd.to_datetime(df_4h['<DATE>'] + ' ' + df_4h['<TIME>'], format='%Y.%m.%d %H:%M:%S')
#     df_15m['Date'] = pd.to_datetime(df_15m['<DATE>'] + ' ' + df_15m['<TIME>'], format='%Y.%m.%d %H:%M:%S')

#     df_4h = df_4h.rename(columns={"<OPEN>": "Open", "<HIGH>": "High", "<LOW>": "Low", "<CLOSE>": "Close"})
#     df_15m = df_15m.rename(columns={"<OPEN>": "Open", "<HIGH>": "High", "<LOW>": "Low", "<CLOSE>": "Close"})

#     df_4h.sort_values("Date", inplace=True)
#     df_15m.set_index("Date", inplace=True)
    
#     return df_4h, df_15m

# # Detect Market Structure
# def detect_structure(df):
#     trend = [None] * len(df)
#     highs = df["High"].values
#     lows = df["Low"].values
#     for i in range(2, len(df)):
#         if highs[i] > highs[i-1] > highs[i-2] and lows[i] > lows[i-1] > lows[i-2]:
#             trend[i] = "Bullish"
#         elif highs[i] < highs[i-1] < highs[i-2] and lows[i] < lows[i-1] < lows[i-2]:
#             trend[i] = "Bearish"
#     df["Trend"] = trend
#     return df

# # --- Streamlit UI ---
# st.title("📊 Forex 71% Zone Backtester")

# rr_ratio = st.sidebar.slider("Risk-Reward Ratio", 1.0, 5.0, 2.45, 0.05)
# initial_balance = st.sidebar.number_input("Initial Balance ($)", value=10000, step=500)

# st.info("Backtesting strategy: Enter at 71% retracement after market structure shift (BoS).")

# df_4h, df_15m = load_data()
# df_4h = detect_structure(df_4h)

# balance = initial_balance
# equity_curve = [balance]
# positions = []

# for i in range(3, len(df_4h)):
#     row = df_4h.iloc[i]
#     bias = row["Trend"]
#     if pd.isna(bias):
#         continue

#     fib_low, fib_high = (row["Low"], row["High"]) if bias == "Bullish" else (row["High"], row["Low"])
#     fib_50 = fib_low + 0.5 * (fib_high - fib_low)
#     current_price = row["Close"]
    
#     if (bias == "Bullish" and current_price >= fib_50) or (bias == "Bearish" and current_price <= fib_50):
#         equity_curve.append(balance)
#         continue

#     start_time = row["Date"]
#     end_time = start_time + pd.Timedelta(hours=8)
#     next_15m = df_15m.loc[start_time:end_time]

#     closes = next_15m["Close"].values
#     highs = next_15m["High"].values
#     lows = next_15m["Low"].values
#     dates = next_15m.index.to_numpy()

#     for j in range(2, len(next_15m)):
#         if (closes[j] > highs[j-2]) if bias == "Bullish" else (closes[j] < lows[j-2]):
#             fib15_hl = lows[j-2]
#             fib15_hh = highs[j]

#             if bias == "Bullish":
#                 entry = fib15_hl + 0.71 * (fib15_hh - fib15_hl)
#                 sl_price = fib15_hl
#                 tp_price = entry + (entry - sl_price) * rr_ratio
#             else:
#                 entry = fib15_hh - 0.71 * (fib15_hh - fib15_hl)
#                 sl_price = fib15_hh
#                 tp_price = entry - (sl_price - entry) * rr_ratio

#             for k in range(j+1, min(j+100, len(next_15m))):
#                 if bias == "Bullish":
#                     if lows[k] <= sl_price:
#                         balance -= balance * 0.01
#                         equity_curve.append(balance)
#                         positions.append({
#                             "time": str(dates[j]), "bias": bias, "entry": entry,
#                             "tp": tp_price, "sl": sl_price, "result": "SL"
#                         })
#                         break
#                     elif highs[k] >= tp_price:
#                         balance += balance * 0.01 * rr_ratio
#                         equity_curve.append(balance)
#                         positions.append({
#                             "time": str(dates[j]), "bias": bias, "entry": entry,
#                             "tp": tp_price, "sl": sl_price, "result": "TP"
#                         })
#                         break
#                 else:
#                     if highs[k] >= sl_price:
#                         balance -= balance * 0.01
#                         equity_curve.append(balance)
#                         positions.append({
#                             "time": str(dates[j]), "bias": bias, "entry": entry,
#                             "tp": tp_price, "sl": sl_price, "result": "SL"
#                         })
#                         break
#                     elif lows[k] <= tp_price:
#                         balance += balance * 0.01 * rr_ratio
#                         equity_curve.append(balance)
#                         positions.append({
#                             "time": str(dates[j]), "bias": bias, "entry": entry,
#                             "tp": tp_price, "sl": sl_price, "result": "TP"
#                         })
#                         break
#             break
#     else:
#         equity_curve.append(balance)

# # --- Results ---
# st.subheader("📈 Equity Curve")
# fig = go.Figure()
# fig.add_trace(go.Scatter(y=equity_curve, mode='lines', name='Balance'))
# fig.update_layout(title="Equity Curve", xaxis_title="Trade #", yaxis_title="Balance")
# st.plotly_chart(fig)

# st.subheader("📋 Trade Log")
# st.dataframe(pd.DataFrame(positions))

# # --- Trade Visualization on 15m Candles ---
# if positions:
#     st.subheader("📌 All Trades Visualized on 15-Minute Candlesticks")

#     for trade in positions:
#         trade["entry_time"] = pd.to_datetime(trade["time"])
#         trade["exit_time"] = trade["entry_time"] + pd.Timedelta(minutes=15)

#     start = min(pd.to_datetime(p["entry_time"]) for p in positions)
#     end = max(pd.to_datetime(p["exit_time"]) for p in positions)
#     df_chart = df_15m.loc[start:end].copy()

#     fig_trades = go.Figure()
#     fig_trades.add_trace(go.Candlestick(
#         x=df_chart.index,
#         open=df_chart["Open"],
#         high=df_chart["High"],
#         low=df_chart["Low"],
#         close=df_chart["Close"],
#         name="15m Price"
#     ))

#     for trade in positions:
#         color = "green" if trade["result"] == "TP" else "red"
#         fig_trades.add_trace(go.Scatter(
#             x=[trade["entry_time"]],
#             y=[trade["entry"]],
#             mode='markers',
#             marker=dict(color=color, symbol="triangle-up", size=10),
#             name=f'Entry ({trade["result"]})'
#         ))
#         exit_price = trade["tp"] if trade["result"] == "TP" else trade["sl"]
#         fig_trades.add_trace(go.Scatter(
#             x=[trade["exit_time"]],
#             y=[exit_price],
#             mode='markers',
#             marker=dict(color=color, symbol="circle", size=8),
#             name=f'Exit ({trade["result"]})'
#         ))

#     fig_trades.update_layout(
#         title="All Trades Visualized on 15m Candles",
#         xaxis_title="Time",
#         yaxis_title="Price",
#         xaxis_rangeslider_visible=False,
#         height=700
#     )
#     st.plotly_chart(fig_trades, use_container_width=True)
