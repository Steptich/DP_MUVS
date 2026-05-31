import streamlit as st
import datetime as dt
import tradesim as tr
from tradesim import HOUR, known_initial_ath, HISTORICAL_START
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import time

st.header("Porovnávač strategií")

st.markdown("""
            Tento porovnávač umožňuje zpětně porovnávat výkon libovolného počtu zadaných investičních strategií na základě historických tržních dat.
            Pro spuštění backtestu porovnávače je nezbytné pro všechny strategie zvolit společné časové období, transakční poplatky,
            výši pravidelné investice a nastavení multiplikátoru **&beta;** pro index **BTFD**, 
            kterým bude pro každou objednávku zvýšena či snížena investovaná částka podle aktuální hodnoty násobitele **&beta;**.
            Jednotlivé strategie lze nastavit skrze odlišené limitní příkazy pro nákupy v korekci. Předpokládaná frekvence nákupu je 1x denně.

            Vyhodnocení strategií se provádí na základě klíčových metrik: zhodnocení investice (ROI), 
            průměrná nákupní cena, celkový absolutní zisk z investice, množství nakoupeného BTC a efektivita využítí kapitálu.
            """, text_alignment="justify")

start = time.time()

btc_full = tr.load_btc_data()


last_dt = btc_full['Datetime'].max() - dt.timedelta(hours=(24-HOUR))
year_before = last_dt - dt.timedelta(days=365)

# --- Mapping pevně definovaných období ---
period_map = {
    "1 roku": 365,
    "2 let": 365 * 2,
    "3 let": 365 * 3,
    "4 let": 365 * 4,
    "5 let": 365 * 5,
}


date_option = st.selectbox(
    "Každodenní investice po dobu:",
    (*period_map.keys(), "Vlastní období"),
    key="date_option",
)

# --- Inicializace session_state (jen jednou) ---
if "start_date" not in st.session_state:
    st.session_state.start_date = year_before

if "end_date" not in st.session_state:
    st.session_state.end_date = last_dt

if date_option in period_map:
    days = period_map[date_option]

    st.session_state.end_date = last_dt
    st.session_state.start_date = last_dt - dt.timedelta(days=days)


elif date_option == "Vlastní období":
    # --- Callbacky ---
    def on_start_change():
        if st.session_state.start_date > st.session_state.end_date:
            st.session_state.end_date = st.session_state.start_date
    def on_end_change():
        if st.session_state.end_date < st.session_state.start_date:
            st.session_state.start_date = st.session_state.end_date

    # --- START DATE ---
    st.date_input(
        "Od:",
        key="start_date",
        min_value=HISTORICAL_START,
        max_value=st.session_state.end_date,
        format="DD.MM.YYYY",
        on_change=on_start_change,
    )

    # --- END DATE ---
    st.date_input(
        "Do:",
        key="end_date",
        min_value=st.session_state.start_date,
        max_value=last_dt,
        format="DD.MM.YYYY",
        on_change=on_end_change,
    )

btc = tr.get_filtered_data(
    btc_full,
    st.session_state.start_date,
    st.session_state.end_date
)
last_price = btc.iloc[-1]['Close']
ref_positions = np.where(btc['Datetime'].dt.hour == HOUR)[0]
print(f"Počet záznamů pro simulaci: {len(btc)}")


# české měsíce
cz_months = {
    1: "leden", 2: "únor", 3: "březen", 4: "duben",
    5: "květen", 6: "červen", 7: "červenec", 8: "srpen",
    9: "září", 10: "říjen", 11: "listopad", 12: "prosinec"
}

print(f"Počet záznamů pro simulaci: {len(btc)}")

# české měsíce
cz_months = {
    1: "leden", 2: "únor", 3: "březen", 4: "duben",
    5: "květen", 6: "červen", 7: "červenec", 8: "srpen",
    9: "září", 10: "říjen", 11: "listopad", 12: "prosinec"
}

# data (1x denně)
btc_filter_key = f"{st.session_state.start_date}_{st.session_state.end_date}"
if 'btc_thinned' not in st.session_state or st.session_state.get('last_btc_filter_key_thinned') != btc_filter_key:
    btc["hour"] = btc["Datetime"].dt.hour
    st.session_state.btc_thinned = btc[btc["hour"] == HOUR].copy()
    st.session_state.last_btc_filter_key_thinned = btc_filter_key

btc_thinned = st.session_state.btc_thinned

plot_key = f"{st.session_state.start_date}_{st.session_state.end_date}"

# tooltip
if 'btc_plot_key' not in st.session_state or st.session_state.btc_plot_key != plot_key:
    # --- Připrav graf jen pokud se změnil časový rozsah ---
    btc_thinned['date_cz'] = (
            btc_thinned['Datetime'].dt.day.astype(str) + ". " +
            btc_thinned['Datetime'].dt.month.map(cz_months) + " " +
            btc_thinned['Datetime'].dt.year.astype(str)
    )

    btc_fig = px.line(
        btc_thinned,
        x="Datetime",
        y="Close",
    )

    # formát osy X
    btc_fig.update_xaxes(
        tickformat="%d.%m.%Y",  # formát osy
        showgrid=True,  # zapnutí vertikálních grid line
        gridwidth=1,  # tloušťka gridu
        tickangle=-45,  # naklonění tick labelů
        range=[
            btc_thinned["Datetime"].min(),
            btc_thinned["Datetime"].max() + dt.timedelta(days=2)
        ]
    )

    btc_fig.update_layout(
        xaxis_title="Čas",
        yaxis_title="Cena (USD)",
        hovermode="x unified"
    )

    # tooltip
    btc_fig.update_traces(
        line=dict(color="#F7931A", width=1.5),
        customdata=btc_thinned['date_cz'],
        hovertemplate=(
                "<b>Cena:</b> %{y:.2f} USD<br>" +
                "<b>Datum:</b> %{customdata}" +
                "<extra></extra>"
        )
    )
    st.session_state.btc_fig = btc_fig
    st.session_state.btc_plot_key = plot_key

st.plotly_chart(st.session_state.btc_fig, key="btc_plot")

st.header("Nastavení dynamické strategie BTFD")

st.markdown("""
        Nastavte parametry pro výpočet multiplikátoru **&beta;**, který bude určovat výši investice pro každý nákup. 
        Multiplikátor bude vypočítán na základě indexu **BTFD**, který měří, jak moc je aktuální cena pod svým historickým maximem.

        Parametry můžete nastavit buď pomocí slideru, nebo zadáním konkrétní hodnoty do pole pro číslo. 
        Obě možnosti jsou synchronizované, takže změna v jednom z nich se projeví i v druhém.""",text_alignment="justify")

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
    "Maximální pokles uvažovaný pokles ceny pro výpočet multiplikátoru **&beta;** [%]:",
    min_value=10,
    max_value=90,
    step=1,
    key="btfdmin_number",
    on_change=min_number_changed
)

# --- Slider ---
st.slider(
    " ",
    min_value=10,
    max_value=90,
    step=1,
    key="btfdmin_slider",
    on_change=min_slider_changed,
    label_visibility="collapsed"
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
    "Maximální hodnota multiplikátoru **&beta;**:",
    min_value=1.0,
    max_value=10.0,
    step=0.1,
    format="%0.1f",
    key="btfd_number",
    on_change=number_changed
)

# --- Slider ---
st.slider(
    " ",
    min_value=1.0,
    max_value=10.0,
    step=0.1,
    format="%0.1f",
    key="btfdMULTI_slider",
    on_change=slider_changed,
    label_visibility="collapsed"
)

MAX_MULTIPLIER = st.session_state.btfdMULTI_slider

# --- Inicializace session_state pro fee_market ---
if "investment_number" not in st.session_state:
    st.session_state.investment_number = 100

# --- Number input fee_market ---
st.number_input(
    "Investovaná částka [USD]",
    min_value=10,
    max_value=10000,
    step=10,
    # format="%0.2f",
    key="investment_number",
)
INVEST_PER_DAY = st.session_state.investment_number

# 1) základní BTFD (NEMĚNÍ SE)
btfd_full = tr.compute_btfd_df(btc_full, known_initial_ath)

# --- 3. Ořez btfd pro simulaci ---
btfd_filter_key = f"{st.session_state.start_date}_{st.session_state.end_date}"
if 'btfd_filtered' not in st.session_state or st.session_state.get('last_btfd_filter_key') != btfd_filter_key:
    st.session_state.btfd_filtered = btfd_full[
        (btfd_full['Datetime'] >= pd.to_datetime(st.session_state.start_date)) &
        (btfd_full['Datetime'] <= pd.to_datetime(st.session_state.end_date + dt.timedelta(days=1)))
        ].sort_values('Datetime').drop_duplicates('Datetime').reset_index(drop=True)
    st.session_state.last_btfd_filter_key = btfd_filter_key

btfd = st.session_state.btfd_filtered

btfd_multiplier_key = f"{btfd_filter_key}_{BTFD_MIN}_{MAX_MULTIPLIER}"
if 'btfd_with_multiplier' not in st.session_state or st.session_state.get(
        'last_btfd_multiplier_key') != btfd_multiplier_key:
    btfd_with_multiplier = tr.add_multiplier(
        btfd,
        BTFD_MIN,
        MAX_MULTIPLIER
    )
    st.session_state.btfd_with_multiplier = btfd_with_multiplier
    st.session_state.last_btfd_multiplier_key = btfd_multiplier_key

btfd = st.session_state.btfd_with_multiplier

multipliers = btfd['Multiplier'].to_numpy()

st.header("Nastavení poplatků pro simulaci")

st.markdown("""
            Na každé kryptoburze nebo směnárně se platí transakční poplatky za spostředkování obchodu.
            Pozice, které dodávají likviditu na trh (limitní příkazy) jsou zpravidla zvýhodněné oproti pozicím, 
            které likviditu na trhu odebírají (tržní příkazy). Poplatky mohou hrát významnou roli v celkové výkonnosti 
            investiční strategie, zejména u strategií s častými obchody, jako je DCA.

            Zadejte poplatky pro limitní a tržní příkazy, které budou použity v simulaci. Poplatky můžete 
            nastavit buď pomocí slideru, nebo zadáním konkrétní hodnoty do pole pro číslo. 
            Obě možnosti jsou synchronizované.""",text_alignment="justify")


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
    "Poplatek za limitní příkaz [%]",
    min_value=0.0,
    max_value=1.0,
    step=0.01,
    format="%0.2f",
    key="fee_limit_number",
    on_change=fee_limit_number_changed
)

# --- Slider fee_limit ---
st.slider(
    " ",
    min_value=0.0,
    max_value=1.0,
    step=0.01,
    format="%0.2f",
    key="fee_limit_slider",
    on_change=fee_limit_slider_changed,
    label_visibility="collapsed"
)

FEE_LIMIT = st.session_state.fee_limit_slider / 100

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
    "Poplatek za tržní příkaz [%]",
    min_value=0.0,
    max_value=1.0,
    step=0.01,
    format="%0.2f",
    key="fee_market_number",
    on_change=fee_market_number_changed
)

# --- Slider fee_market ---
st.slider(
    " ",
    min_value=0.0,
    max_value=1.0,
    step=0.01,
    format="%0.2f",
    key="fee_market_slider",
    on_change=fee_market_slider_changed,
    label_visibility="collapsed"
)

FEE_MARKET = st.session_state.fee_market_slider / 100


limit_levels = (0, 1, 2, 3, 4, 5)
limit_multipliers = np.array([1 - lvl / 100 for lvl in limit_levels])


def df_to_hash(df: pd.DataFrame) -> int:
    return hash((tuple(df.columns), tuple(df.to_numpy().flatten())))


@st.cache_data
def build_market_mask(limit_levels, market_set):
    market_set = set(market_set)
    return np.isin(limit_levels, list(market_set))


@st.cache_data(hash_funcs={pd.DataFrame: df_to_hash, tuple: hash, frozenset: lambda x: hash(tuple(sorted(x)))})
def simulate_configuration(
        weights,
        market_set,
        btc,
        ref_positions,
        limit_levels,
        limit_multipliers,
        invest,
        btfd,
        fee_limit,
        fee_market
):
    market_mask = build_market_mask(limit_levels, market_set)

    # --- použij list, simulate_day_hourly do něj appenduje ---
    n_days = len(ref_positions)

    avg_prices_series = np.zeros((n_days), dtype=np.float64)
    total_cost_series = np.zeros((n_days), dtype=np.float64)
    total_btc_series = np.zeros((n_days), dtype=np.float64)
    total_profit_series = np.zeros((n_days), dtype=np.float64)
    total_value_series = np.zeros((n_days), dtype=np.float64)
    total_roi_series = np.zeros((n_days), dtype=np.float64)
    btfd_value_series = np.full((n_days,), -1, dtype=np.float64)
    btfd_multiplier_series = np.zeros((n_days), dtype=np.float64)
    buy_date_series = np.zeros((n_days,), dtype="datetime64[ns]")

    total_btc = total_cost = count_days = 0
    total_limit = total_market = 0
    closes_all = btc['Close'].values

    fills_sum = np.zeros(len(limit_levels), dtype=np.float32)

    simulate_day = tr.simulate_day_hourly
    valid_days_mask = np.zeros(n_days, dtype=bool)

    buy_indices = np.full(n_days, -1, dtype=int)  # pro pozdější vektorové přiřazení datumu

    for day_i, start_idx in enumerate(ref_positions):
        res = simulate_day(
            btc,
            start_idx,
            weights,
            market_mask,
            invest,
            limit_levels,
            limit_multipliers,
            btfd,
            fee_limit,
            fee_market
        )

        if res is None:
            count_days = day_i  # posledni den nemusi byt nakup
            continue

        btc_bought, cost, fills, inv_l, inv_m, btfd_value, btfd_multiplier, buy_idx = res

        total_btc += btc_bought
        total_cost += cost
        total_btc_series[day_i] = total_btc
        total_cost_series[day_i] = total_cost
        total_value_series[day_i] = total_btc * closes_all[start_idx + 24]
        btfd_value_series[day_i] = btfd_value
        btfd_multiplier_series[day_i] = btfd_multiplier
        valid_days_mask[day_i] = True
        buy_indices[day_i] = buy_idx
        count_days = day_i
        total_limit += inv_l
        total_market += inv_m

        fills_sum += fills

    if count_days == 0:
        return None
    
    # vektorové přiřazení datumu pro platné dny
    buy_date_series[valid_days_mask] = btc['Datetime'].values[buy_indices[valid_days_mask]]

    
    total_btc_series = total_btc_series[valid_days_mask]
    total_cost_series = total_cost_series[valid_days_mask]
    total_value_series = total_value_series[valid_days_mask]
    btfd_value_series = btfd_value_series[valid_days_mask]
    btfd_multiplier_series = btfd_multiplier_series[valid_days_mask]
    buy_date_series = buy_date_series[valid_days_mask]

    total_profit_series = total_value_series - total_cost_series
    avg_prices_series = np.divide(
        total_cost_series,
        total_btc_series,
        out=np.zeros_like(total_cost_series),
        where=total_cost_series != 0
    )
    total_roi_series = np.divide(
        total_profit_series,
        total_cost_series,
        out=np.zeros_like(total_profit_series),
        where=total_cost_series != 0
    ) * 100

    #setting correct values for the last day (in case last day(s) had no purchase)
    last_valid_idx = np.max(np.where(total_cost_series != 0))
    final_value = total_btc * last_price
    final_profit = final_value - total_cost
    final_roi = (final_profit / total_cost) * 100

    total_value_series[last_valid_idx] = final_value
    total_profit_series[last_valid_idx] = final_profit
    total_roi_series[last_valid_idx] = final_roi

    return {
        "weights": weights,
        "market_buy_for": tuple(sorted(market_set)),
        "total_cost_series": total_cost_series,
        "total_btc_series": total_btc_series,
        "total_profit_series": total_profit_series,
        "total_value_series": total_value_series,
        "total_roi_series": total_roi_series,
        "avg_price_series": avg_prices_series,
        "btfd_value_series": btfd_value_series,
        "btfd_multiplier_series": btfd_multiplier_series,
        "buy_date_series": buy_date_series,
        "total_btc": total_btc,
        "total_cost": total_cost,
        "days": count_days,
        "total_profit": total_btc * last_price - total_cost,
        "ROI": (total_btc * last_price - total_cost) / total_cost * 100,
        "ROI_pa": (((total_btc * last_price) / total_cost) ** (1 / (count_days / 365)) - 1) * 100,
        "efficiency": total_cost / (count_days * invest) * 100,
        "uninvested_amount": count_days * invest - total_cost,
        "total_amount": total_btc * last_price + abs(count_days * invest - total_cost),
        "avg_fill_rate": {lvl: fills_sum[i] / count_days for i, lvl in enumerate(limit_levels)},
        "percent_limit_invest": 100 * total_limit / total_cost if total_cost else 0,
        "percent_market_invest": 100 * total_market / total_cost if total_cost else 0,
    }


def run_backtest(weights, market_set):
    results = []

    res = simulate_configuration(
        weights,
        frozenset(market_set),
        btc,
        ref_positions,
        limit_levels,
        limit_multipliers,
        INVEST_PER_DAY,
        btfd,
        FEE_LIMIT,
        FEE_MARKET
    )
    if res:
        results.append(res)

    return results

st.header("Nahrání strategií pro porovnání")

st.markdown("""
            Pro porovnání strategií nahrajte CSV nebo XLSX soubor, který bude obsahovat váhy pro jednotlivé úrovně korekce (sloupce `lvl_0`, `lvl_1`, ..., `lvl_5`).
            Každý řádek v souboru bude reprezentovat jednu strategii, přičemž váhy musí být v rozsahu 0–1 a jejich součet musí být roven 1.
            Po nahrání souboru se zobrazí tabulka s načtenými váhami a následně se spustí backtest pro každou strategii přes všechny možné kombinace tržních nákupů, které odpovídají zadaným váhám.""",text_alignment="justify")

uploaded_file = st.file_uploader("Vložte CSV/XLSX s váhami", type=["csv", "xlsx"])

all_results = []

if uploaded_file:

    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith("csv") else pd.read_excel(uploaded_file)

    required_cols = [f"lvl_{lvl}" for lvl in limit_levels]
    
    # nech jen relevantní sloupce, které existují
    df = df[[c for c in required_cols if c in df.columns]]

    row_cols = [c for c in required_cols if c in df.columns]

    # reset indexu => garantuje 0..n-1
    df = df.reset_index(drop=True)
    
    # strategie číslo odpovídá řádku (index + 1)
    df.insert(0, "Strategie č.", df.index + 1)
    
    st.write("Načtené váhy:")
    st.dataframe(df, hide_index=True)

    # chybějící sloupce
    missing = set(required_cols) - set(df.columns)
    if missing:
        st.error(f"Chybí sloupce {sorted(missing)}")

    else:      
        st.header("Výsledky a porovnání strategií")

        for seq_number, row in df.iterrows():


            weights = [row[col] for col in required_cols]

            # kontrola NaN / None
            if any(pd.isna(w) for w in weights):
                st.error(f"Řádek {seq_number}: obsahuje chybějící váhy, řádek bude přeskočen")
                continue

            if any((w < 0 or w > 1) for w in weights):
                st.error(f"Řádek {seq_number}: obsahuje váhy mimo rozsah 0–1, řádek bude přeskočen")
                continue

            # 1) načtení vah podle limit_levels
            weights = [row[f"lvl_{lvl}"] for lvl in limit_levels]

            total_weight = sum(weights)

            if total_weight > 1 + 1e-9:
                st.error(f"Řádek {seq_number}: součet vah je {total_weight:.4f} (> 1), řádek bude přeskočen")
                continue
            
            if total_weight < 1 - 1e-9:
                st.error(f"Řádek {seq_number}: součet vah je {total_weight:.4f} (< 1), řádek bude přeskočen")
                continue

            # 2) generování všech market kombinací
            market_sets = tr.generate_market_sets(limit_levels,weights)

            # 3) backtest přes všechny kombinace
            seq_results = []

            for market_set in market_sets:
                result = run_backtest(weights, market_set)

                seq_results.append({
                    "market_set": sorted(list(market_set)),
                    "result": result
                })

            all_results.append({
                "sequence": seq_number + 1,
                "weights": weights,
                "results": seq_results
            })

        df = pd.json_normalize(
            [
                {
                    "sequence": seq["sequence"],
                    "weights": seq["weights"],
                    "market_set": list(r["market_set"]),
                    **r["result"][0]
                }
                for seq in all_results
                for r in seq["results"]
            ]
        )


        if not df.empty:

            tab1a, tab2a, tab3a, tab4a, tab5a = st.tabs(["Procentuální zhodnocení", "Průměrná nákupní cena", "Celkový zisk", "Nakoupené množství BTC", "Využití kapitálu"])

            with tab1a:
                st.header("Nejlepší strategie podle ROI (%)")
                cols = st.columns(3)


                top3 = df.sort_values("ROI", ascending=False).head(3)
                bot3 = df.sort_values("ROI", ascending=True).head(3)

                for rank, (_, result) in enumerate(top3.iterrows()):
                      with cols[rank]:
                            if rank == 0: st.subheader(f"🥇 {result['ROI']:.2f} %")
                            if rank == 1: st.subheader(f"🥈 {result['ROI']:.2f} %")
                            if rank == 2: st.subheader(f"🥉 {result['ROI']:.2f} %")

                            result = result.to_dict()

                            fills = {
                                i: round(float(result[f"avg_fill_rate.{i}"]) * 100, 1)
                                for i in range(len(limit_levels))
                            }

                            st.write(f"""
                            Strategie č. {result['sequence']}  
                            Váhy: {list(result['weights'])}  
                            **Tržní nákup:** {list(result['market_set'])}
                            """)

                            st.write(f"- Průměrná cena: {result['avg_price_series'][-1]:.2f} USD")
                            st.write(f"- Celkové BTC: {result['total_btc']:.8f}")
                            st.write(f"- Celkově vložený kapitál: {result['total_cost']:.2f} USD")
                            st.write(f"- Počet dnů: {result['days']}")
                            st.write(f"- Celkový zisk: {result['total_profit']:.2f} USD")
                            st.write(f"- ROI: {result['ROI']:.2f} %")
                            st.write(f"- ROI p.a.: {result['ROI_pa']:.2f} %")
                            st.write(f"- Využití kapitálu: {result['efficiency']:.2f} %")

                            if result['uninvested_amount'] > 0:
                                st.write(f"- Neinvestováno: {result['uninvested_amount']:.2f} USD")
                            else:
                                st.write(f"- Přebytečně investováno: {-result['uninvested_amount']:.2f} USD")

                            st.write(f"- Celkem: {result['total_amount']:.2f} USD")
                            st.write(f"- Naplnění limitních příkazů: {fills}")
                            st.write(f"- Limit %: {result['percent_limit_invest']:.1f} %")
                            st.write(f"- Market %: {result['percent_market_invest']:.1f} %")

                st.header("Nejhorší strategie podle ROI (%)")
                cols = st.columns(3)

                for rank, (_, result) in enumerate(bot3.iterrows()):
                      with cols[rank]:
                            if rank == 0: st.subheader(f"🔻 {result['ROI']:.2f} %")
                            if rank == 1: st.subheader(f"🔻 {result['ROI']:.2f} %")
                            if rank == 2: st.subheader(f"🔻 {result['ROI']:.2f} %")

                            result = result.to_dict()

                            fills = {
                                i: round(float(result[f"avg_fill_rate.{i}"]) * 100, 1)
                                for i in range(len(limit_levels))
                            }

                            st.write(f"""
                            Strategie č. {result['sequence']}  
                            Váhy: {list(result['weights'])}  
                            **Tržní nákup:** {list(result['market_set'])}
                            """)

                            st.write(f"- Průměrná cena: {result['avg_price_series'][-1]:.2f} USD")
                            st.write(f"- Celkové BTC: {result['total_btc']:.8f}")
                            st.write(f"- Celkově vložený kapitál: {result['total_cost']:.2f} USD")
                            st.write(f"- Počet dnů: {result['days']}")
                            st.write(f"- Celkový zisk: {result['total_profit']:.2f} USD")
                            st.write(f"- ROI: {result['ROI']:.2f} %")
                            st.write(f"- ROI p.a.: {result['ROI_pa']:.2f} %")
                            st.write(f"- Využití kapitálu: {result['efficiency']:.2f} %")

                            if result['uninvested_amount'] > 0:
                                st.write(f"- Neinvestováno: {result['uninvested_amount']:.2f} USD")
                            else:
                                st.write(f"- Přebytečně investováno: {-result['uninvested_amount']:.2f} USD")

                            st.write(f"- Celkem: {result['total_amount']:.2f} USD")
                            st.write(f"- Naplnění limitních příkazů: {fills}")
                            st.write(f"- Limit %: {result['percent_limit_invest']:.1f} %")
                            st.write(f"- Market %: {result['percent_market_invest']:.1f} %")
            
            with tab2a:
                st.header("Nejlepší strategie podle průměrné nákupní ceny")
                cols = st.columns(3)
                df["avg_price_final"] = df["total_cost"] / df["total_btc"]

                top3 = df.sort_values("avg_price_final", ascending=True).head(3)
                bot3 = df.sort_values("avg_price_final", ascending=False).head(3)

                for rank, (_, result) in enumerate(top3.iterrows()):
                     with cols[rank]:
                            if rank == 0: st.subheader(f"🥇 {result['avg_price_final']:.0f} USD")
                            if rank == 1: st.subheader(f"🥈 {result['avg_price_final']:.0f} USD")
                            if rank == 2: st.subheader(f"🥉 {result['avg_price_final']:.0f} USD")
                            result = result.to_dict()

                            fills = {
                                i: round(float(result[f"avg_fill_rate.{i}"]) * 100, 1)
                                for i in range(len(limit_levels))
                            }

                            st.write(f"""
                            Strategie č. {result['sequence']}  
                            Váhy: {list(result['weights'])}  
                            **Tržní nákup:** {list(result['market_set'])}
                            """)

                            st.write(f"- Průměrná cena: {result['avg_price_series'][-1]:.2f} USD")
                            st.write(f"- Celkové BTC: {result['total_btc']:.8f}")
                            st.write(f"- Celkově vložený kapitál: {result['total_cost']:.2f} USD")
                            st.write(f"- Počet dnů: {result['days']}")
                            st.write(f"- Celkový zisk: {result['total_profit']:.2f} USD")
                            st.write(f"- ROI: {result['ROI']:.2f} %")
                            st.write(f"- ROI p.a.: {result['ROI_pa']:.2f} %")
                            st.write(f"- Využití kapitálu: {result['efficiency']:.2f} %")

                            if result['uninvested_amount'] > 0:
                                st.write(f"- Neinvestováno: {result['uninvested_amount']:.2f} USD")
                            else:
                                st.write(f"- Přebytečně investováno: {-result['uninvested_amount']:.2f} USD")

                            st.write(f"- Celkem: {result['total_amount']:.2f} USD")
                            st.write(f"- Naplnění limitních příkazů: {fills}")
                            st.write(f"- Limit %: {result['percent_limit_invest']:.1f} %")
                            st.write(f"- Market %: {result['percent_market_invest']:.1f} %")

                st.header("Nejhorší strategie podle průměrné nákupní ceny")
                cols = st.columns(3)

                for rank, (_, result) in enumerate(bot3.iterrows()):
                      with cols[rank]:
                            if rank == 0: st.subheader(f"🔻 {result['avg_price_final']:.0f} USD")
                            if rank == 1: st.subheader(f"🔻 {result['avg_price_final']:.0f} USD")
                            if rank == 2: st.subheader(f"🔻 {result['avg_price_final']:.0f} USD")

                            result = result.to_dict()

                            fills = {
                                i: round(float(result[f"avg_fill_rate.{i}"]) * 100, 1)
                                for i in range(len(limit_levels))
                            }

                            st.write(f"""
                            Strategie č. {result['sequence']}  
                            Váhy: {list(result['weights'])}  
                            **Tržní nákup:** {list(result['market_set'])}
                            """)

                            st.write(f"- Průměrná cena: {result['avg_price_series'][-1]:.2f} USD")
                            st.write(f"- Celkové BTC: {result['total_btc']:.8f}")
                            st.write(f"- Celkově vložený kapitál: {result['total_cost']:.2f} USD")
                            st.write(f"- Počet dnů: {result['days']}")
                            st.write(f"- Celkový zisk: {result['total_profit']:.2f} USD")
                            st.write(f"- ROI: {result['ROI']:.2f} %")
                            st.write(f"- ROI p.a.: {result['ROI_pa']:.2f} %")
                            st.write(f"- Využití kapitálu: {result['efficiency']:.2f} %")

                            if result['uninvested_amount'] > 0:
                                st.write(f"- Neinvestováno: {result['uninvested_amount']:.2f} USD")
                            else:
                                st.write(f"- Přebytečně investováno: {-result['uninvested_amount']:.2f} USD")

                            st.write(f"- Celkem: {result['total_amount']:.2f} USD")
                            st.write(f"- Naplnění limitních příkazů: {fills}")
                            st.write(f"- Limit %: {result['percent_limit_invest']:.1f} %")
                            st.write(f"- Market %: {result['percent_market_invest']:.1f} %")

            with tab3a:
                st.header("Nejlepší strategie podle celkového zisku")
                cols = st.columns(3)
                

                top3 = df.sort_values("total_profit", ascending=False).head(3)
                bot3 = df.sort_values("total_profit", ascending=True).head(3)
                
                for rank, (_, result) in enumerate(top3.iterrows()):
                      with cols[rank]:
                            if rank == 0: st.subheader(f"🥇 {result['total_profit']:.0f} USD")
                            if rank == 1: st.subheader(f"🥈 {result['total_profit']:.0f} USD")
                            if rank == 2: st.subheader(f"🥉 {result['total_profit']:.0f} USD")

                            result = result.to_dict()

                            fills = {
                                i: round(float(result[f"avg_fill_rate.{i}"]) * 100, 1)
                                for i in range(len(limit_levels))
                            }

                            st.write(f"""
                            Strategie č. {result['sequence']}  
                            Váhy: {list(result['weights'])}  
                            **Tržní nákup:** {list(result['market_set'])}
                            """)

                            st.write(f"- Průměrná cena: {result['avg_price_series'][-1]:.2f} USD")
                            st.write(f"- Celkové BTC: {result['total_btc']:.8f}")
                            st.write(f"- Celkově vložený kapitál: {result['total_cost']:.2f} USD")
                            st.write(f"- Počet dnů: {result['days']}")
                            st.write(f"- Celkový zisk: {result['total_profit']:.2f} USD")
                            st.write(f"- ROI: {result['ROI']:.2f} %")
                            st.write(f"- ROI p.a.: {result['ROI_pa']:.2f} %")
                            st.write(f"- Využití kapitálu: {result['efficiency']:.2f} %")

                            if result['uninvested_amount'] > 0:
                                st.write(f"- Neinvestováno: {result['uninvested_amount']:.2f} USD")
                            else:
                                st.write(f"- Přebytečně investováno: {-result['uninvested_amount']:.2f} USD")

                            st.write(f"- Celkem: {result['total_amount']:.2f} USD")
                            st.write(f"- Naplnění limitních příkazů: {fills}")
                            st.write(f"- Limit %: {result['percent_limit_invest']:.1f} %")
                            st.write(f"- Market %: {result['percent_market_invest']:.1f} %")

                st.header("Nejhorší strategie podle celkového zisku")
                cols = st.columns(3)

                for rank, (_, result) in enumerate(bot3.iterrows()):
                      with cols[rank]:
                            if rank == 0: st.subheader(f"🔻 {result['total_profit']:.0f} USD")
                            if rank == 1: st.subheader(f"🔻 {result['total_profit']:.0f} USD")
                            if rank == 2: st.subheader(f"🔻 {result['total_profit']:.0f} USD")

                            result = result.to_dict()

                            fills = {
                                i: round(float(result[f"avg_fill_rate.{i}"]) * 100, 1)
                                for i in range(len(limit_levels))
                            }

                            st.write(f"""
                            Strategie č. {result['sequence']}  
                            Váhy: {list(result['weights'])}  
                            **Tržní nákup:** {list(result['market_set'])}
                            """)

                            st.write(f"- Průměrná cena: {result['avg_price_series'][-1]:.2f} USD")
                            st.write(f"- Celkové BTC: {result['total_btc']:.8f}")
                            st.write(f"- Celkově vložený kapitál: {result['total_cost']:.2f} USD")
                            st.write(f"- Počet dnů: {result['days']}")
                            st.write(f"- Celkový zisk: {result['total_profit']:.2f} USD")
                            st.write(f"- ROI: {result['ROI']:.2f} %")
                            st.write(f"- ROI p.a.: {result['ROI_pa']:.2f} %")
                            st.write(f"- Využití kapitálu: {result['efficiency']:.2f} %")

                            if result['uninvested_amount'] > 0:
                                st.write(f"- Neinvestováno: {result['uninvested_amount']:.2f} USD")
                            else:
                                st.write(f"- Přebytečně investováno: {-result['uninvested_amount']:.2f} USD")

                            st.write(f"- Celkem: {result['total_amount']:.2f} USD")
                            st.write(f"- Naplnění limitních příkazů: {fills}")
                            st.write(f"- Limit %: {result['percent_limit_invest']:.1f} %")
                            st.write(f"- Market %: {result['percent_market_invest']:.1f} %")
            with tab4a:
                st.header("Nejlepší strategie podle nakoupeného množství BTC")
                cols = st.columns(3)


                top3 = df.sort_values("total_btc", ascending=False).head(3)
                bot3 = df.sort_values("total_btc", ascending=True).head(3)

                for rank, (_, result) in enumerate(top3.iterrows()):
                      with cols[rank]:
                            if rank == 0: st.subheader(f"🥇 {result['total_btc']:.8f}")
                            if rank == 1: st.subheader(f"🥈 {result['total_btc']:.8f}")
                            if rank == 2: st.subheader(f"🥉 {result['total_btc']:.8f}")

                            result = result.to_dict()

                            fills = {
                                i: round(float(result[f"avg_fill_rate.{i}"]) * 100, 1)
                                for i in range(len(limit_levels))
                            }

                            st.write(f"""
                            Strategie č. {result['sequence']}  
                            Váhy: {list(result['weights'])}  
                            **Tržní nákup:** {list(result['market_set'])}
                            """)

                            st.write(f"- Průměrná cena: {result['avg_price_series'][-1]:.2f} USD")
                            st.write(f"- Celkové BTC: {result['total_btc']:.8f}")
                            st.write(f"- Celkově vložený kapitál: {result['total_cost']:.2f} USD")
                            st.write(f"- Počet dnů: {result['days']}")
                            st.write(f"- Celkový zisk: {result['total_profit']:.2f} USD")
                            st.write(f"- ROI: {result['ROI']:.2f} %")
                            st.write(f"- ROI p.a.: {result['ROI_pa']:.2f} %")
                            st.write(f"- Využití kapitálu: {result['efficiency']:.2f} %")

                            if result['uninvested_amount'] > 0:
                                st.write(f"- Neinvestováno: {result['uninvested_amount']:.2f} USD")
                            else:
                                st.write(f"- Přebytečně investováno: {-result['uninvested_amount']:.2f} USD")

                            st.write(f"- Celkem: {result['total_amount']:.2f} USD")
                            st.write(f"- Naplnění limitních příkazů: {fills}")
                            st.write(f"- Limit %: {result['percent_limit_invest']:.1f} %")
                            st.write(f"- Market %: {result['percent_market_invest']:.1f} %")

                st.header("Nejhorší strategie podle nakoupeného množství BTC")
                cols = st.columns(3)

                for rank, (_, result) in enumerate(bot3.iterrows()):
                      with cols[rank]:
                            if rank == 0: st.subheader(f"🔻 {result['total_btc']:.8f}")
                            if rank == 1: st.subheader(f"🔻 {result['total_btc']:.8f}")
                            if rank == 2: st.subheader(f"🔻 {result['total_btc']:.8f}")

                            result = result.to_dict()

                            fills = {
                                i: round(float(result[f"avg_fill_rate.{i}"]) * 100, 1)
                                for i in range(len(limit_levels))
                            }

                            st.write(f"""
                            Strategie č. {result['sequence']}  
                            Váhy: {list(result['weights'])}  
                            **Tržní nákup:** {list(result['market_set'])}
                            """)

                            st.write(f"- Průměrná cena: {result['avg_price_series'][-1]:.2f} USD")
                            st.write(f"- Celkové BTC: {result['total_btc']:.8f}")
                            st.write(f"- Celkově vložený kapitál: {result['total_cost']:.2f} USD")
                            st.write(f"- Počet dnů: {result['days']}")
                            st.write(f"- Celkový zisk: {result['total_profit']:.2f} USD")
                            st.write(f"- ROI: {result['ROI']:.2f} %")
                            st.write(f"- ROI p.a.: {result['ROI_pa']:.2f} %")
                            st.write(f"- Využití kapitálu: {result['efficiency']:.2f} %")

                            if result['uninvested_amount'] > 0:
                                st.write(f"- Neinvestováno: {result['uninvested_amount']:.2f} USD")
                            else:
                                st.write(f"- Přebytečně investováno: {-result['uninvested_amount']:.2f} USD")

                            st.write(f"- Celkem: {result['total_amount']:.2f} USD")
                            st.write(f"- Naplnění limitních příkazů: {fills}")
                            st.write(f"- Limit %: {result['percent_limit_invest']:.1f} %")
                            st.write(f"- Market %: {result['percent_market_invest']:.1f} %")

            with tab5a:
                st.header("Nejlepší strategie podle využití kapitálu")
                cols = st.columns(3)


                top3 = df.sort_values("efficiency", ascending=False).head(3)
                bot3 = df.sort_values("efficiency", ascending=True).head(3)

                for rank, (_, result) in enumerate(top3.iterrows()):
                      with cols[rank]:
                            if rank == 0: st.subheader(f"🥇 {result['efficiency']:.2f} %")
                            if rank == 1: st.subheader(f"🥈 {result['efficiency']:.2f} %")
                            if rank == 2: st.subheader(f"🥉 {result['efficiency']:.2f} %")

                            result = result.to_dict()

                            fills = {
                                i: round(float(result[f"avg_fill_rate.{i}"]) * 100, 1)
                                for i in range(len(limit_levels))
                            }

                            st.write(f"""
                            Strategie č. {result['sequence']}  
                            Váhy: {list(result['weights'])}  
                            **Tržní nákup:** {list(result['market_set'])}
                            """)

                            st.write(f"- Průměrná cena: {result['avg_price_series'][-1]:.2f} USD")
                            st.write(f"- Celkové BTC: {result['total_btc']:.8f}")
                            st.write(f"- Celkově vložený kapitál: {result['total_cost']:.2f} USD")
                            st.write(f"- Počet dnů: {result['days']}")
                            st.write(f"- Celkový zisk: {result['total_profit']:.2f} USD")
                            st.write(f"- ROI: {result['ROI']:.2f} %")
                            st.write(f"- ROI p.a.: {result['ROI_pa']:.2f} %")
                            st.write(f"- Využití kapitálu: {result['efficiency']:.2f} %")

                            if result['uninvested_amount'] > 0:
                                st.write(f"- Neinvestováno: {result['uninvested_amount']:.2f} USD")
                            else:
                                st.write(f"- Přebytečně investováno: {-result['uninvested_amount']:.2f} USD")

                            st.write(f"- Celkem: {result['total_amount']:.2f} USD")
                            st.write(f"- Naplnění limitních příkazů: {fills}")
                            st.write(f"- Limit %: {result['percent_limit_invest']:.1f} %")
                            st.write(f"- Market %: {result['percent_market_invest']:.1f} %")

                st.header("Nejhorší strategie podle využití kapitálu")
                cols = st.columns(3)

                for rank, (_, result) in enumerate(bot3.iterrows()):
                      with cols[rank]:
                            if rank == 0: st.subheader(f"🔻 {result['efficiency']:.2f} %")
                            if rank == 1: st.subheader(f"🔻 {result['efficiency']:.2f} %")
                            if rank == 2: st.subheader(f"🔻 {result['efficiency']:.2f} %")

                            result = result.to_dict()

                            fills = {
                                i: round(float(result[f"avg_fill_rate.{i}"]) * 100, 1)
                                for i in range(len(limit_levels))
                            }

                            st.write(f"""
                            Strategie č. {result['sequence']}  
                            Váhy: {list(result['weights'])}  
                            **Tržní nákup:** {list(result['market_set'])}
                            """)

                            st.write(f"- Průměrná cena: {result['avg_price_series'][-1]:.2f} USD")
                            st.write(f"- Celkové BTC: {result['total_btc']:.8f}")
                            st.write(f"- Celkově vložený kapitál: {result['total_cost']:.2f} USD")
                            st.write(f"- Počet dnů: {result['days']}")
                            st.write(f"- Celkový zisk: {result['total_profit']:.2f} USD")
                            st.write(f"- ROI: {result['ROI']:.2f} %")
                            st.write(f"- ROI p.a.: {result['ROI_pa']:.2f} %")
                            st.write(f"- Využití kapitálu: {result['efficiency']:.2f} %")

                            if result['uninvested_amount'] > 0:
                                st.write(f"- Neinvestováno: {result['uninvested_amount']:.2f} USD")
                            else:
                                st.write(f"- Přebytečně investováno: {-result['uninvested_amount']:.2f} USD")

                            st.write(f"- Celkem: {result['total_amount']:.2f} USD")
                            st.write(f"- Naplnění limitních příkazů: {fills}")
                            st.write(f"- Limit %: {result['percent_limit_invest']:.1f} %")
                            st.write(f"- Market %: {result['percent_market_invest']:.1f} %")
        else:
            st.write("Nenalezen žádný validní výsledek. Zkontrolujte součet vah a formát dat.")
st.write("---")

# --- BTFD statistika ---

mean_btfd = btfd['BTFD'].mean()
mean_multiplier = btfd['Multiplier'].mean()
#
#
# Vezmeme všechny multiplikátory
adjusted_investments = multipliers * INVEST_PER_DAY
# Medián denní investice
median_daily_invest = np.median(adjusted_investments)
# Medián měsíční investice (30 dní)
median_monthly_invest = median_daily_invest * 30

# st.write("## 📈 Statistika BTFD indikátoru a multiplikátoru")
# st.write(f"- Průměrná hodnota BTFD indikátoru: {mean_btfd:.2f} %")
# st.write(f"- Průměrná hodnota multiplikátoru: {mean_multiplier:.3f}×")
# st.write(f"- Odpovídající průměrná denní investice: {mean_multiplier * INVEST_PER_DAY:.2f} USD")
# st.write(f"- Odpovídající průměrná měsíční investice (30 dní): {mean_multiplier * INVEST_PER_DAY * 30:.2f} USD")
# st.write(f"- Medián denní investice: {median_daily_invest:.2f} USD")
# st.write(f"- Medián měsíční investice: {median_monthly_invest:.2f} USD")

end = time.time()

#st.write(f"Total runtime of the program is {end - start} seconds")