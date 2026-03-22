import streamlit as st
import datetime as dt
import tradesim as tr
import pandas as pd
import numpy as np
from itertools import combinations

st.header("HANIČKA JE ŠIKULKA")



# --- Nastavení ---
SYMBOL = "BTCUSDT"
DATA_FILE = f"{SYMBOL}_full.csv"
HISTORICAL_START = dt.datetime.strptime("2018-01-01", "%Y-%m-%d")
HOUR = 8
known_initial_ath=20089.0 #USD
today = dt.datetime.now().replace(minute=0, second=0, microsecond=0)

# --- Načtení dat s cache a po hodine znova---
@st.cache_data(show_spinner=True,ttl=3600)
def load_btc_data():
    return tr.load_and_update_data(
        symbol=SYMBOL,
        file_path=DATA_FILE,
        start=HISTORICAL_START,
        end=today,
        cloud_flag=tr.is_cloud()
    )
btc_full = load_btc_data()
print("Data načtena")

last_dt = btc_full['Datetime'].max()
year_before = last_dt - dt.timedelta(days=365)



col1a, col2a = st.columns(2)

with col1a:
    # --- Inicializace ---
    if "start_date" not in st.session_state:
        st.session_state.start_date = year_before
    if "end_date" not in st.session_state:
        st.session_state.end_date = last_dt
    # --- Callbacky ---
    def on_start_change():
        if st.session_state.start_date > st.session_state.end_date:
            st.session_state.end_date = st.session_state.start_date
    def on_end_change():
        if st.session_state.end_date < st.session_state.start_date:
            st.session_state.start_date = st.session_state.end_date
    
    # --- START DATE ---
    st.date_input(
        "Select start date for simulation:",
        key="start_date",
        min_value=HISTORICAL_START,
        max_value=st.session_state.end_date,
        format="DD.MM.YYYY",
        on_change=on_start_change,      
    )

    # --- END DATE ---
    st.date_input(
        "Select end date for simulation:",
        key="end_date",
        min_value=st.session_state.start_date,
        max_value=last_dt,
        format="DD.MM.YYYY",
        on_change=on_end_change,
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

    if "btfd_number" not in st.session_state:
        st.session_state.btfd_number = st.session_state.btfdMULTI_slider

    # --- Callback pro slider ---
    def slider_changed():
        st.session_state.btfd_number = st.session_state.btfdMULTI_slider

    # --- Callback pro number input ---
    def number_changed():
        st.session_state.btfdMULTI_slider = st.session_state.btfd_number

    # --- Number input ---
    st.number_input(
        "Insert a number",
        min_value=1.0,
        max_value=10.0,
        step=0.1,
        format="%0.1f",
        key="btfd_number",
        on_change=number_changed
    )

    # --- Slider ---
    st.slider(
        "Select a range of values",
        min_value=1.0,
        max_value=10.0,
        step=0.1,
        format="%0.1f",
        key="btfdMULTI_slider",
        on_change=slider_changed
    )

    MAX_MULTIPLIER = st.session_state.btfdMULTI_slider

with col2a:
    "dummy text"

# --- Inicializace session_state pro fee_limit ---
if "fee_limit_slider" not in st.session_state:
    st.session_state.fee_limit_slider = 0.4  # výchozí hodnota 0.4 %

if "fee_limit_number" not in st.session_state:
    st.session_state.fee_limit_number = st.session_state.fee_limit_slider

# --- Callback pro slider fee_limit ---
def fee_limit_slider_changed():
    st.session_state.fee_limit_number = st.session_state.fee_limit_slider

# --- Callback pro number input fee_limit ---
def fee_limit_number_changed():
    st.session_state.fee_limit_slider = st.session_state.fee_limit_number

# --- Number input fee_limit ---
st.number_input(
    "Fee Limit (%)",
    min_value=0.0,
    max_value=1.0,
    step=0.01,
    format="%0.2f",
    key="fee_limit_number",
    on_change=fee_limit_number_changed
)

# --- Slider fee_limit ---
st.slider(
    "Select Fee Limit (%)",
    min_value=0.0,
    max_value=1.0,
    step=0.01,
    format="%0.2f",
    key="fee_limit_slider",
    on_change=fee_limit_slider_changed
)

FEE_LIMIT = st.session_state.fee_limit_slider /100


# --- Inicializace session_state pro fee_market ---
if "fee_market_slider" not in st.session_state:
    st.session_state.fee_market_slider = 0.6  # výchozí hodnota 0.6 %

if "fee_market_number" not in st.session_state:
    st.session_state.fee_market_number = st.session_state.fee_market_slider

# --- Callback pro slider fee_market ---
def fee_market_slider_changed():
    st.session_state.fee_market_number = st.session_state.fee_market_slider

# --- Callback pro number input fee_market ---
def fee_market_number_changed():
    st.session_state.fee_market_slider = st.session_state.fee_market_number

# --- Number input fee_market ---
st.number_input(
    "Fee Market (%)",
    min_value=0.0,
    max_value=1.0,
    step=0.01,
    format="%0.2f",
    key="fee_market_number",
    on_change=fee_market_number_changed
)

# --- Slider fee_market ---
st.slider(
    "Select Fee Market (%)",
    min_value=0.0,
    max_value=1.0,
    step=0.01,
    format="%0.2f",
    key="fee_market_slider",
    on_change=fee_market_slider_changed
)

FEE_MARKET = st.session_state.fee_market_slider / 100

# --- Inicializace session_state pro fee_market ---
if "investment_number" not in st.session_state:
    st.session_state.investment_number = 100


# --- Number input fee_market ---
st.number_input(
    "Investment (USD)",
    min_value=0,
    max_value=10000,
    step=10,
    #format="%0.2f",
    key="investment_number",
)
INVEST_PER_DAY = st.session_state.investment_number

initial_ath = tr.compute_initial_ath(
    btc_full=btc_full,
    start_date=st.session_state.start_date,
    known_initial_ath=known_initial_ath
)
print(f"Dosavaď dosažené ATH před {st.session_state.start_date}: {initial_ath}")

# --- 3. Ořez datasetu pro simulaci ---
btc = btc_full[
    (btc_full['Datetime'] >= pd.to_datetime(st.session_state.start_date)) &
    (btc_full['Datetime'] <= pd.to_datetime(st.session_state.end_date))
].sort_values('Datetime').drop_duplicates('Datetime').reset_index(drop=True)

print(f"Počet záznamů pro simulaci: {len(btc)}")

btc['Weekday'] = btc['Datetime'].dt.weekday
btc['ATH'] = btc['High'].cummax()
index_map = {idx: i for i, idx in enumerate(btc.index)}

limit_levels = (1, 2, 3, 4, 5)
weight_sets = ((1.00, 0.00, 0.00, 0.00, 0.00),)
limit_multipliers = np.array([1 - lvl / 100 for lvl in limit_levels])
    
last_price = btc.iloc[-1]['Close']
ref_times = tr.get_reference_times(btc, hour=HOUR)
ref_index = tuple(ref_times['index'])

# =========================
# ⚡ FAST HASH
# =========================
def df_to_hash(df: pd.DataFrame) -> int:
    return hash((tuple(df.columns), tuple(df.to_numpy().flatten())))

# =========================
# 🎯 MARKET SETS CACHE
# =========================
@st.cache_data(hash_funcs={tuple: hash})
def generate_market_sets(limit_levels, weights):
    nonzero = tuple(lvl for lvl, w in zip(limit_levels, weights) if w > 0)
    return tuple(frozenset(combo) for r in range(len(nonzero) + 1) for combo in combinations(nonzero, r))


# =========================
# 🚀 CORE SIMULATION (CACHE)
# =========================
@st.cache_data(hash_funcs={pd.DataFrame: df_to_hash, tuple: hash, frozenset: lambda x: hash(tuple(sorted(x)))})

def simulate_configuration(
    weights,
    market_set,
    btc,
    ref_index,
    limit_levels,
    invest,
    initial_ath,
    btfd_min,
    max_multiplier,
    fee_limit,
    fee_market,
    last_price
):
    market_mask = np.array([lvl in market_set for lvl in limit_levels], dtype=np.bool_)

    # --- použij list, simulate_day_hourly do něj appenduje ---
    n_days = len(ref_index)
    btfd_index_series = np.empty((n_days, 5), dtype=np.float64)
    btfd_index_series[:] = np.nan

    avg_prices = []
    total_btc = total_cost = count_days = 0
    total_limit = total_market = 0

    fills_sum = np.zeros(len(limit_levels), dtype=np.float32)

    for day_i, idx in enumerate(ref_index):
        start_idx = index_map[idx]

        res = tr.simulate_day_hourly(
            btc,
            start_idx,
            weights,
            market_mask,
            invest,
            initial_ath,
            limit_levels,
            limit_multipliers,
            btfd_index_series,
            btfd_min,
            max_multiplier,
            fee_limit,
            fee_market,
            btfd_i=day_i,
        )

        if res is None:
            continue

        avg_p, btc_b, cost, fills, inv_l, inv_m = res

        avg_prices.append(avg_p)
        total_btc += btc_b
        total_cost += cost
        count_days += 1
        total_limit += inv_l
        total_market += inv_m

        fills_sum += fills

    if count_days == 0:
        return None
    
    return {
        "weights": weights,
        "market_buy_for": tuple(sorted(market_set)),
        "avg_price": np.mean(avg_prices),
        "total_btc": total_btc,
        "total_cost": total_cost,
        "days": count_days,
        "total_profit": total_btc * last_price - total_cost,
        "ROI": (total_btc * last_price - total_cost) / total_cost * 100,
        "ROI_pa": (((total_btc * last_price) / total_cost) ** (1 / (count_days / 365)) - 1) * 100,
        "efficiency": total_cost / (count_days * invest) * 100,
        "uninvested_amount": count_days * invest - total_cost,
        "total_amount": total_btc * last_price + (count_days * invest - total_cost),
        "avg_fill_rate": {lvl: fills_sum[i]/count_days for i, lvl in enumerate(limit_levels)},
        "percent_limit_invest": 100 * total_limit / total_cost if total_cost else 0,
        "percent_market_invest": 100 * total_market / total_cost if total_cost else 0,
        'btfd_index_series': btfd_index_series
    }

# =========================
# 🧠 BACKTEST
# =========================
def run_backtest():
    results = []

    ref_index = tuple(ref_times['index'])

    for i, weights in enumerate(weight_sets):
        market_sets = generate_market_sets(limit_levels, weights)
        for market_set in market_sets:
            print(f"\nTestuji váhovou sadu {i + 1}/{len(weight_sets)}: {weights}")
            res = simulate_configuration(
                weights,
                market_set,
                btc,
                ref_index,
                limit_levels,
                INVEST_PER_DAY,
                initial_ath,
                BTFD_MIN,
                MAX_MULTIPLIER,
                FEE_LIMIT,
                FEE_MARKET,
                last_price
            )

            if res:
                results.append(res)

    return results

# =========================
# ▶ RUN
# =========================
results = run_backtest()

print(f"Počet výsledků: {len(results)}")

#📊 OUTPUT
#=========================
#==== 1. TOP podle průměrné ceny ====
top_price = sorted(results, key=lambda x: x['avg_price'])[:5]

print("\n📊 TOP 5 strategií podle průměrné nákupní ceny:")
for i, r in enumerate(top_price, 1):
    fills = {k: round(v * 100, 1) for k, v in r['avg_fill_rate'].items()}

    print(f"{i}. Váhy: {list(r['weights'])}, Tržní nákup: {list(r['market_buy_for'])}")
    print(f"   Průměrná cena: {r['avg_price']:.2f} USD")
    print(f"   Celkové BTC: {r['total_btc']:.6f}")
    print(f"   Celkově vložený kapitál: {r['total_cost']:.2f} USD")
    print(f"   Počet dnů: {r['days']}")
    print(f"   Celkový zisk: {r['total_profit']:.2f} USD")
    print(f"   ROI: {r['ROI']:.2f} %")
    print(f"   ROI p.a.: {r['ROI_pa']:.2f} %")
    print(f"   Efektivita: {r['efficiency']:.2f} %")
    print(f"   Neinvestováno: {r['uninvested_amount']:.2f} USD")
    print(f"   Celkem: {r['total_amount']:.2f} USD")
    print(f"   Fill rate: {fills}")
    print(f"   Limit %: {r['percent_limit_invest']:.1f} %")
    print(f"   Market %: {r['percent_market_invest']:.1f} %\n")


# ==== 2. TOP podle BTC ====
top_btc = sorted(results, key=lambda x: x['total_btc'], reverse=True)[:5]

print("\n📊 TOP 5 strategií podle množství BTC:")
for i, r in enumerate(top_btc, 1):
    fills = {k: round(v * 100, 1) for k, v in r['avg_fill_rate'].items()}

    print(f"{i}. Váhy: {list(r['weights'])}, Tržní nákup: {list(r['market_buy_for'])}")
    print(f"   BTC: {r['total_btc']:.6f}")
    print(f"   Průměrná cena: {r['avg_price']:.2f} USD")
    print(f"   ROI: {r['ROI']:.2f} %")
    print(f"   ROI p.a.: {r['ROI_pa']:.2f} %")
    print(f"   Zisk: {r['total_profit']:.2f} USD")
    print(f"   Efektivita: {r['efficiency']:.2f} %")
    print(f"   Fill rate: {fills}")
    print(f"   Limit %: {r['percent_limit_invest']:.1f} %")
    print(f"   Market %: {r['percent_market_invest']:.1f} %\n")


# ==== 3. TOP podle ROI ====
top_roi = sorted(results, key=lambda x: x['ROI'], reverse=True)[:5]

print("\n📊 TOP 5 strategií podle ROI:")
for i, r in enumerate(top_roi, 1):
    fills = {k: round(v * 100, 1) for k, v in r['avg_fill_rate'].items()}

    print(f"{i}. Váhy: {list(r['weights'])}, Tržní nákup: {list(r['market_buy_for'])}")
    print(f"   ROI: {r['ROI']:.2f} %")
    print(f"   ROI p.a.: {r['ROI_pa']:.2f} %")
    print(f"   Zisk: {r['total_profit']:.2f} USD")
    print(f"   BTC: {r['total_btc']:.6f}")
    print(f"   Průměrná cena: {r['avg_price']:.2f} USD")
    print(f"   Efektivita: {r['efficiency']:.2f} %")
    print(f"   Fill rate: {fills}")
    print(f"   Limit %: {r['percent_limit_invest']:.1f} %")
    print(f"   Market %: {r['percent_market_invest']:.1f} %\n")


btfd_index_series = results[0]['btfd_index_series']
btfd_df = pd.DataFrame(
    btfd_index_series,
    columns=['Datetime', 'BTC_Close', 'ATH', 'BTFD', 'Multiplier']
)

st.dataframe(btfd_df)

mean_btfd = btfd_df['BTFD'].mean()
mean_multiplier = btfd_df['Multiplier'].mean()
#
#
# Vezmeme všechny multiplikátory
multipliers = btfd_df['Multiplier'].to_numpy()
adjusted_investments = multipliers * INVEST_PER_DAY
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
