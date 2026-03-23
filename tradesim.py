import pandas as pd
import streamlit as st
import numpy as np
from binance.client import Client
from datetime import timezone
import os
import socket

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

def simulate_day_hourly(data, start_idx, weights, market_mask, invest_per_day,limit_levels,limit_multipliers,btfd_multipliers,fee_limit,fee_market,btfd_i):
    end_idx = start_idx + 24

    if end_idx > len(data):
        return None

    day_data = data.iloc[start_idx:end_idx]

    if len(day_data) < 2:
        return None

    start_time = data.iloc[start_idx]['Datetime']
    ref_price = data.iloc[start_idx]['Open']

    invest_per_day = invest_per_day * btfd_multipliers[btfd_i]

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
        invest_amount = w * invest_per_day
        hit_indices = np.where(lows <= limit_price)[0]
        if len(hit_indices) > 0:
            buy_price = lows[hit_indices[0]]
            fills[i] = 1
            effective_invest = invest_amount * (1 - fee_limit)
            invest_limit_total += invest_amount

        elif market_mask[i]:
            buy_price = closes[-2]
            effective_invest = invest_amount * (1 - fee_market)
            invest_market_total += invest_amount

        else:
            continue

        btc_bought = effective_invest / buy_price
        cost = invest_amount

    if btc_bought == 0:
        return None
    

    return btc_bought, cost, fills, invest_limit_total, invest_market_total
