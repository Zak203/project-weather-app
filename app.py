"""
Smart Weather Monitoring Dashboard — Geneva
==========================================
Production-ready Streamlit app connected to Google BigQuery.
Tables:
  - indoor_readings  (timestamp, room, indoor_temp, indoor_humidity, tvoc, eco2, motion_detected)
  - weather_readings (timestamp, location, outdoor_temp, weather_main, weather_desc,
                      forecast_day_1, forecast_day_2, forecast_day_3)

Run:
    streamlit run app.py

Requirements:
    pip install -r requirements.txt
"""

# ── Imports ───────────────────────────────────────────────────────────────────
import os
import time
import datetime
import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smart Weather Monitoring – Geneva",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Root / background ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
.stApp {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    color: #e8eaf6;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.05);
    border-right: 1px solid rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
}
section[data-testid="stSidebar"] * { color: #e8eaf6 !important; }

/* ── Metric cards ── */
div[data-testid="metric-container"] {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 20px 24px;
    backdrop-filter: blur(6px);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
div[data-testid="metric-container"]:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
div[data-testid="metric-container"] label { color: #a0a8d0 !important; font-size: 0.82rem !important; }
div[data-testid="metric-container"] [data-testid="metric-value"] { color: #ffffff !important; font-size: 2rem !important; font-weight: 700; }
div[data-testid="metric-container"] [data-testid="metric-delta"] { font-size: 0.8rem !important; }

/* ── Section headers ── */
.section-header {
    font-size: 1.15rem;
    font-weight: 600;
    color: #a0a8d0;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin: 28px 0 12px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

/* ── Alert boxes ── */
.alert-green  { background:rgba(72,199,116,0.15); border:1px solid #48c774; border-radius:12px; padding:14px 18px; color:#48c774; margin:6px 0; }
.alert-orange { background:rgba(255,181,71,0.15);  border:1px solid #ffb547; border-radius:12px; padding:14px 18px; color:#ffb547; margin:6px 0; }
.alert-red    { background:rgba(255,83,83,0.15);   border:1px solid #ff5353; border-radius:12px; padding:14px 18px; color:#ff5353; margin:6px 0; }

/* ── Forecast cards ── */
.forecast-card {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 22px 16px;
    text-align: center;
    backdrop-filter: blur(6px);
    transition: transform 0.2s;
}
.forecast-card:hover { transform: translateY(-4px); }
.forecast-card .fc-day   { font-size: 0.78rem; color:#a0a8d0; text-transform:uppercase; letter-spacing:.08em; margin-bottom:6px; }
.forecast-card .fc-icon  { font-size: 2.2rem; margin: 8px 0; }
.forecast-card .fc-desc  { font-size: 0.9rem; color:#c8ceee; font-weight:500; }
.forecast-card .fc-temp  { font-size: 1.1rem; font-weight:700; color:#fff; margin-top:8px; }

/* ── Status pill ── */
.status-pill {
    display:inline-block;
    background:rgba(72,199,116,0.2);
    border:1px solid #48c774;
    border-radius:20px;
    padding:4px 14px;
    font-size:0.78rem;
    color:#48c774;
    font-weight:600;
    letter-spacing:.05em;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%,100% { opacity:1; }
    50% { opacity:.6; }
}

/* ── Chart containers ── */
.element-container { border-radius:12px; }

/* ── Divider ── */
hr { border-color: rgba(255,255,255,0.08) !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# BIGQUERY CLIENT
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_bq_client() -> bigquery.Client:
    """
    Returns a BigQuery client.

    Priority:
    1. Streamlit secrets: [gcp_service_account] block in secrets.toml
    2. GOOGLE_APPLICATION_CREDENTIALS env variable
    3. Application Default Credentials (gcloud auth application-default login)
    """
    if "gcp_service_account" in st.secrets:
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return bigquery.Client(
            credentials=creds,
            project=st.secrets["gcp_service_account"]["project_id"],
        )
    # Fallback: ADC / env variable
    return bigquery.Client()


def get_project_dataset() -> tuple[str, str]:
    """Return (project_id, dataset_id) from secrets or environment."""
    if "gcp_service_account" in st.secrets:
        project = st.secrets["gcp_service_account"]["project_id"]
    else:
        project = os.getenv("GCP_PROJECT_ID", "your-project-id")

    dataset = st.secrets.get("bq_dataset", os.getenv("BQ_DATASET", "weather_iot"))
    return project, dataset


# ─────────────────────────────────────────────────────────────────────────────
# DATA FETCHING  (cached)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def fetch_indoor(room: str, hours: int) -> pd.DataFrame:
    """Fetch indoor readings for a given room and time window."""
    client = get_bq_client()
    project, dataset = get_project_dataset()

    room_filter = "" if room == "All Rooms" else f"AND room = @room"
    query = f"""
        SELECT
            t.event_time,
            t.room,
            t.indoor_temp,
            t.indoor_humidity,
            t.tvoc,
            t.eco2,
            t.motion_detected
        FROM `{project}.{dataset}.indoor_readings` AS t
        WHERE t.event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {int(hours)} HOUR)
            {room_filter}
        ORDER BY t.event_time ASC
        LIMIT 2000
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("room", "STRING", room)]
        if room != "All Rooms"
        else []
    )
    df = client.query(query, job_config=job_config).to_dataframe()
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["event_time"])
    return df


@st.cache_data(ttl=60)
def fetch_weather(hours: int) -> pd.DataFrame:
    """Fetch outdoor weather readings for the given time window."""
    client = get_bq_client()
    project, dataset = get_project_dataset()

    query = f"""
        SELECT
            t.event_time,
            t.location,
            t.outdoor_temp,
            t.weather_main,
            t.weather_desc,
            t.forecast_day_1,
            t.forecast_day_2,
            t.forecast_day_3
        FROM `{project}.{dataset}.weather_readings` AS t
        WHERE t.event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {int(hours)} HOUR)
        ORDER BY t.event_time ASC
        LIMIT 1000
    """
    df = client.query(query).to_dataframe()
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["event_time"])
    return df


@st.cache_data(ttl=300)
def fetch_rooms() -> list[str]:
    """Fetch distinct room names for the dropdown."""
    client = get_bq_client()
    project, dataset = get_project_dataset()
    query = f"SELECT DISTINCT room FROM `{project}.{dataset}.indoor_readings` ORDER BY room"

    df = client.query(query).to_dataframe()
    return df["room"].tolist()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

WEATHER_ICONS = {
    "clear": "☀️", "sun": "☀️",
    "cloud": "☁️", "overcast": "☁️",
    "rain": "🌧️", "drizzle": "🌦️",
    "thunderstorm": "⛈️", "storm": "⛈️",
    "snow": "❄️", "mist": "🌫️", "fog": "🌫️",
    "haze": "🌁", "wind": "💨",
}

def weather_icon(description: str) -> str:
    desc = str(description).lower()
    for keyword, icon in WEATHER_ICONS.items():
        if keyword in desc:
            return icon
    return "🌡️"


def parse_forecast(raw: str) -> dict:
    """
    Parse a forecast string like: '2026-03-23: Clouds, 8.2°C / 3.1°C'
    Returns dict with keys: date, description, temp_max, temp_min
    """
    result = {"date": raw, "description": "", "temp_max": "", "temp_min": ""}
    try:
        parts = raw.split(":", 1)
        result["date"] = parts[0].strip()
        rest = parts[1].strip() if len(parts) > 1 else raw
        # split description from temps: 'Clouds, 8.2°C / 3.1°C'
        if "," in rest:
            desc_part, temp_part = rest.rsplit(",", 1)
            result["description"] = desc_part.strip()
            temp_part = temp_part.strip()
            if "/" in temp_part:
                t_max, t_min = temp_part.split("/")
                result["temp_max"] = t_max.strip().replace("°C", "")
                result["temp_min"] = t_min.strip().replace("°C", "")
        else:
            result["description"] = rest
    except Exception:
        pass
    return result


def section(title: str):
    st.markdown(f'<div class="section-header">📊 {title}</div>', unsafe_allow_html=True)


def latest(df: pd.DataFrame, col: str, default=None):
    """Return the most recent non-null value from a column."""
    s = df[col].dropna()
    return s.iloc[-1] if not s.empty else default


# ─────────────────────────────────────────────────────────────────────────────
# CHART THEME
# ─────────────────────────────────────────────────────────────────────────────

CHART_CONFIG = {
    "displayModeBar": False,
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#a0a8d0", size=12),
    xaxis=dict(
        gridcolor="rgba(255,255,255,0.06)",
        linecolor="rgba(255,255,255,0.1)",
        tickfont=dict(size=11),
    ),
    yaxis=dict(
        gridcolor="rgba(255,255,255,0.06)",
        linecolor="rgba(255,255,255,0.1)",
        tickfont=dict(size=11),
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor="rgba(255,255,255,0.1)",
        borderwidth=1,
        font=dict(color="#c8ceee"),
    ),
    margin=dict(l=10, r=10, t=30, b=10),
    hovermode="x unified",
)


def make_line_chart(df: pd.DataFrame, x_col: str, y_cols: list[dict], title: str = ""):
    """
    Build a Plotly line chart with the dark glass theme.
    y_cols: list of dicts with keys: col, name, color
    """
    import plotly.graph_objects as go

    fig = go.Figure()
    for y in y_cols:
        fig.add_trace(go.Scatter(
            x=df[x_col],
            y=df[y["col"]],
            name=y["name"],
            mode="lines",
            line=dict(color=y["color"], width=2.5, shape="spline", smoothing=0.8),
            fill="tozeroy",
            fillcolor=y["color"].replace("rgb", "rgba").replace(")", ",0.08)"),
        ))
    layout = dict(**PLOTLY_LAYOUT)
    layout["title"] = dict(text=title, font=dict(size=14, color="#c8ceee"), x=0)
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # ── Auto-refresh ──────────────────────────────────────────────────────────
    REFRESH_INTERVAL = 60  # seconds

    # ── Sidebar: Filters ──────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## ⚙️ Filters")
        st.markdown("---")

        # Room selector
        try:
            rooms = ["All Rooms"] + fetch_rooms()
        except Exception:
            rooms = ["All Rooms"]
        selected_room = st.selectbox("🏠 Room", rooms, index=0)

        # Time range
        time_options = {"Last 1 hour": 1, "Last 6 hours": 6, "Last 24 hours": 24}
        selected_range = st.selectbox("🕐 Time range", list(time_options.keys()), index=1)
        hours = time_options[selected_range]

        st.markdown("---")
        st.markdown("### 🔄 Auto-refresh")
        st.markdown(f"<span class='status-pill'>● LIVE — {REFRESH_INTERVAL}s</span>", unsafe_allow_html=True)
        st.caption(f"Data updates every {REFRESH_INTERVAL} seconds.")

        st.markdown("---")
        if st.button("🔃 Refresh now"):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.caption("Smart Weather Monitoring v1.0\nBuilt with Streamlit + BigQuery")

    # ── Header ────────────────────────────────────────────────────────────────
    col_title, col_time = st.columns([3, 1])
    with col_title:
        st.markdown(
            "# 🌤️ Smart Weather Monitoring\n"
            "<span style='color:#a0a8d0;font-size:1rem;'>📍 Geneva, Switzerland</span>",
            unsafe_allow_html=True,
        )
    with col_time:
        now = datetime.datetime.now()
        st.markdown(
            f"<div style='text-align:right;padding-top:14px;'>"
            f"<div style='font-size:1.6rem;font-weight:700;color:#fff;'>{now.strftime('%H:%M:%S')}</div>"
            f"<div style='color:#a0a8d0;font-size:0.82rem;'>{now.strftime('%A, %d %B %Y')}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("---")

    # ── Fetch data ────────────────────────────────────────────────────────────
    indoor_df = pd.DataFrame()
    weather_df = pd.DataFrame()
    data_error = False

    try:
        with st.spinner("Fetching data from BigQuery…"):
            indoor_df = fetch_indoor(selected_room, hours)
            weather_df = fetch_weather(hours)
    except Exception as e:
        data_error = True
        st.error(
            f"⚠️ **BigQuery connection failed.** Make sure your credentials are configured.\n\n"
            f"```\n{e}\n```\n\n"
            "**Setup options:**\n"
            "1. Add a `[gcp_service_account]` block to `.streamlit/secrets.toml`\n"
            "2. Set `GOOGLE_APPLICATION_CREDENTIALS` env variable\n"
            "3. Run `gcloud auth application-default login`"
        )

    if data_error:
        st.info("👆 Configure your BigQuery credentials to load live data.")
        return

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    section("Key Performance Indicators")
    k1, k2, k3, k4, k5 = st.columns(5)

    def kpi_delta(df, col, fmt=".1f"):
        """Compute delta between latest and N records ago."""
        s = df[col].dropna()
        if len(s) >= 2:
            delta = s.iloc[-1] - s.iloc[-min(len(s), 10)]
            return round(delta, 2)
        return None

    with k1:
        val = latest(indoor_df, "indoor_temp")
        delta = kpi_delta(indoor_df, "indoor_temp") if not indoor_df.empty else None
        st.metric("🌡️ Indoor Temp", f"{val:.1f} °C" if val is not None else "—", delta=f"{delta:+.1f} °C" if delta else None)

    with k2:
        val = latest(indoor_df, "indoor_humidity")
        delta = kpi_delta(indoor_df, "indoor_humidity") if not indoor_df.empty else None
        st.metric("💧 Humidity", f"{val:.1f} %" if val is not None else "—", delta=f"{delta:+.1f} %" if delta else None)

    with k3:
        val = latest(indoor_df, "eco2")
        delta = kpi_delta(indoor_df, "eco2") if not indoor_df.empty else None
        st.metric("🫁 eCO₂", f"{int(val)} ppm" if val is not None else "—", delta=f"{int(delta):+d} ppm" if delta else None)

    with k4:
        val = latest(indoor_df, "tvoc")
        delta = kpi_delta(indoor_df, "tvoc") if not indoor_df.empty else None
        st.metric("🧪 TVOC", f"{int(val)} ppb" if val is not None else "—", delta=f"{int(delta):+d} ppb" if delta else None)

    with k5:
        val = latest(weather_df, "outdoor_temp")
        delta = kpi_delta(weather_df, "outdoor_temp") if not weather_df.empty else None
        st.metric("🌡️ Outdoor Temp", f"{val:.1f} °C" if val is not None else "—", delta=f"{delta:+.1f} °C" if delta else None)

    st.markdown("---")

    # ── Alerts ────────────────────────────────────────────────────────────────
    section("Alerts")

    alerts_triggered = False
    a1, a2, a3 = st.columns(3)

    eco2_val  = latest(indoor_df, "eco2")  if not indoor_df.empty else None
    tvoc_val  = latest(indoor_df, "tvoc")  if not indoor_df.empty else None
    hum_val   = latest(indoor_df, "indoor_humidity") if not indoor_df.empty else None

    with a1:
        if eco2_val is None:
            st.markdown('<div class="alert-orange">⚠️ <b>eCO₂</b> — No data</div>', unsafe_allow_html=True)
            alerts_triggered = True
        elif eco2_val > 1200:
            st.markdown(f'<div class="alert-red">🚨 <b>eCO₂ HIGH:</b> {int(eco2_val)} ppm (limit 1200)</div>', unsafe_allow_html=True)
            alerts_triggered = True
        else:
            st.markdown(f'<div class="alert-green">✅ <b>eCO₂ OK:</b> {int(eco2_val)} ppm</div>', unsafe_allow_html=True)

    with a2:
        if tvoc_val is None:
            st.markdown('<div class="alert-orange">⚠️ <b>TVOC</b> — No data</div>', unsafe_allow_html=True)
            alerts_triggered = True
        elif tvoc_val > 400:
            st.markdown(f'<div class="alert-red">🚨 <b>TVOC HIGH:</b> {int(tvoc_val)} ppb (limit 400)</div>', unsafe_allow_html=True)
            alerts_triggered = True
        else:
            st.markdown(f'<div class="alert-green">✅ <b>TVOC OK:</b> {int(tvoc_val)} ppb</div>', unsafe_allow_html=True)

    with a3:
        if hum_val is None:
            st.markdown('<div class="alert-orange">⚠️ <b>Humidity</b> — No data</div>', unsafe_allow_html=True)
            alerts_triggered = True
        elif hum_val < 40:
            st.markdown(f'<div class="alert-orange">⚠️ <b>Humidity LOW:</b> {hum_val:.1f}% (min 40%)</div>', unsafe_allow_html=True)
            alerts_triggered = True
        else:
            st.markdown(f'<div class="alert-green">✅ <b>Humidity OK:</b> {hum_val:.1f}%</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Indoor Charts ─────────────────────────────────────────────────────────
    section("Indoor Readings")

    if indoor_df.empty:
        st.info("No indoor data available for the selected filters.")
    else:
        import plotly.graph_objects as go

        col_left, col_right = st.columns(2)
        with col_left:
            fig_temp = make_line_chart(
                indoor_df, "timestamp",
                [{"col": "indoor_temp", "name": "Indoor Temp (°C)", "color": "rgb(255,183,77)"}],
                "🌡️ Indoor Temperature",
            )
            st.plotly_chart(fig_temp, use_container_width=True, config=CHART_CONFIG)

        with col_right:
            fig_hum = make_line_chart(
                indoor_df, "timestamp",
                [{"col": "indoor_humidity", "name": "Humidity (%)", "color": "rgb(100,181,246)"}],
                "💧 Indoor Humidity",
            )
            st.plotly_chart(fig_hum, use_container_width=True, config=CHART_CONFIG)

        # CO2 / TVOC combined chart
        fig_air = go.Figure()
        fig_air.add_trace(go.Scatter(
            x=indoor_df["timestamp"], y=indoor_df["eco2"],
            name="eCO₂ (ppm)", mode="lines",
            line=dict(color="rgb(102,187,106)", width=2.5, shape="spline"),
            fill="tozeroy", fillcolor="rgba(102,187,106,0.08)",
            yaxis="y1",
        ))
        fig_air.add_trace(go.Scatter(
            x=indoor_df["timestamp"], y=indoor_df["tvoc"],
            name="TVOC (ppb)", mode="lines",
            line=dict(color="rgb(239,83,80)", width=2.5, shape="spline"),
            fill="tozeroy", fillcolor="rgba(239,83,80,0.08)",
            yaxis="y2",
        ))
        # Threshold lines
        fig_air.add_hline(y=1200, line_dash="dot", line_color="rgba(239,83,80,0.5)", annotation_text="CO₂ limit", yref="y")
        layout_air = dict(**PLOTLY_LAYOUT)
        layout_air["title"] = dict(text="🫧 Air Quality — eCO₂ & TVOC", font=dict(size=14, color="#c8ceee"), x=0)
        layout_air["yaxis2"] = dict(
            overlaying="y", side="right",
            gridcolor="rgba(0,0,0,0)",
            tickfont=dict(size=11, color="#a0a8d0"),
        )
        fig_air.update_layout(**layout_air)
        st.plotly_chart(fig_air, use_container_width=True, config=CHART_CONFIG)

        # Motion indicator
        if "motion_detected" in indoor_df.columns:
            motion_count = indoor_df["motion_detected"].sum()
            total = len(indoor_df)
            st.markdown(
                f"<div style='font-size:0.85rem;color:#a0a8d0;margin-top:-8px;'>"
                f"🚶 Motion detected in <b style='color:#fff'>{int(motion_count)}</b> of {total} readings"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Outdoor Charts ────────────────────────────────────────────────────────
    section("Outdoor Conditions")

    if weather_df.empty:
        st.info("No outdoor weather data available for the selected time range.")
    else:
        col_otemp, col_odesc = st.columns([2, 1])
        with col_otemp:
            fig_out = make_line_chart(
                weather_df, "timestamp",
                [{"col": "outdoor_temp", "name": "Outdoor Temp (°C)", "color": "rgb(129,212,250)"}],
                "🌡️ Outdoor Temperature",
            )
            st.plotly_chart(fig_out, use_container_width=True, config=CHART_CONFIG)

        with col_odesc:
            st.markdown(
                "<div style='color:#a0a8d0;font-size:0.82rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px;'>Weather Conditions</div>",
                unsafe_allow_html=True,
            )
            if not weather_df.empty:
                latest_weather = weather_df.iloc[-1]
                icon = weather_icon(str(latest_weather.get("weather_desc", "")))
                st.markdown(
                    f"<div style='text-align:center;padding:20px 0;'>"
                    f"<div style='font-size:4rem;'>{icon}</div>"
                    f"<div style='font-size:1.4rem;font-weight:700;color:#fff;margin:8px 0;'>"
                    f"{latest_weather.get('weather_main','—')}</div>"
                    f"<div style='color:#a0a8d0;font-size:0.9rem;'>{latest_weather.get('weather_desc','')}</div>"
                    f"<div style='font-size:1.8rem;font-weight:700;color:#fff;margin-top:16px;'>"
                    f"{latest_weather.get('outdoor_temp','—'):.1f} °C</div>"
                    f"<div style='color:#a0a8d0;font-size:0.78rem;margin-top:4px;'>"
                    f"📍 {latest_weather.get('location','Geneva')}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                # Weather description counts
                desc_counts = weather_df["weather_desc"].value_counts().head(5)
                desc_df = desc_counts.reset_index()
                desc_df.columns = ["Condition", "Count"]
                st.dataframe(
                    desc_df,
                    hide_index=True,
                    use_container_width=True,
                    column_config={"Count": st.column_config.ProgressColumn("Frequency", min_value=0, max_value=int(desc_counts.max()))},
                )

    st.markdown("---")

    # ── Indoor vs Outdoor Comparison ─────────────────────────────────────────
    section("Indoor vs Outdoor Comparison")

    if indoor_df.empty or weather_df.empty:
        st.info("Both indoor and outdoor data are needed for comparison.")
    else:
        import plotly.graph_objects as go

        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Scatter(
            x=indoor_df["timestamp"], y=indoor_df["indoor_temp"],
            name="Indoor", mode="lines",
            line=dict(color="rgb(255,183,77)", width=2.5, shape="spline"),
            fill="tozeroy", fillcolor="rgba(255,183,77,0.08)",
        ))
        fig_cmp.add_trace(go.Scatter(
            x=weather_df["timestamp"], y=weather_df["outdoor_temp"],
            name="Outdoor", mode="lines",
            line=dict(color="rgb(129,212,250)", width=2.5, shape="spline"),
            fill="tozeroy", fillcolor="rgba(129,212,250,0.08)",
        ))
        layout_cmp = dict(**PLOTLY_LAYOUT)
        layout_cmp["title"] = dict(text="🔄 Indoor vs Outdoor Temperature (°C)", font=dict(size=14, color="#c8ceee"), x=0)
        fig_cmp.update_layout(**layout_cmp)
        st.plotly_chart(fig_cmp, use_container_width=True, config=CHART_CONFIG)

        # Delta KPI
        in_t = latest(indoor_df, "indoor_temp")
        out_t = latest(weather_df, "outdoor_temp")
        if in_t is not None and out_t is not None:
            delta_t = in_t - out_t
            color = "#ff5353" if abs(delta_t) > 10 else "#48c774"
            st.markdown(
                f"<div style='text-align:center;margin-top:-10px;color:{color};font-size:0.9rem;font-weight:600;'>"
                f"Δ Temperature: {delta_t:+.1f} °C (indoor vs outdoor)"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Forecast ──────────────────────────────────────────────────────────────
    section("3-Day Forecast")

    if weather_df.empty or not any(c in weather_df.columns for c in ["forecast_day_1", "forecast_day_2", "forecast_day_3"]):
        st.info("No forecast data available.")
    else:
        latest_row = weather_df.tail(1).iloc[0]
        forecasts = [
            latest_row.get("forecast_day_1", ""),
            latest_row.get("forecast_day_2", ""),
            latest_row.get("forecast_day_3", ""),
        ]

        fc_cols = st.columns(3)
        for i, (col, raw) in enumerate(zip(fc_cols, forecasts)):
            parsed = parse_forecast(str(raw))
            icon = weather_icon(parsed["description"])
            day_label = f"Day +{i+1}"
            try:
                day_label = datetime.datetime.strptime(parsed["date"], "%Y-%m-%d").strftime("%A")
            except Exception:
                pass

            with col:
                temp_str = ""
                if parsed["temp_max"] and parsed["temp_min"]:
                    temp_str = f"<div class='fc-temp'>⬆ {parsed['temp_max']}°C &nbsp; ⬇ {parsed['temp_min']}°C</div>"

                st.markdown(
                    f"<div class='forecast-card'>"
                    f"<div class='fc-day'>{day_label}</div>"
                    f"<div class='fc-icon'>{icon}</div>"
                    f"<div class='fc-desc'>{parsed['description'] or raw[:40]}</div>"
                    f"{temp_str}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    # ── Raw data expanders ────────────────────────────────────────────────────
    with st.expander("📋 Raw Indoor Data"):
        if indoor_df.empty:
            st.info("No data.")
        else:
            st.dataframe(
                indoor_df.sort_values("timestamp", ascending=False),
                use_container_width=True,
                hide_index=True,
            )

    with st.expander("📋 Raw Weather Data"):
        if weather_df.empty:
            st.info("No data.")
        else:
            st.dataframe(
                weather_df.sort_values("timestamp", ascending=False),
                use_container_width=True,
                hide_index=True,
            )

    # ── Auto-refresh ──────────────────────────────────────────────────────────
    time.sleep(REFRESH_INTERVAL)
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
