import streamlit as st
import datetime as dt
import tradesim as tr
from tradesim import HOUR, known_initial_ath, HISTORICAL_START
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import time


st.header("HANIČKA JE ŠIKULKA")

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
        tickformat="%d.%m.%Y",   # formát osy
        showgrid=True,            # zapnutí vertikálních grid line
        gridwidth=1,              # tloušťka gridu
        tickangle=-45,             # naklonění tick labelů
        range=[
            btc_thinned["Datetime"].min(),
            btc_thinned["Datetime"].max()+ dt.timedelta(days=2)
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

st.plotly_chart(st.session_state.btc_fig,key="btc_plot")


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


# --- Inicializace session_state pro fee_market ---
if "investment_number" not in st.session_state:
    st.session_state.investment_number = 100


# --- Number input fee_market ---
st.number_input(
    "Investment (USD)",
    min_value=10,
    max_value=10000,
    step=10,
    #format="%0.2f",
    key="investment_number",
)
INVEST_PER_DAY = st.session_state.investment_number


# 1) základní BTFD (NEMĚNÍ SE)
btfd_full = tr.compute_btfd_df(btc_full, known_initial_ath)

# --- 3. Ořez btfd pro simulaci ---
btfd_filter_key = f"{st.session_state.start_date}_{st.session_state.end_date}"
if'btfd_filtered' not in st.session_state or st.session_state.get('last_btfd_filter_key') != btfd_filter_key:
    st.session_state.btfd_filtered = btfd_full[
        (btfd_full['Datetime'] >= pd.to_datetime(st.session_state.start_date)) &
        (btfd_full['Datetime'] <= pd.to_datetime(st.session_state.end_date+dt.timedelta(days=1)))
    ].sort_values('Datetime').drop_duplicates('Datetime').reset_index(drop=True)
    st.session_state.last_btfd_filter_key = btfd_filter_key

btfd = st.session_state.btfd_filtered

btfd_multiplier_key = f"{btfd_filter_key}_{BTFD_MIN}_{MAX_MULTIPLIER}"
if 'btfd_with_multiplier' not in st.session_state or st.session_state.get('last_btfd_multiplier_key') != btfd_multiplier_key:
    btfd_with_multiplier = tr.add_multiplier(
        btfd,
        BTFD_MIN,
        MAX_MULTIPLIER
    )
    st.session_state.btfd_with_multiplier = btfd_with_multiplier
    st.session_state.last_btfd_multiplier_key = btfd_multiplier_key

btfd = st.session_state.btfd_with_multiplier

multipliers = btfd['Multiplier'].to_numpy()

btfd_thinned_key = f"{btfd_multiplier_key}_{INVEST_PER_DAY}_24"

if ('btfd_thinned' not in st.session_state
    or st.session_state.get('last_btfd_thinned_key') != btfd_thinned_key
):
    btfd["hour"] = btfd["Datetime"].dt.hour
    btfd_thinned = btfd[btfd["hour"] == HOUR].copy()
    btfd_thinned["Cumulative"] = (
    (btfd_thinned["Multiplier"] * INVEST_PER_DAY)
    .cumsum()
    .shift(1, fill_value=0)
    )

    st.session_state.btfd_thinned = btfd_thinned
    st.session_state.last_btfd_thinned_key = btfd_thinned_key

btfd_thinned = st.session_state.btfd_thinned

tab1, tab2, tab3, tab4 = st.tabs(["BTFD", "Multiplikátor","Nákupní částka", "Investovaná částka"])

plot_key1 = (
    f"{st.session_state.start_date}_{st.session_state.end_date}_"
    f"{st.session_state.btfdmin_slider}_{st.session_state.btfdMULTI_slider}"
    f"{st.session_state.investment_number}"
)

# tooltip
if 'btfd_plot_key' not in st.session_state or st.session_state.btfd_plot_key != plot_key1:

    # --- Připrav graf jen pokud se změnil časový rozsah ---
    btfd_thinned['date_cz'] = (
        btfd_thinned['Datetime'].dt.day.astype(str) + ". " +
        btfd_thinned['Datetime'].dt.month.map(cz_months) + " " +
        btfd_thinned['Datetime'].dt.year.astype(str)
    )
    
    btfd_fig = px.line(
        btfd_thinned,
        x="Datetime",
        y="BTFD",
    )

    btfd_fig.add_hline(y=BTFD_MIN, line_dash="dash", line_color="red", annotation_text=f"{BTFD_MIN} %", annotation_position="bottom right")
    btfd_fig.add_hline(y=0.0, line_dash="dash", line_color="red", annotation_text=f"0 %", annotation_position="top right")
    
    # formát osy X
    btfd_fig.update_xaxes(
        tickformat="%d.%m.%Y",   # formát osy
        showgrid=True,            # zapnutí vertikálních grid line
        gridwidth=1,              # tloušťka gridu
        tickangle=-45,            # naklonění tick labelů
        range=[
            btfd_thinned["Datetime"].min(),
            btfd_thinned["Datetime"].max()+ dt.timedelta(days=2)
        ]
    )

    btfd_fig.update_layout(
        xaxis_title="Čas",
        yaxis_title="Hodnota indexu BTFD [%]",
        hovermode="x unified"
    )

        # tooltip
    btfd_fig.update_traces(
        line=dict(color="blue", width=1.5),
        customdata=btc_thinned['date_cz'],
        hovertemplate=(
            "<b>Hodnota BTFD:</b> %{y:.2f}%<br>" +
            "<b>Datum:</b> %{customdata}" +
            "<extra></extra>"
        )
    )


    multiplier_fig = px.line(
        btfd_thinned,
        x="Datetime",
        y="Multiplier",
    )
    multiplier_fig.add_hline(y=MAX_MULTIPLIER, line_dash="dash", line_color="green", annotation_text=f"Max: {MAX_MULTIPLIER}x", annotation_position="top right")
    multiplier_fig.add_hline(y=1.0, line_dash="dash", line_color="green", annotation_text=f"Min: 1.0x", annotation_position="bottom right")
    
    # formát osy X
    multiplier_fig.update_xaxes(
        tickformat="%d.%m.%Y",   # formát osy
        showgrid=True,            # zapnutí vertikálních grid line
        gridwidth=1,              # tloušťka gridu
        tickangle=-45,            # naklonění tick labelů
        range=[
            btfd_thinned["Datetime"].min(),
            btfd_thinned["Datetime"].max()+ dt.timedelta(days=2)
        ]
    )

    multiplier_fig.update_layout(
        xaxis_title="Čas",
        yaxis_title="Hodnota multiplikátoru",
        hovermode="x unified"
    )

        # tooltip
    multiplier_fig.update_traces(
        line=dict(color="red", width=1.5),
        customdata=btc_thinned['date_cz'],
        hovertemplate=(
            "<b>Hodnota multiplikátoru:</b> %{y:.2f}x<br>" +
            "<b>Datum:</b> %{customdata}" +
            "<extra></extra>"
        )
    )

    
    buy_fig = px.line(
        btfd_thinned,
        x="Datetime",
        y=btfd_thinned["Multiplier"]*INVEST_PER_DAY
    )
    buy_fig.add_hline(y=INVEST_PER_DAY, line_dash="dash", line_color="#F7931A",  annotation_text=f"Fixní investice: {INVEST_PER_DAY} USD", annotation_position="bottom right")
    
    buy_fig.update_xaxes(
        tickformat="%d.%m.%Y",   # formát osy
        showgrid=True,            # zapnutí vertikálních grid line
        gridwidth=1,              # tloušťka gridu
        tickangle=-45,             # naklonění tick labelů
        range=[
            btc_thinned["Datetime"].min(),
            btc_thinned["Datetime"].max()+ dt.timedelta(days=2)
        ]
    )

    buy_fig.update_layout(
        xaxis_title="Čas",
        yaxis_title="Nákupní částka [USD]",
        hovermode="x unified"
    )   

    buy_fig.update_traces(
        line=dict(color="green", width=1.5),
        customdata=btc_thinned['date_cz'],
        hovertemplate=(
            "<b>Investovaná částka:</b> %{y:.2f} USD<br>" +
            "<b>Datum:</b> %{customdata}" +
            "<extra></extra>"
        )
    )

    invest_fig = go.Figure()

    # --- spodní: dynamická (plná) ---
    invest_fig.add_trace(
        go.Scatter(
            x=btfd_thinned["Datetime"],
            y=btfd_thinned["Cumulative"],
            mode="lines",
            line=dict(color="green", width=1.5),
            name="Dynamická investice",
            customdata=btc_thinned['date_cz'],
            hovertemplate="<b>Celkově investováno (dynamická částka):</b> %{y:.2f} USD<br><b>Datum:</b> %{customdata}<extra></extra>"
        )
    )

    # --- vrchní: fixní (dash) ---
    invest_fig.add_trace(
        go.Scatter(
            x=btfd_thinned["Datetime"],
            y=INVEST_PER_DAY * np.arange(len(btfd_thinned)),
            mode="lines",
            line=dict(color="#F7931A", dash="dash", width=1.5),
            name=f"Fixní investice: {INVEST_PER_DAY} USD",
            customdata=btc_thinned['date_cz'],
            hovertemplate="<b>Celkově investováno (fixní částka):</b> %{y:.2f} USD<br><b>Datum:</b> %{customdata}<extra></extra>"
        )
    )

    invest_fig.update_xaxes(
        tickformat="%d.%m.%Y",   # formát osy
        showgrid=True,            # zapnutí vertikálních grid line
        gridwidth=1,              # tloušťka gridu
        tickangle=-45,            # naklonění tick labelů
        range=[
            btfd_thinned["Datetime"].min(),
            btfd_thinned["Datetime"].max()+ dt.timedelta(days=2)
        ]
    )

    invest_fig.update_layout(
        xaxis_title="Čas",
        yaxis_title="Investovaná částka [USD]",
        hovermode="x unified",
        legend=dict(
            x=0.01,
            y=0.99,
            xanchor="left",
            yanchor="top",
        )
    )   

    invest_fig.data[0].update(
        customdata=btc_thinned['date_cz'],
        name="Dynamická investice",
        showlegend=True,
        hovertemplate=(
            "<b>Celkově investováno (dynamická částka):</b> %{y:.2f} USD<br>" +
            "<b>Datum:</b> %{customdata}" +
            "<extra></extra>"
        )
    ) 
    invest_fig.data[1].update(
        customdata=btc_thinned['date_cz'],
        hovertemplate=(
            "<b>Celkově investováno (fixní částka):</b> %{y:.2f} USD<br>" +
            "<b>Datum:</b> %{customdata}" +
            "<extra></extra>"
        )
    )  

    st.session_state.btfd_fig = btfd_fig
    st.session_state.multiplier_fig = multiplier_fig        
    st.session_state.buy_fig = buy_fig
    st.session_state.invest_fig = invest_fig
    st.session_state.btfd_plot_key = plot_key1

with tab1:
    st.plotly_chart(st.session_state.btfd_fig, key="btfd_plot")

with tab2:
    st.plotly_chart(st.session_state.multiplier_fig, key="multiplier_plot")

with tab3:
    st.plotly_chart(st.session_state.buy_fig, key="buy_plot")

with tab4:
    st.plotly_chart(st.session_state.invest_fig, key="invest_plot")


end = time.time()

st.write(f"Total runtime of the program is {end - start} seconds")