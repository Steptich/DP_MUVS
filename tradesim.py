import pandas as pd
import streamlit as st
import numpy as np
from binance.client import Client
from datetime import timezone
import os
import socket
from itertools import combinations
import datetime as dt

# --- Nastavení ---
SYMBOL = "BTCUSDT"
DATA_FILE = f"{SYMBOL}_full.csv"
HISTORICAL_START = dt.datetime.strptime("2018-01-01", "%Y-%m-%d")
HOUR = 8
known_initial_ath=20089.0 #USD
today = dt.datetime.now().replace(hour=0,minute=0, second=0, microsecond=0)

# --- Načtení dat s cache a po hodine znova---
@st.cache_data(show_spinner=True,ttl=3600)
def load_btc_data():
    return load_and_update_data(
        symbol=SYMBOL,
        file_path=DATA_FILE,
        start=HISTORICAL_START,
        end=today,
        cloud_flag=is_cloud()
    )

@st.cache_data
def get_filtered_data(df, start, end):
    return df[
        (df['Datetime'] >= pd.to_datetime(start)) &
        (df['Datetime'] <= pd.to_datetime(end+dt.timedelta(days=1)))  # přidáme 1 den, aby se zahrnul i poslední den do filtru
    ].sort_values('Datetime').drop_duplicates('Datetime').reset_index(drop=True)

# detekce Streamlit Cloud
def is_cloud():
    return os.environ.get("HOSTNAME") == "streamlit"

#detekce připojení k internetu
def is_connected():
    try:
        # Try to connect to Google's DNS server
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        pass
    return False

# --- Funkce pro download ---
@st.cache_data
def download_binance_hourly_data(symbol, start, end):
    client = Client()

    # --- převod datetime -> timestamp v milisekundách (UTC!) ---
    start_ts = int(start.replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ts = int(end.replace(tzinfo=timezone.utc).timestamp() * 1000)

    klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1HOUR, start_ts, end_ts)

    df = pd.DataFrame(klines, columns=[
        'Datetime', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close_time', 'Quote_asset_volume', 'Number_of_trades',
        'Taker_buy_base_asset_volume', 'Taker_buy_quote_asset_volume', 'Ignore'
    ])

    df['Datetime'] = pd.to_datetime(df['Datetime'], unit='ms')
    df['Open'] = df['Open'].astype(float)
    df['High'] = df['High'].astype(float)
    df['Low'] = df['Low'].astype(float)
    df['Close'] = df['Close'].astype(float)
    df['Volume'] = df['Volume'].astype(float)

    # Zachovej pouze potřebné sloupce:
    df = df[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']]
    df = df.sort_values('Datetime').reset_index(drop=True)

    # Přidání stejného sloupce jako u yfinance
    df['Weekday'] = df['Datetime'].dt.weekday
    return df

# --- 1. Načtení nebo stažení dat ---
@st.cache_data
def load_and_update_data(symbol, file_path, start, end, cloud_flag):
    
    # --- CLOUD: pouze načti CSV ---
    if cloud_flag:
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                "CSV soubor na serveru neexistuje. Nahraj ho do repozitáře."
            )

        print("CLOUD režim: načítám pouze CSV")
        df = pd.read_csv(file_path, sep=";", parse_dates=['Datetime'])
        df = df.sort_values('Datetime').reset_index(drop=True) 
        return df
    
    if is_connected():
        
       # --- 1. CSV existuje ---
       if os.path.exists(file_path):
           print("Načítám existující CSV...")
           df = pd.read_csv(file_path, sep=";", parse_dates=['Datetime'])
           df = df.sort_values('Datetime').reset_index(drop=True) 
        
           last_dt = df['Datetime'].max()
           print(f"Poslední datum v CSV: {last_dt}")

           # --- 2. Update pokud chybí data ---
           if end > last_dt:
               print("Stahuji nová data...")
               # malý overlap kvůli bezpečnosti
               update_start = (last_dt - pd.Timedelta(hours=2))
               df_new = download_binance_hourly_data(
                   symbol=symbol,
                   start=update_start,
                   end=end
               )

               # --- 3. Sloučení + deduplikace ---
               df = pd.concat([df, df_new])
               df = df.drop_duplicates(subset='Datetime')
               df = df.sort_values('Datetime').reset_index(drop=True)

               # --- 4. Uložení ---
               df.to_csv(file_path, sep=";", index=False)
               print("CSV aktualizováno")

       # --- 5. CSV neexistuje → full download ---
       else:
           print("CSV neexistuje → stahuji celou historii")

           df = download_binance_hourly_data(
               symbol=symbol,
               start=start,
               end=end
           )

           df.to_csv(file_path, sep=";", index=False)

       return df
    else:
        if os.path.exists(file_path):
            print("Offline režim: načítám uložené CSV")
            df = pd.read_csv(file_path, sep=";", parse_dates=['Datetime'])
            df = df.sort_values('Datetime').reset_index(drop=True) 
            return df
        else:
            raise   FileNotFoundError("CSV soubor neexistuje a není připojení k internetu.")

# ==== 2. Funkce pro získání referenčních časů každý den ve stejnou hodinu ====
@st.cache_data
def get_reference_times(df, hour):
    df['Date'] = df['Datetime'].dt.date
    df['Hour'] = df['Datetime'].dt.hour
    refs = df[df['Hour'] == hour].copy()
    return refs.reset_index()

def simulate_day_hourly(data, start_idx, weights, market_mask, invest_per_day,limit_levels,limit_multipliers,btfd_multipliers,fee_limit,fee_market):
    end_idx = start_idx + 24

    if end_idx > len(data):
        return None

    day_data = data.iloc[start_idx:end_idx]

    if len(day_data) < 2:
        return None

    ref_price = data.iloc[start_idx]['Open']

    lows = day_data['Low'].values
    closes = day_data['Close'].values

    btc_bought = 0
    fills = np.zeros(len(limit_levels), dtype=np.int8)

    invest_limit_total = 0  # investice přes limitní nákup
    invest_market_total = 0  # investice přes tržní nákup
    limit_prices = ref_price * limit_multipliers
    for i in range(len(limit_levels)):
        w = weights[i]

        if w == 0:
            continue
        limit_price = limit_prices[i]
        hit_indices = np.where(lows <= limit_price)[0]
        if len(hit_indices) > 0:
            btfd_idx = start_idx  + hit_indices[0]
            buy_price = lows[hit_indices[0]]
            fills[i] = 1
            invest_amount = invest_per_day * w * btfd_multipliers[btfd_idx]
            effective_invest = invest_amount * (1 - fee_limit)
            invest_limit_total += invest_amount

        elif market_mask[i]:
            btfd_idx = start_idx + len(closes) - 2
            buy_price = closes[-2]
            invest_amount = invest_per_day * w * btfd_multipliers[btfd_idx]
            effective_invest = invest_amount * (1 - fee_market)
            invest_market_total += invest_amount

        else:
            continue

        btc_bought = effective_invest / buy_price
        cost = invest_amount

    if btc_bought == 0:
        return None
    

    return btc_bought, cost, fills, invest_limit_total, invest_market_total

@st.cache_data(show_spinner=False)
def compute_btfd_df(btc_full: pd.DataFrame, known_initial_ath: float):
    df = btc_full[['Datetime', 'High', 'Close']].copy()

    # --- ATH (globální přes celý dataset) ---
    df['ATH'] = np.maximum(
        df['High'].cummax(),
        known_initial_ath
    )
    # --- BTFD ---
    df['BTFD'] = (df['Close'] - df['ATH']) / df['ATH'] * 100

    return df[['Datetime', 'BTFD']]

@st.cache_data(show_spinner=False)
def add_multiplier(btfd_df: pd.DataFrame, btfd_min: float, max_multiplier: float):

    df = btfd_df.copy()

    btfd = df['BTFD'].to_numpy()
    denom = btfd_min if btfd_min != 0 else -1e-9

    df['Multiplier'] = np.where(
        btfd >= 0,
        1.0,
        np.where(
            btfd <= btfd_min,
            max_multiplier,
            1.0 + (btfd / denom) * (max_multiplier - 1.0)
        )
    )

    return df

@st.cache_data(hash_funcs={tuple: hash})
def generate_market_sets(limit_levels, weights):
    nonzero = tuple(lvl for lvl, w in zip(limit_levels, weights) if w > 0)
    return tuple(frozenset(combo) for r in range(len(nonzero) + 1) for combo in combinations(nonzero, r))





