# SwachhVayu AI — Urban Air Quality Assistant for India

> **"Don't just check the air. Know what to do, when to do it, and why it matters."**

A GenAI-powered assistant that suggests **low-emission daily routines,
indoor air quality hacks, and sustainable alternatives tailored to a user's
location and lifestyle — and clearly explains the direct impact of each
choice.**

Built for **Hack2Skill Virtual: PromptWars — Challenge 6: Urban Air Quality
Assistant**. Free, no login, no account. India only.

> **Live app:** https://swachh-vayu-ai.streamlit.app/
> **Demo video:** _add the Unlisted YouTube link after upload_
> **By Bhavana Shah** · Hack2Skill Virtual: PromptWars — Challenge 6

## What it does

SwachhVayu AI turns air-quality data into **actionable daily decisions for
Indian families**. It does not just show an AQI number — it tells you when
to exercise, when to open windows, whether it is safe to run at 7 AM or
6 PM, what your cooking is doing to your indoor air, and how much CO2 your
commute choices save — with a **"Why This, Why Now?"** explanation on every
single recommendation:

- **Why this?** — the reason for the recommendation
- **Why now?** — why today's conditions make it relevant
- **What impact?** — what changes if you follow it

## The Indian AQI — calculated in-app (CPCB method)

The app's primary display is the **Calculated Indian AQI**, computed in-app
from Open-Meteo modelled concentrations using the **CPCB (Central Pollution
Control Board) methodology** — the same method behind India's official
National Air Quality Index (NAQI). The breakpoint table is verified from
CPCB's own site (cpcb.gov.in, 20 Nov 2026) and pinned by 94 unit tests.

How it works:

- The app requests `past_hours=24` + `forecast_days=5` (timezone
  Asia/Kolkata) and computes **24-hour means** for PM2.5 / PM10 / NO2 / SO2
  and **8-hour means** for O3 / CO.
- Open-Meteo reports CO in µg/m³, so it is divided by 1000 to mg/m³
  **before** the CPCB breakpoints are applied.
- Each pollutant gets a sub-index by linear interpolation within its CPCB
  band; the overall AQI is the **worst (maximum) sub-index**, capped at 500.
- CPCB rule: minimum **3 pollutants, one of which must be PM2.5 or PM10** —
  otherwise the app shows "insufficient data for Indian AQI" and falls back
  to the US AQI as the primary display, labelled as such.
- NH3 and Pb are **not available** from Open-Meteo — the app shows them as
  "not available" and never invents values.
- The dashboard shows the averaging basis ("24-hr mean, 24 hourly values"
  or "partial: 14 hourly values"), the dominant pollutant, and the sub-index
  per pollutant — so users see **why** the AQI is what it is.

The Severe band has no upper bound in the CPCB table. Convention used here
(documented in `planner/indian_aqi.py`): the Severe band is interpolated
over the previous band's width and capped at 500.

### Three data types — never mixed

1. **CPCB station measurement** — the official NAQI. This app does **not**
   integrate live station data (no verified free CPCB API) and never claims
   a station reading.
2. **Open-Meteo modelled estimate** — Copernicus CAMS modelled forecast
   data (NOT live sensor data). Labelled "Latest available modelled
   estimate" + data timestamp + source credit + limitations, everywhere.
3. **Calculated Indian AQI** — computed in-app from modelled concentrations
   (above). Labelled "Calculated Indian AQI (CPCB method) from modelled
   data — not a CPCB station reading."

US AQI and European AQI (from Open-Meteo) are shown as **separate
secondary references**, never mixed into the Indian AQI. The Learn page
explains why apps differ: CPCB caps NAQI at 500 and uses 24-hr averages,
while US-method apps can show much higher numbers for the same air.

## Features (18 modules, one page each)

| # | Module | Page |
|---|--------|------|
| 1 | Home Dashboard — calculated Indian AQI, pollutants, weather, morning briefing, alerts, hourly + 5-day charts, data confidence | Home Dashboard |
| 2 | Indian City Search + Locations — India-only search, state-wise selection, bundled 45-city database, favourites, recent cities, Home/Office/School tracking, travel check | My Locations |
| 3 | Forecast + Pollution Predictor — hourly + 5-day forecast, best/worst hours, rule-based spike predictor, anomaly detection | Forecast & Predictor |
| 4 | Personalised Daily Routine — profile (sensitivity, commute, WFH, household), dynamic plan that flags forecast changes, offline saved routine | My Routine |
| 5 | Smart Activity Planner — "Is it safe to…?" for running, walking, cycling, yoga, outdoor gym, children's play, morning walk, gardening | Activity Planner |
| 6 | Indoor Air Intelligence — PM2.5 estimator (labelled ESTIMATE), room-by-room planner, cooking advisor, source checklist, ventilation timing, Home Clean-Air Score | Indoor Air |
| 7 | Sustainable Alternatives + Impact Calculator — transport/home/food/shopping swaps with CO2 estimates + local practicality | Alternatives & Impact |
| 8 | AI What-If Simulator — commute modes, time-of-day (7 AM vs 6 PM), cooking ventilation, Impact Score | What If Simulator |
| 9 | Gemini AI Assistant — Hindi / English / Hinglish chat with follow-ups, voice briefing (gTTS), Report Explainer (PDF/TXT/CSV/image) | AI Assistant |
| 10 | Multi-City Comparison + Map + Ranking — 2–4 Indian cities, same scale + timestamp; Plotly India map (city-level modelled values, not station data) | Compare & Map |
| 11 | Smart Alerts — in-app only (no push): poor-air, PM2.5, exercise-limit, ventilation tips, forecast warnings | Alerts |
| 12 | Family & Household — family profiles, 7-Day Challenge, habit tracker, badges, goals, weekly report, family calendar, School Air Safety Planner, Festival Guide | Family & Household |
| 13 | Mask & Air Purifier Guide — N95/FFP2, HEPA, CADR, room-size, filter replacement (educational only) | Mask & Purifier Guide |
| 14 | India Environmental Awareness — Diwali mode, stubble burning, construction dust, traffic intelligence (time-based only, no invented data), seasonal comparison, pollutant sources | Awareness |
| 15 | Community & Education — city dashboard, community challenges, Report Local Pollution (generates a formatted report — the app does NOT submit anything), awareness quiz, household-local leaderboard | Community |
| 16 | Advanced Data & Analytics — historical trends (Open-Meteo past_days + local snapshots), pollutant comparison, anomaly + confidence, seasonal analysis | Analytics |
| 17 | Personal Dashboard, Progress & Reports — saved plan, history, Markdown/CSV/PDF export, share summary, offline saved routine | My Plan & Reports |
| 18 | Accessibility, Settings, Learn + Digital Twin — Hindi/English toggle, large text, high contrast, simple language, colour-independent AQI labels, CPCB explainer, experimental educational Digital Twin | Learn & Digital Twin |

**Signature feature:** "Why This, Why Now?" — every recommendation shows
Why this? / Why now? / What impact?, implemented as a shared component
(`planner/why.py`), not one-off text.

## Approach / logic

- **Data:** Open-Meteo Air Quality API (free, no key) — current + hourly
  (PM2.5, PM10, NO2, SO2, CO, O3, US AQI, European AQI, dust), `past_hours=24`
  for the CPCB averaging windows, 5-day forecast, timezone Asia/Kolkata;
  Geocoding API (results filtered to `country_code == "IN"`); Forecast API
  for weather context. Calls are cached in-session (`st.cache_data`, 15-min
  TTL) to stay polite within free limits.
- **Indian AQI:** calculated in-app from the hourly concentrations
  (`planner/indian_aqi.py`, CPCB method, see above). Hourly points also get
  an *indicative* single-hour Indian AQI for the activity planner and
  charts — labelled as indicative, since a single hour is not a CPCB mean.
- **Routine engine:** rule-based, driven by the primary AQI (Indian when
  available, US fallback) and the real hourly forecast — cleanest window,
  best/worst hours, exercise/mask limits per sensitivity (Indian limits
  follow CPCB bands: 200 general / 100 sensitive; US limits 150 / 100).
- **Indoor estimator:** a documented box model (outdoor PM2.5 × ventilation
  factor + cooking + smoking + occupants, × room-size factor; purifier
  removes ~55%). All assumptions and uncertainty (±50% or more) are shown;
  the result is an estimate, never a measurement.
- **Impact maths:** simple emission factors (petrol/diesel car 0.17,
  auto-rickshaw 0.08, two-wheeler 0.06, bus 0.05, metro 0.03, EV 0.05,
  carpool 0.085, cycle/walk/WFH 0 kg CO2 per passenger-km — typical Indian
  grid and fleet averages). Every figure is an estimate with its assumption
  stated.
- **Storage:** SQLite (`swachhvayu.db`) for favourites, recent cities,
  saved locations, plan history and daily AQI snapshots, with a graceful
  in-memory fallback if the database cannot be written. **Note:** Streamlit
  Community Cloud's filesystem is ephemeral, so saved data may reset when
  the app sleeps or reboots.
- **Accessibility:** Hindi + English UI toggle, large-text mode,
  high-contrast mode, simple-language mode, colour-independent AQI labels
  (text + symbol, never colour alone), screen-reader-friendly badge labels.

## GenAI usage

- **Google Gemini `gemini-2.5-flash`** via `google-genai`, on the AI
  Assistant page only, **optional** and capped at **5 calls per session**.
- Prompts send **only validated context** (city, AQI values, sensitivity,
  commute, exercise habits). Free-text user notes are fenced as untrusted
  data and the model is told not to follow instructions inside them.
- Answers are **grounded in the forecast + user profile**, never generic.
- **Offline rule-based fallback** (English + Hindi) when no key is set or
  Gemini fails — the app is fully usable without an API key.
- **Voice:** gTTS (free) reads the morning briefing aloud, best-effort,
  with the full text always visible.
- **Report Explainer:** upload a pollution report (PDF via pypdf, TXT, CSV;
  images need Gemini) — Gemini explains it in plain language with a Hindi
  summary; offline, a basic summary is produced without AI.
- The key comes from the `GEMINI_API_KEY` environment variable or Streamlit
  secrets — **never hard-coded, never stored in the repo**.
- No ChatGPT / OpenAI / Claude / paid tools are used or claimed.

## Data sources

- **Open-Meteo Air Quality API** — https://open-meteo.com/en/docs/air-quality-api
  (Copernicus CAMS modelled data; free, no key, non-commercial)
- **Open-Meteo Geocoding API** — https://open-meteo.com/en/docs/geocoding-api
- **Open-Meteo Forecast API** — https://open-meteo.com/en/docs
- **CPCB — National Air Quality Index** — https://cpcb.nic.in/national-air-quality-index/
  (breakpoint table verified 20 Nov 2026)
- **Bundled Indian city database** — 45 cities in 22 states/UTs, coordinates
  verified against the Geocoding API at build time (20 Nov 2026).

## Honesty rules (hard)

- Modelled data is labelled modelled, with timestamp + limitations. Sample /
  demo data (offline fallback) carries a clear "sample data" banner.
- The calculated Indian AQI is **never** presented as a CPCB station reading.
- Indoor estimator outputs are estimates, not measurements. Impact/CO2
  figures are estimates with disclosed assumptions, not measured emissions.
- Health guidance is general information, not medical advice. Sensitive-group
  guidance is conservative and non-diagnostic.
- No fake bookings, payments, accounts, push notifications, sensor data,
  traffic data, station data, global leaderboards, or authority submissions.
  Report Local Pollution **generates** a formatted report for the user — it
  does not submit anything. The leaderboard is household-local only. The
  Digital Twin is labelled an educational simulation, not a prediction.
- Every feature ships genuinely working or not at all — no placeholder
  buttons that pretend to work.

## How to run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Optional Gemini: set `GEMINI_API_KEY` (environment variable or
`.streamlit/secrets.toml`). Without it, the AI Assistant uses the offline
fallback.

```bash
# Tests
pip install -r requirements-dev.txt
python -m pytest -q
```

## Tests

419 tests, all passing (`pytest -q`, ~2s): Indian AQI calculation (94 tests
pinning the verified CPCB breakpoint table), AQI banding (US + European),
API parsing (mocked responses, India-only filtering, past_hours request),
routine generation, safety verdicts, indoor estimator, impact maths,
What-If scenarios, habits/badges/scores, alerts, household guidance,
store (SQLite + memory fallback), i18n, forecast predictor/anomaly,
rooms, Digital Twin, community (report/quiz/leaderboard), awareness,
school planner, voice, AI prompt fencing + offline fallback + report
explainer, exports (Markdown/CSV/PDF), and app smoke tests (18 pages,
all modules import, no hard-coded key).

CI (`.github/workflows/ci.yml`) runs `pytest -q` on Python 3.12.

## Assumptions & limitations

- Open-Meteo air data is **modelled** (CAMS), not measured — it can differ
  from a ground monitor near you. The app says so everywhere a number
  appears.
- The calculated Indian AQI uses modelled concentrations, so it is an
  estimate of what the CPCB method would give — not an official reading.
- India only: city search is filtered to India; non-Indian searches get a
  clear "covers India only" note.
- All times are IST (Asia/Kolkata).
- No login, no account: profile, habits and plans live in the session;
  favourites/history/snapshots live in a local SQLite file (ephemeral on
  Streamlit Community Cloud — see Storage above).
- The Digital Twin is a teaching model with disclosed weights, not a
  scientific forecast.
- Voice (gTTS) needs internet at runtime; it is best-effort with text
  always available.
