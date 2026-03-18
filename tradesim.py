import pandas as pd
import streamlit as st
from binance.client import Client
import os


# --- Funkce pro download ---
@st.cache_data
def download_binance_hourly_data(symbol, start, end):
    client = Client()

    klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1HOUR, start, end)

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
def load_and_update_data(symbol, file_path, start, end):
    # --- 1. CSV existuje ---
    if os.path.exists(file_path):
        print("Načítám existující CSV...")
        df = pd.read_csv(file_path, sep=";", parse_dates=['Datetime'])

        last_dt = df['Datetime'].max()
        print(f"Poslední datum v CSV: {last_dt}")

        # --- 2. Update pokud chybí data ---
        if end > last_dt.strftime("%d %b, %Y"):
            print("Stahuji nová data...")
            # malý overlap kvůli bezpečnosti
            update_start = (last_dt - pd.Timedelta(hours=2)).strftime("%d %b, %Y")
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

@st.cache_data
def compute_initial_ath(btc_full, start_date, known_initial_ath):
    """
    Vrátí ATH před zadaným start_date.

    Parametry:
    - btc_full: DataFrame s historickými daty (musí obsahovat 'Datetime' a 'High')
    - start_date: str nebo datetime (např. '1 Jan, 2019')
    - known_initial_ath: float (známé ATH mimo dataset)

    Návratová hodnota:
    - initial_ath: float
    """

    start_dt = pd.to_datetime(start_date)

    btc_before = btc_full[btc_full['Datetime'] < start_dt]

    # max z datasetu (pokud existuje)
    data_ath = btc_before['High'].max() if not btc_before.empty else None

    # finální ATH = maximum z obou
    if data_ath is not None:
        return max(known_initial_ath, data_ath)

    return known_initial_ath

# ==== 2. Funkce pro získání referenčních časů každý den ve stejnou hodinu ====
def get_reference_times(df, hour):
    df['Date'] = df['Datetime'].dt.date
    df['Hour'] = df['Datetime'].dt.hour
    refs = df[df['Hour'] == hour].copy()
    return refs.reset_index()

def get_btfd_multiplier(btfd_percent: float, btfd_min: float, max_multiplier: float) -> float:
    if btfd_percent >= 0:
        return 1.0
    elif btfd_percent <= btfd_min:
        return max_multiplier
    else:
        # Lineární interpolace mezi 1 a max_multiplier
        scale = (btfd_percent - 0) / (btfd_min - 0)
        return 1.0 + scale * (max_multiplier - 1.0)

def simulate_day_hourly(data, start_idx, weights, market_buy_for, invest_per_day,current_ath,limit_levels,btfd_index_series,btfd_min,max_multiplier,fee_limit=0.004,fee_market = 0.006):
    ref_price = data.iloc[start_idx]['Open']
    start_time = data.iloc[start_idx]['Datetime']
    end_time = start_time + pd.Timedelta(days=1)
    day_data = data[(data['Datetime'] >= start_time) & (data['Datetime'] < end_time)]
    if day_data.empty or len(day_data) < 2:
        return None

    # Výpočet aktuálního ATH v rámci historických dat až po začátek dne
    ath_until_now = data[data['Datetime'] < start_time]['High'].max()
    ath_until_now = max(ath_until_now, current_ath)

    current_price = data.loc[start_idx, 'Close']
    btfd = 100 * (current_price - ath_until_now) / ath_until_now
    multiplier = get_btfd_multiplier(btfd,btfd_min,max_multiplier)
    invest_per_day = invest_per_day * multiplier

    btfd_index_series.append({
        'Datetime': start_time,
        'BTC_Close': current_price,
        'ATH': ath_until_now,
        'BTFD': btfd,
        'Multiplier': multiplier
    })

    btc_bought = 0
    total_cost = 0
    fills = {lvl: 0 for lvl in limit_levels}

    invest_limit_total = 0  # investice přes limitní nákup
    invest_market_total = 0  # investice přes tržní nákup
    for w, lvl in zip(weights, limit_levels):
        if w == 0:
            continue
        limit_price = ref_price * (1 - lvl / 100)
        invest_amount = w * invest_per_day
        hit = day_data[day_data['Low'] <= limit_price]
        if not hit.empty:
            buy_price = hit.iloc[0]['Low']
            fills[lvl] = 1
            effective_invest = invest_amount * (1 - fee_limit)
            invest_limit_total += invest_amount
        elif lvl in market_buy_for:
            buy_price = day_data.iloc[-2]['Close']
            fills[lvl] = 0
            effective_invest = invest_amount * (1 - fee_market)
            invest_market_total += invest_amount
        else:
            fills[lvl] = 0
            continue
        btc_bought += effective_invest / buy_price
        total_cost += invest_amount
    if btc_bought == 0:
        return None
    avg_price = total_cost / btc_bought
    return avg_price, btc_bought, total_cost, fills, invest_limit_total, invest_market_total
