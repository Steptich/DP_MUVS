import streamlit as st
import datetime as dt
import tradesim as tr
import pandas as pd
import numpy as np
from itertools import combinations
import time

st.header("HANIČKA JE ŠIKULKA")




# --- Nastavení ---
SYMBOL = "BTCUSDT"
DATA_FILE = f"{SYMBOL}_full.csv"
HISTORICAL_START = "2018-01-01"
HOUR = 8
known_initial_ath=20089.0 #USD
today = dt.datetime.now()
tomorrow = today + dt.timedelta(days=1)
last_year = today - dt.timedelta(days=365)


start_date = st.date_input(
    "Select start date for simulation:",
    last_year,
    min_value =HISTORICAL_START,
    max_value=today,
    format="DD.MM.YYYY",
)

end_date = st.date_input(
    "Select end date for simulation:",
    today,
    min_value =HISTORICAL_START,
    max_value=today,
    format="DD.MM.YYYY",
)

# --- Inicializace session_state ---
if "btfdmin_slider" not in st.session_state:
    st.session_state.btfdmin_slider = 75  # default hodnota

if "btfdmin_number" not in st.session_state:
    st.session_state.btfdmin_number = st.session_state.btfdmin_slider

# --- Callback pro slider ---
def min_slider_changed():
    st.session_state.btfdmin_number = st.session_state.btfdmin_slider

# --- Callback pro number input ---
def min_number_changed():
    st.session_state.btfdmin_slider = st.session_state.btfdmin_number

# --- Number input ---
st.number_input(
    "Insert min value",
    min_value=10,
    max_value=90,
    step=1,
    key="btfdmin_number",
    on_change=min_number_changed
)

# --- Slider ---
st.slider(
    "Select min range value",
    min_value=10,
    max_value=90,
    step=1,
    key="btfdmin_slider",
    on_change=min_slider_changed
)

BTFD_MIN = - st.session_state.btfdmin_slider


# --- Inicializace session_state ---
if "btfdMULTI_slider" not in st.session_state:
    st.session_state.btfdMULTI_slider = 4.0  # default hodnota

if "btfd" not in st.session_state:
    st.session_state.btfd = st.session_state.btfdMULTI_slider

# --- Callback pro slider ---
def slider_changed():
    st.session_state.btfd = st.session_state.btfdMULTI_slider

# --- Callback pro number input ---
def number_changed():
    st.session_state.btfdMULTI_slider = st.session_state.btfd

# --- Number input ---
st.number_input(
    "Insert a number",
    min_value=1.0,
    max_value=10.0,
    step=0.1,
    key="btfd",
    on_change=number_changed
)

# --- Slider ---
st.slider(
    "Select a range of values",
    min_value=1.0,
    max_value=10.0,
    step=0.1,
    key="btfdMULTI_slider",
    on_change=slider_changed
)

MAX_MULTIPLIER = st.session_state.btfdMULTI_slider

FEE_LIMIT=0.004
FEE_MARKET = 0.006

INVEST_PER_DAY = 70 #USD

btc_full = tr.load_and_update_data(
    symbol=SYMBOL,
    file_path=DATA_FILE,
    start=HISTORICAL_START,
    end=tomorrow
)
print("Data uložena do CSV")

initial_ath = tr.compute_initial_ath(
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

results = []
last_price = btc.iloc[-1]['Close']
ref_times = tr.get_reference_times(btc, hour=8)

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
            res = tr.simulate_day_hourly(btc, start_idx, weights, market_set, INVEST_PER_DAY,initial_ath,limit_levels,btfd_index_series,BTFD_MIN,MAX_MULTIPLIER,FEE_LIMIT,FEE_MARKET)
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
