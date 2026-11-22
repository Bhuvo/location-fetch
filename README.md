# 🌐 IPTrace – Advanced IP Geolocation & Visitor Analytics

[![Live Demo](https://img.shields.io/badge/Live%20Demo-location--fetch--3fcp.vercel.app-black.svg?logo=vercel&logoColor=white)](https://location-fetch-3fcp.vercel.app)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.15-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Framework](https://img.shields.io/badge/Framework-Flask%203.x-lightgrey.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Database-SQLite%20%2F%20SQLAlchemy-green.svg?logo=sqlite&logoColor=white)](https://sqlite.org)
[![Mapping](https://img.shields.io/badge/Mapping-Leaflet.js%20%2B%20OpenStreetMap-brightgreen.svg?logo=leaflet&logoColor=white)](https://leafletjs.com)
[![Charts](https://img.shields.io/badge/Charts-Chart.js%204.x-orange.svg?logo=chartdotjs&logoColor=white)](https://chartjs.org)
[![Tests](https://img.shields.io/badge/Tests-40%20Passed%20(100%25)-success.svg?logo=pytest&logoColor=white)](tests/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

> 🚀 **Live Production Deployment**: **[https://location-fetch-3fcp.vercel.app](https://location-fetch-3fcp.vercel.app)**
>
> **Default Admin Credentials**:
> - **Login Portal**: [https://location-fetch-3fcp.vercel.app/admin/login](https://location-fetch-3fcp.vercel.app/admin/login)
> - **Username**: `admin`
> - **Password**: `AdminSecurePass123!`

**IPTrace** is a full-stack, enterprise-grade IP Geolocation & Visitor Analytics web application built with Python, Flask, SQLite, and vanilla frontend technologies (HTML5, CSS3, ES6 JavaScript, Bootstrap 5, Chart.js, and Leaflet.js).

It empowers administrators to generate unique tracking links, capture public IP addresses upon URL visit, resolve granular geographical metadata across multiple geolocation providers concurrently, detect generic city-centre fallbacks, and visualize visitor distributions on interactive global maps and analytics dashboards.

---

## 📑 Table of Contents

- [Live Deployment](#-live-deployment)
- [Key Features](#-key-features)
- [Why IP Geolocation Returns City Centroids (e.g. Chennai 13.0878, 80.2785)](#-why-ip-geolocation-returns-city-centroids)
- [Tech Stack](#-tech-stack)
- [Application Architecture](#-application-architecture)
- [Quick Start Guide](#-quick-start-guide)
  - [Prerequisites](#prerequisites)
  - [Installation on Windows](#installation-on-windows)
  - [Installation on Linux / macOS](#installation-on-linux--macos)
- [Deploying to Vercel](#-deploying-to-vercel)
- [Configuration (.env)](#-configuration-env)
- [Multi-Provider Geolocation & Diagnostic Mode](#-multi-provider-geolocation--diagnostic-mode)
- [Network Testing Environments](#-network-testing-environments)
- [Automated Testing Suite](#-automated-testing-suite)
- [REST API Reference](#-rest-api-reference)
- [Security & Privacy Architecture](#-security--privacy-architecture)
- [License & Ethical Disclaimer](#-license--ethical-disclaimer)

---

## 🚀 Live Deployment

The application is deployed and hosted on **Vercel Serverless Functions**:

- **Production URL**: [https://location-fetch-3fcp.vercel.app](https://location-fetch-3fcp.vercel.app)
- **Admin Login**: [https://location-fetch-3fcp.vercel.app/admin/login](https://location-fetch-3fcp.vercel.app/admin/login)
- **GitHub Repository**: [https://github.com/Bhuvo/location-fetch](https://github.com/Bhuvo/location-fetch)

---

## 🚀 Key Features

### 📍 Multi-Provider Geolocation Engine
- **Parallel Querying**: Simultaneously queries **IPinfo**, **ip-api.com**, and **MaxMind GeoIP2 / ipapi.co** using thread pools for sub-300ms response times.
- **Strict Rule — Never Average Coordinates**: Preserves distinct coordinate outputs per provider. Averaging coordinates creates artificial midpoints in bodies of water or empty fields; IPTrace keeps provider data authentic.
- **Accuracy Radius Capture**: Records uncertainty radius (in km) when supplied by providers.

### 🎯 City-Centre Centroid Detection & Confidence Scoring
- **Automated Centroid Recognition**: Identifies coordinates matching canonical municipal reference centroids (e.g. Chennai `13.0878, 80.2785`, London `51.5074, -0.1278`, New York `40.7128, -74.0060`, Bangalore `12.9716, 77.5946`).
- **Subnet Reuse Detection**: Scans the SQLite database for identical coordinates shared across different visitor IPs.
- **Confidence Rating Engine**: Computes an automated confidence tier:
  - 🟢 **`HIGH`**: Strong multi-provider consensus, matching postal code, radius ≤ 25 km.
  - 🟡 **`MEDIUM`**: General regional agreement, postal code missing or radius 25–100 km.
  - 🔴 **`LOW`**: Generic city-centre centroid detected or significant provider disagreement.
  - ⚪ **`UNKNOWN`**: Provider failure, private IP, or missing coordinates.

### 📊 Modern SaaS Analytics Dashboard
- **Live KPIs**: Total Links, Total Visits, Unique IPs, Countries Detected, Cities Detected.
- **Interactive Chart.js Visualizations**:
  - 14-day visit trends line chart.
  - Top country distribution doughnut chart.
  - Browser engine breakdown.
  - Operating system distribution.
- **Leaflet.js Global Map**: Color-coded markers, popups with ISP metadata, coordinate inspection, and filter-by-link functionality.
- **Provider Diagnostics Page**: Side-by-side comparison table and multi-pin variance map allowing admins to test any IP live.
- **Visitor Records Management**: Full search by city/country, date range filtering, pagination, detailed JSON breakdown, and CSV export.

---

## 🔍 Why IP Geolocation Returns City Centroids

If you observe identical coordinates such as **Latitude 13.0878, Longitude 80.2785** returned for multiple visitors across Tamil Nadu, India:

1. **No Device GPS Access**: IP geolocation databases map IP blocks allocated to ISPs by regional registries (e.g. APNIC). They do not access device hardware GPS, mobile cell towers, or local Wi-Fi hotspots.
2. **Municipal Centroids**: When an ISP announces an entire IP range for an urban area, geolocation databases fall back to the **canonical city-centre reference point** (e.g. municipal headquarters or main telecom exchange).
3. **Subnet Sharing**: Thousands of mobile and broadband users connected to towers or DSLAMs miles apart in different districts will share the same gateway subnet and receive the exact same city-centre coordinates.

> **Mandatory Disclaimer**: *"IP-based location is an estimate and does not represent the exact physical location of the visitor."*

---

## 💻 Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.11+ / 3.15, Flask 3.1, Flask-SQLAlchemy 3.1, SQLite, Werkzeug, Requests, python-dotenv |
| **Security** | Flask-WTF (CSRF), Flask-Limiter (Rate Limiting), Scrypt password hashing, Proxy Header validation |
| **Frontend** | HTML5, CSS3, Vanilla ES6 JavaScript, Bootstrap 5.3, Bootstrap Icons |
| **Analytics & Maps** | Chart.js 4.4, Leaflet.js 1.9, OpenStreetMap Tiles |
| **Testing** | Pytest 9.2 (40 unit, integration, and E2E lifecycle tests with offline mocks) |

---

## 📂 Application Architecture

```
location-fetch/
├── app/
│   ├── __init__.py            # Flask factory, extension registration, SQLite auto-migrations
│   ├── extensions.py          # SQLAlchemy, CSRFProtect, Limiter singletons
│   ├── models.py              # Admin, TrackingLink, VisitorRecord, SystemSetting ORM models
│   ├── routes/
│   │   ├── auth.py            # Admin login, logout, and session lifecycle
│   │   ├── dashboard.py       # Admin dashboard page views (overview, links, visitors, map, settings)
│   │   ├── tracking.py        # Public tracking endpoint (/track/<token>) & auto-fetch
│   │   ├── links.py           # REST API: Tracking links CRUD (/api/links)
│   │   ├── visitors.py        # REST API: Search, filter, delete, and CSV export (/api/visitors)
│   │   ├── analytics.py       # REST API: Overview KPIs, timeline, country breakdown, map points
│   │   ├── diagnostics.py     # REST API: Multi-provider live comparison (/api/diagnostics/compare)
│   │   └── settings.py        # REST API: Retention policy & manual purge (/api/settings)
│   ├── services/
│   │   ├── ip_resolver.py     # Client IP resolution, anti-spoofing proxy validation, UA parser
│   │   ├── geolocation.py     # Multi-provider resolution with in-memory TTL caching
│   │   ├── provider_comparator.py # Multi-threaded parallel provider comparison & variance
│   │   ├── confidence.py      # City centroid detection & confidence rating engine
│   │   └── analytics.py       # Aggregation queries, Leaflet map coordinates, CSV generator
│   ├── static/
│   │   ├── css/style.css      # SaaS design system (Dark navy sidebar, emerald green accents)
│   │   └── js/
│   │       ├── dashboard.js   # Chart.js charts and live KPI metrics
│   │       ├── links.js       # Tracking link management & clipboard copy
│   │       ├── visitors.js    # Visitor records table, search debounce, modal details, pagination
│   │       └── analytics.js   # Leaflet map initialization, markers, and regional table
│   └── templates/
│       ├── base.html          # Base admin layout (sidebar, navbar, toasts)
│       ├── login.html         # Admin login portal
│       ├── dashboard.html     # SaaS analytics dashboard view
│       ├── links.html         # Tracking links management view
│       ├── visitors.html      # Searchable, filterable visitor table view
│       ├── analytics.html     # Leaflet map and approximate location view
│       ├── diagnostics.html   # Multi-provider comparison & variance view
│       ├── settings.html      # System retention and proxy configuration view
│       └── tracking.html      # Public visitor tracking confirmation view
├── api/
│   └── index.py               # Vercel serverless function entrypoint
├── instance/
│   └── iptrace.db             # SQLite database file (created on launch)
├── tests/
│   ├── conftest.py            # Pytest fixtures and test database setup
│   ├── test_auth.py           # Admin authentication and session tests
│   ├── test_tracking_links.py # Link creation, cryptographic token generation, cascading delete
│   ├── test_tracking_flow.py  # Public auto-fetch and decline flow tests
│   ├── test_accuracy_and_confidence.py # Centroids, confidence, disagreement, never-averaged tests
│   ├── test_ip_resolver_and_geo.py # IP extraction, proxy security, geolocation fallback tests
│   ├── test_analytics_and_visitors.py # Filtering, pagination, CSV export, retention tests
│   ├── test_rate_limiting.py  # Public endpoint rate limiting tests
│   └── test_e2e.py            # Complete end-to-end user lifecycle test
├── app.py                     # Universal WSGI entrypoint alias
├── config.py                  # Base Config and TestConfig (with safe serverless /tmp fallback)
├── run.py                     # Local development entry point
├── pyproject.toml             # Project metadata, Vercel entrypoint & PEP 621 dependencies
├── requirements.txt           # Python package dependencies
├── .env.example               # Environment variables template
├── .env                       # Local environment variables
└── README.md                  # Project documentation
```

---

## ☁️ Deploying to Vercel

IPTrace is pre-configured for zero-friction deployment to **Vercel Serverless Functions**:

1. **Push your code to GitHub**:
   ```bash
   git push origin main
   ```
2. **Import into Vercel**:
   - Go to [vercel.com](https://vercel.com) and click **"Add New Project"**.
   - Select your `location-fetch` repository.
   - Framework Preset: **Other** (Vercel automatically detects Python via `pyproject.toml` and `tool.vercel.entrypoint = "run:app"`).
3. **Configure Environment Variables** *(Optional in Project Settings)*:
   - `ADMIN_USERNAME`: Custom admin username (default: `admin`).
   - `ADMIN_PASSWORD`: Custom secure password (default: `AdminSecurePass123!`).
   - `SECRET_KEY`: Custom secret key for session signing.
   - `USE_PROXY_HEADERS`: Set to `True` for Vercel edge reverse proxy client IP resolution.
   - `IPINFO_API_TOKEN`: Optional API key for IPinfo.
4. **Deploy**:
   - Click **Deploy**. Vercel will install dependencies via `uv`, configure WSGI routing, and deploy your live URL.
   - Data is stored in `/tmp/iptrace.db` on serverless execution, and automatically initializes on first request.

---

## ⚡ Quick Start Guide

### Prerequisites
- Python 3.11+ installed.
- Git installed.

### Installation on Windows

```powershell
# 1. Clone the repository
git clone https://github.com/Bhuvo/location-fetch.git
cd location-fetch

# 2. Create virtual environment
python -m venv venv

# 3. Allow execution of scripts (if restricted) and activate venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create local environment file
Copy-Item .env.example .env

# 6. Run application
python run.py
```

### Installation on Linux / macOS

```bash
# 1. Clone the repository
git clone https://github.com/Bhuvo/location-fetch.git
cd location-fetch

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create local environment file
cp .env.example .env

# 5. Run application
python run.py
```

---

## 🔑 Default Credentials & Access

Open your browser:
- **Admin Dashboard**: [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login)
- **Default Username**: `admin`
- **Default Password**: `AdminSecurePass123!`

*(You can configure custom credentials in your `.env` file before first launch).*

---

## ⚙️ Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | *(Auto-generated)* | 64-character hexadecimal session & CSRF signing key |
| `ADMIN_USERNAME` | `admin` | Initial admin username |
| `ADMIN_PASSWORD` | `AdminSecurePass123!` | Initial admin password (hashed with Scrypt) |
| `IPINFO_API_TOKEN` | *(Blank)* | Optional IPinfo API token for higher rate limits |
| `IP_API_KEY` | *(Blank)* | Optional ip-api.com Pro key |
| `MAXMIND_ACCOUNT_ID` | *(Blank)* | Optional MaxMind account ID |
| `MAXMIND_LICENSE_KEY` | *(Blank)* | Optional MaxMind license key |
| `USE_PROXY_HEADERS` | `False` | Set `True` only behind trusted reverse proxies |
| `TRUSTED_PROXIES` | `127.0.0.1,::1` | Comma-separated list of trusted upstream proxy IPs |
| `DATA_RETENTION_DAYS` | `90` | Automated record retention cutoff (0 to keep indefinitely) |
| `DEV_RESOLVE_SERVER_PUBLIC_IP` | `True` | In dev mode, resolves machine public IP for 127.0.0.1 testing |

---

## 🌐 Network Testing Environments

- **Localhost Testing (`127.0.0.1`)**: Loopback addresses have no public coordinates. With `DEV_RESOLVE_SERVER_PUBLIC_IP=True` enabled in `.env`, IPTrace queries the host machine's external IP during local testing so realistic coordinates appear on your dashboard map.
- **LAN Testing (`192.168.x.x`)**: Private RFC 1918 addresses are safely recognized and tagged as local network interfaces.
- **Public Internet / Cloud Deployment**: When deployed behind Nginx, Caddy, or Cloudflare, set `USE_PROXY_HEADERS=True` and define your proxy IP in `TRUSTED_PROXIES` to inspect `X-Forwarded-For` without risk of spoofing.

---

## 🧪 Automated Testing Suite

IPTrace includes a comprehensive suite of **40 automated tests**:

```powershell
.\venv\Scripts\python.exe -m pytest -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.15.1, pytest-9.2.0
tests/test_accuracy_and_confidence.py ......... [ 22%]
tests/test_analytics_and_visitors.py .....     [ 35%]
tests/test_auth.py ......                      [ 50%]
tests/test_e2e.py .                            [ 52%]
tests/test_ip_resolver_and_geo.py ........     [ 72%]
tests/test_rate_limiting.py .                  [ 75%]
tests/test_tracking_flow.py ......             [ 87%]
tests/test_tracking_links.py .....             [100%]
============================= 40 passed in 10.20s =============================
```

All external provider HTTP calls are mocked in tests, enabling the entire test suite to execute fast and completely offline with 0 warnings.

---

## 📡 REST API Reference

### Public Tracking
- `GET /track/<token>`: Immediately resolves visitor IP, queries geolocation, saves record, and displays result.
- `POST /api/track/<token>/consent`: API endpoint to record visitor tracking request.
- `POST /api/track/<token>/decline`: Declines tracking request without saving any data.

### Administration (Session Required)
- `POST /admin/login`: Admin login.
- `POST /admin/logout`: Admin logout.
- `GET /api/links`: List all tracking links.
- `POST /api/links`: Create a new tracking link (`{"name": "Campaign Name"}`).
- `PATCH /api/links/<id>`: Toggle active status or edit link name.
- `DELETE /api/links/<id>`: Delete link and cascade-delete all associated visitor records.
- `GET /api/visitors`: Retrieve paginated, searchable, and filtered visitor records.
- `GET /api/visitors/<id>`: Retrieve full details for a single record.
- `DELETE /api/visitors/<id>`: Delete an individual visitor record.
- `GET /api/visitors/export`: Export filtered visitor records to CSV file.
- `GET /api/analytics/overview`: Top-level KPI counts.
- `GET /api/analytics/timeline`: Daily event counts over time.
- `GET /api/analytics/countries`: Top country distribution.
- `GET /api/analytics/map`: Approximate coordinates for Leaflet map markers.
- `GET /api/diagnostics/compare?ip=<ip>`: Multi-provider real-time diagnostic comparison.
- `GET /api/settings`: Current retention and network configuration.
- `POST /api/settings/retention`: Update retention cutoff in days.
- `POST /api/settings/purge`: Manually purge records older than retention threshold.

---

## 🛡️ Security & Privacy Architecture

1. **Anti-Spoofing IP Resolution**: Never trusts arbitrary `X-Forwarded-For` headers by default. Only configured `TRUSTED_PROXIES` are permitted to pass upstream client headers.
2. **Rate Limiting**: Public endpoints are rate-limited to 30 requests/minute per IP with `Flask-Limiter`.
3. **Session Hardening**: Cookies configured with `HttpOnly=True`, `SameSite='Lax'`, and 8-hour lifetime.
4. **Data Retention**: Automated pruning of visitor records older than the configured threshold (default 90 days).
5. **No Fingerprinting**: Does not use third-party tracking pixels, canvas probing, or invasive cookies.

---

## 📜 License & Ethical Disclaimer

This project is licensed under the **MIT License**.

**Educational & Authorized Use**: IPTrace is developed strictly for educational analytics, authorized research, and transparency demonstrations. Do not use this tool for unauthorized tracking, deceptive collection, or malicious surveillance.
