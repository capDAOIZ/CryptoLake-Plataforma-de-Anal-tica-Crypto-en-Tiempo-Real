"""CryptoLake Streamlit dashboard (v3)."""

import os
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="CryptoLake Dashboard", page_icon="CL", layout="wide")


st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

      :root {
        --bg-0: #f5f8fc;
        --bg-1: #eaf2fb;
        --bg-2: #f9fbfe;
        --panel: rgba(255, 255, 255, 0.8);
        --line: rgba(64, 98, 128, 0.18);
        --txt: #0d2237;
        --muted: #4d6278;
        --accent: #0f9d80;
        --accent-2: #0e79d1;
        --danger: #d93f64;
      }

      .stApp {
        background:
          radial-gradient(900px 420px at 12% -20%, #e4f0fc 0%, rgba(228,240,252,0) 58%),
          radial-gradient(700px 420px at 90% 0%, #e6f5ef 0%, rgba(230,245,239,0) 48%),
          linear-gradient(180deg, var(--bg-1) 0%, var(--bg-0) 45%, var(--bg-2) 100%);
      }

      html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
        color: var(--txt);
      }

      .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
      }

      h1, h2, h3 {
        letter-spacing: 0.3px;
      }

      [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #eef5fc 0%, #f8fbff 100%);
        border-right: 1px solid var(--line);
      }

      [data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 12px 14px;
      }

      div[data-testid="stMetricValue"] {
        font-size: 1.45rem;
      }

      .hero {
        background: linear-gradient(120deg, rgba(15,157,128,0.08), rgba(14,121,209,0.07));
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 1rem 1.1rem;
        margin-bottom: 0.7rem;
      }

      .hero-kicker {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        color: var(--muted);
        margin-bottom: 0.2rem;
      }

      .hero-title {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
      }

      .hero-sub {
        color: var(--muted);
        margin-top: 0.2rem;
        margin-bottom: 0;
      }

      [data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 12px;
      }

      .stTabs [data-baseweb="tab-list"] {
        gap: 0.25rem;
      }

      .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid var(--line);
      }

      .stTabs [aria-selected="true"] {
        background: rgba(15, 157, 128, 0.16) !important;
        border-color: rgba(15, 157, 128, 0.45) !important;
      }

      .stButton > button,
      .stDownloadButton > button {
        border: 1px solid rgba(14, 121, 209, 0.35) !important;
        background: linear-gradient(180deg, #f1f8ff 0%, #e5f3ff 100%) !important;
        color: #0d2a44 !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
      }

      .stButton > button:hover,
      .stDownloadButton > button:hover {
        border-color: rgba(14, 121, 209, 0.65) !important;
        background: linear-gradient(180deg, #e8f4ff 0%, #d8ecff 100%) !important;
        color: #06253f !important;
      }

      .stButton > button:focus,
      .stDownloadButton > button:focus {
        box-shadow: 0 0 0 2px rgba(14, 121, 209, 0.2) !important;
      }

      [data-baseweb="select"] > div,
      [data-baseweb="input"] > div,
      .stDateInput > div > div {
        background: rgba(255, 255, 255, 0.88) !important;
        border: 1px solid var(--line) !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_http_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.35,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


@st.cache_data(ttl=90, show_spinner=False)
def api_get_cached(endpoint: str, params_items: tuple[tuple[str, str], ...] = ()):
    response = get_http_session().get(
        f"{API_URL}{endpoint}",
        params=dict(params_items),
        timeout=12,
    )
    response.raise_for_status()
    return response.json()


def api_get(endpoint: str, params: dict | None = None):
    try:
        items = tuple(sorted((params or {}).items()))
        return api_get_cached(endpoint, items)
    except requests.RequestException as exc:
        st.error(f"API error in `{endpoint}`: {exc}")
        return None


def metric_fmt(value: float | None, kind: str = "usd") -> str:
    if value is None:
        return "-"
    if kind == "usd":
        return f"${value:,.2f}"
    if kind == "pct":
        return f"{value:+.2f}%"
    return f"{value:,.2f}"


def pct_change(df: pd.DataFrame, days: int) -> float | None:
    if len(df) <= days:
        return None
    now = float(df.iloc[-1]["price_usd"])
    prev = float(df.iloc[-(days + 1)]["price_usd"])
    if prev == 0:
        return None
    return ((now - prev) / prev) * 100


def normalize_base100(df: pd.DataFrame, value_col: str) -> pd.Series:
    first = df[value_col].iloc[0]
    if first == 0:
        return pd.Series([None] * len(df))
    return (df[value_col] / first) * 100


st.markdown(
    """
    <div class="hero">
      <div class="hero-kicker">CRYPTOLAKE / MARKET TERMINAL</div>
      <p class="hero-title">Crypto Intelligence Dashboard</p>
      <p class="hero-sub">Inspired by crypto market terminals: compact KPI cards, normalized comparisons, and sentiment overlays.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Control panel")
    if st.button("Refresh cached data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    preset = st.selectbox("Quick range", ["30d", "90d", "180d", "365d", "Custom"], index=1)

    today = date.today()
    if preset == "Custom":
        start_default = today - timedelta(days=120)
        start_date, end_date = st.date_input(
            "Date range",
            value=(start_default, today),
            max_value=today,
        )
    else:
        days = int(preset.replace("d", ""))
        start_date = today - timedelta(days=days)
        end_date = today
        st.caption(f"Using range: {start_date.isoformat()} -> {end_date.isoformat()}")

    fg_limit = st.slider("Fear & Greed window", min_value=14, max_value=180, value=60)
    show_ma = st.checkbox("Show moving averages", value=True)


with st.spinner("Checking API status..."):
    health = api_get("/api/v1/health")

if not health or health.get("status") != "healthy":
    st.warning("API is unavailable. Start services and run the pipeline first.")
    st.stop()


with st.spinner("Loading market metadata..."):
    overview = api_get("/api/v1/analytics/market-overview")
    coins = api_get("/api/v1/analytics/coins")

if not coins:
    st.warning("No coin metadata returned from API.")
    st.stop()

coin_ids = [c["coin_id"] for c in coins]
default_single = "bitcoin" if "bitcoin" in coin_ids else coin_ids[0]

with st.sidebar:
    selected_coin = st.selectbox("Focus coin", coin_ids, index=coin_ids.index(default_single))
    default_compare = [c for c in ["bitcoin", "ethereum", "solana"] if c in coin_ids]
    selected_multi = st.multiselect(
        "Compare performance (Base 100)",
        coin_ids,
        default=default_compare or [selected_coin],
    )
    st.caption(
        "Base 100 = todas empiezan en 100 al inicio del rango. "
        "Si termina en 120, subio +20%."
    )

if overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Coins tracked", overview.get("total_coins", 0))
    c2.metric("Fact rows", f"{overview.get('total_fact_rows', 0):,}")
    c3.metric(
        "Fear & Greed",
        overview.get("latest_fear_greed", "-"),
        overview.get("latest_sentiment", ""),
    )
    c4.metric(
        "Date range",
        f"{overview.get('date_range_start', '?')} -> {overview.get('date_range_end', '?')}",
    )

params = {
    "start_date": start_date.isoformat(),
    "end_date": end_date.isoformat(),
    "limit": str(max(30, (end_date - start_date).days + 10)),
}

with st.spinner("Loading focus coin series..."):
    prices = api_get(f"/api/v1/prices/{selected_coin}", params=params)

if not prices:
    st.warning(f"No data for `{selected_coin}` in selected range.")
    st.stop()

df = pd.DataFrame(prices)
df["price_date"] = pd.to_datetime(df["price_date"])
df = df.sort_values("price_date")

last_price = float(df.iloc[-1]["price_usd"]) if not df.empty else None
ret_7d = pct_change(df, 7)
ret_30d = pct_change(df, 30)
vol_30d = float(df["volatility_7d"].tail(30).mean()) if "volatility_7d" in df else None

st.subheader(f"Focus: {selected_coin}")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Last price", metric_fmt(last_price, "usd"))
k2.metric("7d return", metric_fmt(ret_7d, "pct"))
k3.metric("30d return", metric_fmt(ret_30d, "pct"))
k4.metric("Volatility (30d avg)", metric_fmt(vol_30d, "pct"))


tab1, tab2, tab3, tab4 = st.tabs(["Price", "Compare", "Sentiment", "Coin table"])

with tab1:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["price_date"],
            y=df["price_usd"],
            name="Price",
            line=dict(color="#26c485", width=2),
        )
    )
    if show_ma:
        if "moving_avg_7d" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["price_date"],
                    y=df["moving_avg_7d"],
                    name="MA 7d",
                    line=dict(color="#22a1f0", dash="dash"),
                )
            )
        if "moving_avg_30d" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["price_date"],
                    y=df["moving_avg_30d"],
                    name="MA 30d",
                    line=dict(color="#f6c95a", dash="dot"),
                )
            )

    fig.update_layout(
        title=f"{selected_coin.title()} price trend",
        xaxis_title="Date",
        yaxis_title="USD",
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=470,
        legend=dict(orientation="h", y=1.05, x=0),
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.caption(
        "Comparativa relativa: elimina sesgo de precio nominal y muestra "
        "quien rindio mejor en el periodo."
    )
    compare_frames = []
    for coin in selected_multi or [selected_coin]:
        series = api_get(f"/api/v1/prices/{coin}", params=params)
        if not series:
            continue
        s_df = pd.DataFrame(series)
        s_df["price_date"] = pd.to_datetime(s_df["price_date"])
        s_df = s_df.sort_values("price_date")
        s_df["base_100"] = normalize_base100(s_df, "price_usd")
        s_df["coin_id"] = coin
        compare_frames.append(s_df[["price_date", "coin_id", "base_100"]])

    if compare_frames:
        comp_df = pd.concat(compare_frames, ignore_index=True)
        perf = (
            comp_df.sort_values("price_date")
            .groupby("coin_id", as_index=False)
            .agg(start=("base_100", "first"), end=("base_100", "last"))
        )
        perf["return_pct"] = perf["end"] - perf["start"]

        top_row = perf.sort_values("return_pct", ascending=False).iloc[0]
        low_row = perf.sort_values("return_pct", ascending=True).iloc[0]
        avg_ret = perf["return_pct"].mean()

        st.info(
            f"Top: {top_row['coin_id']} ({top_row['return_pct']:+.2f}%). "
            f"Peor: {low_row['coin_id']} ({low_row['return_pct']:+.2f}%). "
            f"Media del grupo: {avg_ret:+.2f}%."
        )

        fig_comp = px.line(
            comp_df,
            x="price_date",
            y="base_100",
            color="coin_id",
            title="Normalized performance (base = 100 at range start)",
        )
        fig_comp.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Date",
            yaxis_title="Performance index",
            height=470,
            legend_title_text="",
        )
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("No comparison data available for selected coins.")

with tab3:
    fg = api_get("/api/v1/analytics/fear-greed", params={"limit": str(fg_limit)})
    if fg:
        fg_df = pd.DataFrame(fg)
        fg_df["index_date"] = pd.to_datetime(fg_df["index_date"])
        fg_df = fg_df.sort_values("index_date")
        color_map = {
            "Extreme Fear": "#ff5f7a",
            "Fear": "#ff9966",
            "Neutral": "#f6c95a",
            "Greed": "#57d18f",
            "Extreme Greed": "#26c485",
        }
        fig_fg = px.bar(
            fg_df,
            x="index_date",
            y="fear_greed_value",
            color="classification",
            color_discrete_map=color_map,
            title=f"Fear & Greed Index ({fg_limit} days)",
        )
        fig_fg.add_hline(y=50, line_dash="dash", line_color="#8aa0b4")
        fig_fg.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Date",
            yaxis_title="Index",
            height=430,
            legend_title_text="",
        )
        st.plotly_chart(fig_fg, use_container_width=True)
    else:
        st.info("No sentiment data available.")

with tab4:
    coins_df = pd.DataFrame(coins)
    st.dataframe(coins_df, use_container_width=True, hide_index=True)
    st.download_button(
        label="Download coin stats CSV",
        data=coins_df.to_csv(index=False).encode("utf-8"),
        file_name="cryptolake_coin_stats.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.caption(
    f"Source: {API_URL} | Last refresh: {pd.Timestamp.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
)
