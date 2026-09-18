import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Анализ задержек авиарейсов",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Дашборд задержек авиарейсов")
st.markdown("Интерактивный анализ задержек и отмен рейсов за 2024 год.")


@st.cache_data
def load_data():
    needed_cols = [
        'fl_date', 'op_unique_carrier', 'origin', 'dest',
        'dep_delay', 'cancelled', 'month',
        'carrier_delay', 'weather_delay', 'nas_delay',
        'security_delay', 'late_aircraft_delay'
    ]

    dtypes = {
        'op_unique_carrier': 'category',
        'origin': 'category',
        'dest': 'category',
        'dep_delay': 'float32',
        'cancelled': 'float32',
        'month': 'int8',
        'carrier_delay': 'float32',
        'weather_delay': 'float32',
        'nas_delay': 'float32',
        'security_delay': 'float32',
        'late_aircraft_delay': 'float32',
    }

    df = pd.read_csv("flight_data_2024.csv", usecols=needed_cols, dtype=dtypes)
    df = df.dropna(subset=['dep_delay', 'op_unique_carrier'])
    return df


try:
    df = load_data()
except FileNotFoundError:
    st.error("Файл `flight_data_2024.csv` не найден. Положите его в папку с проектом.")
    st.stop()
except ValueError as e:
    st.error(f"Проблема с колонками в CSV: {e}")
    st.write("Реальные колонки файла:",
             pd.read_csv("flight_data_2024.csv", nrows=0).columns.tolist())
    st.stop()


# --- Словарь авиакомпаний и колонка carrier_name ---
airline_names = {
    '9E': 'Endeavor Air', 'AA': 'American Airlines', 'AS': 'Alaska Airlines',
    'B6': 'JetBlue Airways', 'DL': 'Delta Air Lines', 'F9': 'Frontier Airlines',
    'G4': 'Allegiant Air', 'HA': 'Hawaiian Airlines', 'NK': 'Spirit Airlines',
    'OH': 'PSA Airlines', 'OO': 'SkyWest Airlines', 'UA': 'United Airlines',
    'WN': 'Southwest Airlines', 'YX': 'Republic Airways', 'YV': 'Mesa Airlines'
}

df['carrier_name'] = (
    df['op_unique_carrier']
    .map(airline_names)
    .fillna(df['op_unique_carrier'])
    .astype('category')
)


# --- Фильтры ---
st.sidebar.header("🔍 Фильтры")

carriers = sorted(df["carrier_name"].unique().tolist())
selected_carriers = st.sidebar.multiselect(
    "Авиакомпании",
    options=carriers,
    default=carriers[:5]
)

months = sorted(df["month"].dropna().unique().tolist())
selected_months = st.sidebar.multiselect(
    "Месяцы",
    options=months,
    default=months
)

filtered = df[
    (df["carrier_name"].isin(selected_carriers)) &
    (df["month"].isin(selected_months))
]


# --- Ключевые показатели ---
st.subheader("📊 Ключевые показатели")

total_flights = len(filtered)
if total_flights == 0:
    st.warning("Нет данных для отображения. Попробуйте изменить фильтры.")
    st.stop()

delayed_flights = filtered[filtered["dep_delay"] > 15]
cancelled_flights = filtered[filtered["cancelled"] == 1]

col1, col2, col3, col4 = st.columns(4)

col1.metric("Всего рейсов", f"{total_flights:,}")
col2.metric(
    "Задержано (>15 мин)",
    f"{len(delayed_flights):,}",
    f"{len(delayed_flights) / total_flights * 100:.1f}%"
)
col3.metric(
    "Отменено",
    f"{len(cancelled_flights):,}",
    f"{len(cancelled_flights) / total_flights * 100:.1f}%"
)
col4.metric("Средняя задержка", f"{filtered['dep_delay'].mean():.1f} мин")


# --- График 1: Средняя задержка по авиакомпаниям ---
st.subheader("📈 Средняя задержка по авиакомпаниям")

delay_by_carrier = (
    filtered.groupby("carrier_name", observed=True)["dep_delay"]
    .mean()
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
)

fig1 = px.bar(
    delay_by_carrier,
    x="carrier_name",
    y="dep_delay",
    color="dep_delay",
    color_continuous_scale="Reds",
    labels={"carrier_name": "Авиакомпания", "dep_delay": "Средняя задержка (мин)"}
)
fig1.update_layout(showlegend=False)
st.plotly_chart(fig1, use_container_width=True)


# --- График 2: Динамика по месяцам ---
st.subheader("📅 Динамика задержек по месяцам")

delay_by_month = (
    filtered.groupby("month", observed=True)["dep_delay"]
    .mean()
    .reset_index()
)

fig2 = px.line(
    delay_by_month,
    x="month",
    y="dep_delay",
    markers=True,
    labels={"month": "Месяц", "dep_delay": "Средняя задержка (мин)"}
)
st.plotly_chart(fig2, use_container_width=True)


# --- График 3: Причины задержек ---
st.subheader("🔍 Причины задержек")

delay_causes = {
    "carrier_delay": "Авиакомпания",
    "weather_delay": "Погода",
    "nas_delay": "Авиадиспетчеры",
    "security_delay": "Безопасность",
    "late_aircraft_delay": "Поздний борт"
}

cause_data = []
for col, label in delay_causes.items():
    if col in filtered.columns:
        total_minutes = filtered[col].sum()
        if total_minutes > 0:
            cause_data.append({"Причина": label, "Минут": total_minutes})

if cause_data:
    cause_df = pd.DataFrame(cause_data)
    fig3 = px.pie(cause_df, values="Минут", names="Причина", hole=0.4)
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Данные о причинах задержек отсутствуют в выбранном срезе.")


# --- Таблица исходных данных ---
with st.expander("📋 Показать исходные данные"):
    st.dataframe(
        filtered[["fl_date", "carrier_name", "origin", "dest",
                  "dep_delay", "cancelled"]].head(100)
    )

st.caption("Данные: Flight Delay Dataset — 2024 (Kaggle)")
