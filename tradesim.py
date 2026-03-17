import pandas as pd
import numpy as np
from itertools import combinations
from datetime import datetime, timedelta
from binance.client import Client
import os

# --- Nastavení ---
SYMBOL = "BTCUSDT"
DATA_FILE = f"{SYMBOL}_full.csv"
HISTORICAL_START = "1 Jan, 2018"
HOUR = 8
known_initial_ath=20089.0 #USD
today = datetime.now()
tomorrow = today + timedelta(days=1)
formatted_tomorrow = f"{tomorrow.day} {tomorrow.strftime('%b, %Y')}"

BTFD_MIN =-75
MAX_MULTIPLIER = 4

FEE_LIMIT=0.004
FEE_MARKET = 0.006

INVEST_PER_DAY = 70 #USD

start_date='1 Jan, 2018'
end_date='1 Jan, 2026'


# --- Funkce pro download ---
def download_binance_hourly_data(symbol=SYMBOL, start=HISTORICAL_START, end=formatted_tomorrow):
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
def load_and_update_data(symbol=SYMBOL, file_path=DATA_FILE, start=HISTORICAL_START, end=formatted_tomorrow):
    # --- 1. CSV existuje ---
    if os.path.exists(file_path):
        print("Načítám existující CSV...")
        df = pd.read_csv(file_path, sep=";", parse_dates=['Datetime'])

        last_dt = df['Datetime'].max()
        print(f"Poslední datum v CSV: {last_dt}")
        # --- 2. Update pokud chybí data ---
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
def get_reference_times(df, hour=HOUR):
    df['Date'] = df['Datetime'].dt.date
    df['Hour'] = df['Datetime'].dt.hour
    refs = df[df['Hour'] == hour].copy()
    return refs.reset_index()

def get_btfd_multiplier(btfd_percent: float, btfd_min: float = BTFD_MIN, max_multiplier: float = MAX_MULTIPLIER) -> float:
    if btfd_percent >= 0:
        return 1.0
    elif btfd_percent <= btfd_min:
        return max_multiplier
    else:
        # Lineární interpolace mezi 1 a max_multiplier
        scale = (btfd_percent - 0) / (btfd_min - 0)
        return 1.0 + scale * (max_multiplier - 1.0)


############################################################################################################
btc_full = load_and_update_data(
    symbol=SYMBOL,
    file_path=DATA_FILE,
    start=HISTORICAL_START,
    end=formatted_tomorrow
)
print("Data uložena do CSV")

initial_ath = compute_initial_ath(
    btc_full=btc_full,
    start_date=start_date,
    known_initial_ath=known_initial_ath
)
print(f"Dosavaď dosažené ATH před {start_date}: {initial_ath}")

# --- 3. Ořez datasetu pro simulaci ---
btc = btc_full[
    (btc_full['Datetime'] >= pd.to_datetime(start_date)) &
    (btc_full['Datetime'] <= pd.to_datetime(end_date))
].reset_index(drop=True)

print(f"Počet záznamů pro simulaci: {len(btc)}")

############################################################################################################
btc['Weekday'] = btc['Datetime'].dt.weekday
btc = btc[~btc['Datetime'].duplicated(keep='first')].reset_index(drop=True)

# === 3. Inicializace listu pro uložení vývoje BTFD indexu ===
btfd_index_series = []  # (datetime, price, ath, btfd)

limit_levels = [1, 2, 3, 4, 5]
weight_sets = [
    [1.00, 0.00, 0.00, 0.00, 0.00],  # jen 1 %
    [0.00, 1.00, 0.00, 0.00, 0.00],  # jen 2 %
    [0.00, 0.00, 1.00, 0.00, 0.00],  # jen 3 %
    [0.00, 0.00, 0.00, 1.00, 0.00],  # jen 4 %
    [0.00, 0.00, 0.00, 0.00, 1.00],  # jen 5 %
]

def simulate_day_hourly(data, start_idx, weights, market_buy_for, invest_per_day,current_ath=initial_ath,fee_limit=0.004,fee_market = 0.006):
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
    multiplier = get_btfd_multiplier(btfd)
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

results = []
last_price = btc.iloc[-1]['Close']
ref_times = get_reference_times(btc, hour=8)

for i, weights in enumerate(weight_sets):
    print(f"\nTestuji váhovou sadu {i + 1}/{len(weight_sets)}: {weights}")
    nonzero_levels = [lvl for lvl, w in zip(limit_levels, weights) if w > 0]
    possible_market_buy_for = [set(combo) for r in range(len(nonzero_levels)+1) for combo in combinations(nonzero_levels, r)]# [{limit_levels[0]}] #
    for market_set in possible_market_buy_for:
        sum_market_weights = sum(w for w, lvl in zip(weights, limit_levels) if lvl in market_set)
        if sum_market_weights < 0.8:
            continue
        avg_prices = []
        total_btc = 0
        total_cost = 0
        count_days = 0
        total_invest_limit = 0
        total_invest_market = 0
        total_limit_fill = {lvl: 0 for lvl in limit_levels}
        for idx in ref_times['index']:
            start_idx = btc.index.get_loc(idx)
            res = simulate_day_hourly(btc, start_idx, weights, market_set, INVEST_PER_DAY,initial_ath,FEE_LIMIT,FEE_MARKET)
            if res is not None:
                avg_p, btc_b, cost, fills, invest_limit, invest_market = res
                avg_prices.append(avg_p)
                total_btc += btc_b
                total_cost += cost
                count_days += 1
                for lvl in limit_levels:
                    total_limit_fill[lvl] += fills[lvl]
                total_invest_limit += invest_limit
                total_invest_market += invest_market
        if count_days == 0:
            continue

        # Výpočet procent limitních a tržních investic:
        percent_limit_invest = 100 * total_invest_limit / total_cost if total_cost > 0 else 0
        percent_market_invest = 100 * total_invest_market / total_cost if total_cost > 0 else 0

        mean_price = np.mean(avg_prices)
        avg_fill_rate = {lvl: total_limit_fill[lvl] / count_days for lvl in limit_levels}
        total_profit = total_btc * last_price - total_cost
        ROI = total_profit/total_cost *100
        ROI_pa = (((total_btc * last_price) / total_cost) ** (1 / (count_days / 365)) -1)*100
        efficiency = total_cost/(count_days*INVEST_PER_DAY) *100
        uninvested_amount = count_days * INVEST_PER_DAY - total_cost
        total_amount = total_btc * last_price + uninvested_amount
        results.append({
            'weights': weights,
            'market_buy_for': market_set,
            'avg_price': mean_price,
            'total_btc': total_btc,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'ROI': ROI,
            'ROI_pa': ROI_pa,
            'efficiency': efficiency,
            'days': count_days,
            'uninvested_amount': uninvested_amount,
            'total_amount': total_amount,
            'sum_market_weights': sum_market_weights,
            'avg_fill_rate': avg_fill_rate,
            'percent_limit_invest': percent_limit_invest,
            'percent_market_invest': percent_market_invest,
        })

# ==== 6. Výpis TOP 3 podle průměrné ceny ====
top3_price = sorted(results, key=lambda x: x['avg_price'])[:5]

print("\n📊 TOP 3 strategií podle průměrné nákupní ceny (s průměrným % naplnění limitů):")
for i, r in enumerate(top3_price, 1):
    w = [round(x, 3) for x in r['weights']]
    mb = sorted(r['market_buy_for'])
    fills = {k: round(v * 100, 1) for k, v in r['avg_fill_rate'].items()}
    print(f"{i}. Váhy: {w}, Tržní nákup: {mb}")
    print(f"   Průměrná cena: {r['avg_price']:.2f} USD")
    print(f"   Celkové BTC: {r['total_btc']:.6f}")
    print(f"   Celkově vložený kapitál: {r['total_cost']:.2f} USD")
    print(f"   Počet dnů: {r['days']}")
    print(f"   Celkový zisk: {(r['total_profit'] if 'total_profit' in r else 0):.2f} USD")
    print(f"   Návratnost investice (ROI): {(r['ROI'] if 'ROI' in r else 0):.2f} %")
    print(f"   Roční zhodnocení (ROI p.a.): {(r['ROI_pa'] if 'ROI_pa' in r else 0):.2f} %")
    print(f"   Efektivní využití kapitálu: {(r['efficiency'] if 'efficiency' in r else 0):.2f} %")
    print(f"   Neinvestovaná  částka: {(r[' uninvested_amount'] if ' uninvested_amount' in r else 0):.2f} USD")
    print(f"   Celkový kapitál: {(r['total_amount'] if 'total_amount' in r else 0):.2f} USD")
    print(f"   Průměrné naplnění limitů (% z dnů): {fills}")
    print(f"   Procento investic přes limitní nákupy: {r['percent_limit_invest']:.1f} %")
    print(f"   Procento investic přes tržní nákupy: {r['percent_market_invest']:.1f} %")
    print(f"   Tržní pokrytí (váha): {r['sum_market_weights']:.2f}\n")

# ==== 7. Výpis TOP 3 podle nejvyššího množství BTC ====
top3_btc = sorted(results, key=lambda x: x['total_btc'], reverse=True)[:5]

print("\n📊 TOP 3 strategií podle nejvyššího množství nakoupeného BTC (s průměrnou nákupní cenou):")
for i, r in enumerate(top3_btc, 1):
    w = [round(x, 3) for x in r['weights']]
    mb = sorted(r['market_buy_for'])
    fills = {k: round(v * 100, 1) for k, v in r['avg_fill_rate'].items()}
    print(f"{i}. Váhy: {w}, Tržní nákup: {mb}")
    print(f"   Průměrná cena: {r['avg_price']:.2f} USD")
    print(f"   Celkové BTC: {r['total_btc']:.6f}")
    print(f"   Celkově vložený kapitál: {r['total_cost']:.2f} USD")
    print(f"   Počet dnů: {r['days']}")
    print(f"   Celkový zisk: {(r['total_profit'] if 'total_profit' in r else 0):.2f} USD")
    print(f"   Návratnost investice (ROI): {(r['ROI'] if 'ROI' in r else 0):.2f} %")
    print(f"   Roční zhodnocení (ROI p.a.): {(r['ROI_pa'] if 'ROI_pa' in r else 0):.2f} %")
    print(f"   Efektivní využití kapitálu: {(r['efficiency'] if 'efficiency' in r else 0):.2f} %")
    print(f"   Neinvestovaná  částka: {(r[' uninvested_amount'] if ' uninvested_amount' in r else 0):.2f} USD")
    print(f"   Celkový kapitál: {(r['total_amount'] if 'total_amount' in r else 0):.2f} USD")
    print(f"   Průměrné naplnění limitů (% z dnů): {fills}")
    print(f"   Procento investic přes limitní nákupy: {r['percent_limit_invest']:.1f} %")
    print(f"   Procento investic přes tržní nákupy: {r['percent_market_invest']:.1f} %")
    print(f"   Tržní pokrytí (váha): {r['sum_market_weights']:.2f}\n")

# ==== 8. Výpis TOP 3 podle největšího zisku ====
top3_ROI = sorted(results, key=lambda x: x['ROI'], reverse=True)[:5]

print("\n📊 TOP 3 strategií podle největšího ROI:")
for i, r in enumerate(top3_ROI, 1):
    w = [round(x, 3) for x in r['weights']]
    mb = sorted(r['market_buy_for'])
    fills = {k: round(v * 100, 1) for k, v in r['avg_fill_rate'].items()}
    print(f"{i}. Váhy: {w}, Tržní nákup: {mb}")
    print(f"   Průměrná cena: {r['avg_price']:.2f} USD")
    print(f"   Celkové BTC: {r['total_btc']:.6f}")
    print(f"   Celkově vložený kapitál: {r['total_cost']:.2f} USD")
    print(f"   Počet dnů: {r['days']}")
    print(f"   Celkový zisk: {(r['total_profit'] if 'total_profit' in r else 0):.2f} USD")
    print(f"   Návratnost investice (ROI): {(r['ROI'] if 'ROI' in r else 0):.2f} %")
    print(f"   Roční zhodnocení (ROI p.a.): {(r['ROI_pa'] if 'ROI_pa' in r else 0):.2f} %")
    print(f"   Efektivní využití kapitálu: {(r['efficiency'] if 'efficiency' in r else 0):.2f} %")
    print(f"   Neinvestovaná  částka: {(r[' uninvested_amount'] if ' uninvested_amount' in r else 0):.2f} USD")
    print(f"   Celkový kapitál: {(r['total_amount'] if 'total_amount' in r else 0):.2f} USD")
    print(f"   Průměrné naplnění limitů (% z dnů): {fills}")
    print(f"   Procento investic přes limitní nákupy: {r['percent_limit_invest']:.1f} %")
    print(f"   Procento investic přes tržní nákupy: {r['percent_market_invest']:.1f} %")
    print(f"   Tržní pokrytí (váha): {r['sum_market_weights']:.2f}\n")

btfd_df = pd.DataFrame(btfd_index_series)
mean_btfd = btfd_df['BTFD'].mean()
mean_multiplier = btfd_df['Multiplier'].mean()


# Vezmeme všechny multiplikátory
multipliers = [entry['Multiplier'] for entry in btfd_index_series]
adjusted_investments = [m * INVEST_PER_DAY for m in multipliers]
# Medián denní investice
median_daily_invest = np.median(adjusted_investments)
# Medián měsíční investice (30 dní)
median_monthly_invest = median_daily_invest * 30

print("\n📈 Statistika BTFD indikátoru a multiplikátoru:")
print(f"   Průměrná hodnota BTFD indikátoru: {mean_btfd:.2f} %")
print(f"   Průměrná hodnota multiplikátoru: {mean_multiplier:.3f}×")
print(f"   Odpovídající průměrná denní investice: {mean_multiplier * INVEST_PER_DAY:.2f} USD")
print(f"   Odpovídající průměrná měsíční investice (30 dní): {mean_multiplier * INVEST_PER_DAY * 30:.2f} USD")
print(f"📉 Medián denní investice: {median_daily_invest:.2f} USD")
print(f"📅 Medián měsíční investice: {median_monthly_invest:.2f} USD")
