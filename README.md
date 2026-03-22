# 🌤️ Smart Weather Monitoring Dashboard — Geneva

A **production-ready Streamlit dashboard** visualizing IoT sensor data from M5Stack devices, stored in Google BigQuery.

## Features

| Section | Details |
|---|---|
| **Header** | Live clock, auto-refresh indicator |
| **Filters** | Room selector, time-range picker (1h / 6h / 24h) |
| **KPI Cards** | Indoor temp, humidity, eCO₂, TVOC, outdoor temp |
| **Alerts** | Color-coded (green/orange/red) for CO₂, TVOC, humidity |
| **Indoor Charts** | Temperature, humidity, air-quality (eCO₂ + TVOC) |
| **Outdoor Charts** | Temperature timeline, weather condition summary |
| **Comparison** | Indoor vs outdoor temperature overlay |
| **Forecast** | 3-day card display |
| **Raw Data** | Collapsible tables for both datasets |

## Quick Start

```bash
# 1. Clone & enter the project
cd Cloud_Project_Apple

# 2. Create a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure BigQuery credentials (choose one option below)
# Option A — Streamlit secrets (recommended)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# then fill in your service account details

# Option B — Application Default Credentials
gcloud auth application-default login

# 5. Run the dashboard
streamlit run app.py
```

## BigQuery Schema

### `indoor_readings`
| Column | Type | Description |
|---|---|---|
| `timestamp` | TIMESTAMP | Reading time |
| `room` | STRING | Room name |
| `indoor_temp` | FLOAT | Temperature °C |
| `indoor_humidity` | FLOAT | Relative humidity % |
| `tvoc` | INTEGER | TVOC ppb |
| `eco2` | INTEGER | eCO₂ ppm |
| `motion_detected` | BOOLEAN | PIR sensor |

### `weather_readings`
| Column | Type | Description |
|---|---|---|
| `timestamp` | TIMESTAMP | Reading time |
| `location` | STRING | City name |
| `outdoor_temp` | FLOAT | Temperature °C |
| `weather_main` | STRING | Main condition |
| `weather_desc` | STRING | Detailed description |
| `forecast_day_1/2/3` | STRING | 3-day forecast strings |

## Alert Thresholds

| Metric | Threshold | Severity |
|---|---|---|
| eCO₂ | > 1200 ppm | 🔴 Red |
| TVOC | > 400 ppb | 🔴 Red |
| Humidity | < 40 % | 🟠 Orange |

## Configuration

Edit `.streamlit/secrets.toml` with your GCP details:

```toml
bq_dataset = "weather_iot"

[gcp_service_account]
project_id   = "your-project-id"
# ... (see secrets.toml.example for full template)
```

## Tech Stack

- **[Streamlit](https://streamlit.io)** — Dashboard framework
- **[Google BigQuery](https://cloud.google.com/bigquery)** — Data warehouse
- **[Plotly](https://plotly.com)** — Interactive charts
- **[Pandas](https://pandas.pydata.org)** — Data wrangling