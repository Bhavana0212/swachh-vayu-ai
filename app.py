"""SwachhVayu AI — Urban Air Quality Assistant for India.

Hack2Skill PromptWars Challenge 6. India-only: the app calculates the
Indian AQI in-app from Open-Meteo modelled concentrations (CPCB method),
and turns it into actionable daily decisions for Indian families.

Free, no login, no account: Streamlit + Open-Meteo (no key) + optional
Gemini (free tier). All data is session-local; favourites/history live in
a local SQLite file with a session-state fallback.
"""
from __future__ import annotations

import math
import pathlib

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import date

from planner import aqi as aqi_mod
from planner.alerts import build_alerts
from planner.alternatives import swaps_for, weekly_co2_saving_kg
from planner.api import (
    DATA_NOTE,
    DEMO_CITIES,
    INDIAN_CITIES,
    INDIA_ONLY_NOTE,
    QUICK_CITIES,
    WEATHER_CODE_LABELS,
    AirReport,
    City,
    fetch_air,
    fetch_past_days,
    ist_now,
    sample_report,
    search_cities_with_note,
    city_from_bundled,
)
from planner.awareness import (
    CONSTRUCTION_INFO,
    DIWALI_NOTE,
    DIWALI_PHASES,
    FESTIVALS,
    GOVERNMENT_RESOURCES,
    SOURCES,
    SOURCES_NOTE,
    STUBBLE_INFO,
    TRAFFIC_INFO,
)
from planner.community import (
    COMMUNITY_CHALLENGES,
    QUIZ_QUESTIONS,
    REPORT_DISCLAIMER,
    REPORT_TYPES,
    PollutionReport,
    grade_quiz,
    household_leaderboard,
)
from planner.export import (
    plan_to_csv,
    plan_to_markdown,
    plan_to_pdf,
    share_summary,
)
from planner.forecast import (
    PREDICTOR_NOTE,
    SEASONS,
    detect_anomalies,
    detect_spikes,
    morning_briefing,
    seasonal_analysis,
)
from planner.habits import (
    HABITS,
    badges_earned,
    challenge_progress,
    goal_progress,
    habits_this_week,
    streak_days,
    total_habits,
    weekly_report_text,
)
from planner.household import (
    ROLES,
    Member,
    household_summary,
)
from planner.i18n import greeting, t
from planner.indoor import (
    ASSUMPTIONS_TEXT,
    EQUIPMENT_GUIDE,
    INDOOR_HACKS,
    estimate_indoor_pm25,
    improvement_comparison,
)
from planner.rooms import (
    COOKING_TIPS,
    ROOMS,
    SOURCE_CHECKLIST,
    home_clean_air_score,
    room_plan,
    ventilation_advice,
)
from planner.routine import (
    COMMUTE_MODES,
    HOUSEHOLD_TYPES,
    SENSITIVITIES,
    WORKPLACES,
    Profile,
    build_day_plan,
)
from planner.safety import ACTIVITIES, assess
from planner.school import SCHOOL_CHECKLIST, school_plan
from planner.score import co2_savings_series, grade_for, impact_score
from planner.store import Store, default_store
from planner.twin import SCENARIOS, TWIN_LABEL, improvement_suggestions, simulate
from planner.utils import day_label, hour_label
from planner.voice import VOICE_LANGUAGES, briefing_script, speak
from planner.whatif import (
    compare_modes,
    compare_times,
    cooking_ventilation_scenario,
    lowest_emission_mode,
)
from planner.why import why_block_html
from planner.ai import (
    EXPLAINABILITY_TEXT,
    LANGUAGES as AI_LANGUAGES,
    MAX_AI_CALLS_PER_SESSION,
    extract_report_text,
    generate_advice,
    generate_followup,
    generate_report_explanation,
    get_api_key,
    local_advice,
    offline_report_summary,
)
from planner.indian_aqi import (
    CATEGORIES as INDIAN_CATEGORIES,
    LABEL as INDIAN_AQI_LABEL,
    category_for as indian_category_for,
)

st.set_page_config(
    page_title="SwachhVayu AI — Urban Air Quality Assistant",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "SwachhVayu AI — Urban Air Quality Assistant for India. "
                         "Calculated Indian AQI (CPCB method) from modelled "
                         "data, personalised routines, indoor air hacks and "
                         "sustainable alternatives. Free, no login."},
)


def load_professional_theme() -> None:
    """Inject the professional theme CSS (assets/professional-theme.css).

    Theme lives in its own file, not mixed into app logic — that is the
    well-architected split: planner/ = engine, app.py = screens,
    assets/professional-theme.css = look. If the file is missing (e.g.
    a partial upload), the app still works with Streamlit's default look.
    """
    css_path = pathlib.Path(__file__).resolve().parent / "assets" / "professional-theme.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


load_professional_theme()


def load_hero_art() -> str:
    """Decorative hero SVG (assets/hero.svg), inlined; empty if missing."""
    svg_path = pathlib.Path(__file__).resolve().parent / "assets" / "hero.svg"
    if svg_path.exists():
        return svg_path.read_text(encoding="utf-8")
    return ""

APP_NAME = "SwachhVayu AI"

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------


def _init_state() -> None:
    defaults = {
        "city": {"name": "Delhi", "lat": 28.65, "lon": 77.23},
        "lang": "en",
        "large_text": False,
        "high_contrast": False,
        "simple_language": False,
        "profile": Profile(),
        "members": [],
        "habit_log": {},
        "challenge_days": [],
        "goal_kg": 5.0,
        "adopted": set(),
        "ai_calls": 0,
        "chat_history": [],
        "quiz_answers": {},
        "community_done": set(),
        "plan": None,
        "plan_report_time": "",
        "search_results": [],
        "search_note": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


_init_state()


def get_store() -> Store:
    if "store" not in st.session_state:
        st.session_state["store"] = default_store()
    return st.session_state["store"]


# ---------------------------------------------------------------------------
# Data loading (cached, polite to the free API)
# ---------------------------------------------------------------------------


@st.cache_data(ttl=900, show_spinner=False)
def load_report(name: str, lat: float, lon: float) -> AirReport:
    """Live report, or a clearly-labelled sample report when offline."""
    city = City(name=name, latitude=lat, longitude=lon)
    try:
        return fetch_air(city)
    except Exception:
        return sample_report(city)


def current_report() -> AirReport:
    city = st.session_state["city"]
    report = load_report(city["name"], city["lat"], city["lon"])
    # Record today's snapshot for the Analytics page (cheap, idempotent).
    try:
        store = get_store()
        indian = report.indian_aqi
        store.save_snapshot(
            report.city.name, date.today().isoformat(),
            indian_aqi=(indian.value if indian.available else None),
            us_aqi=report.current.us_aqi,
            pm25=report.current.pm2_5)
        store.add_recent({"name": city["name"], "lat": city["lat"],
                          "lon": city["lon"]})
    except Exception:
        pass
    return report


def set_city(name: str, lat: float, lon: float) -> None:
    st.session_state["city"] = {"name": name, "lat": lat, "lon": lon}


# ---------------------------------------------------------------------------
# Small UI helpers
# ---------------------------------------------------------------------------


def lang() -> str:
    return st.session_state["lang"]


def L(key: str) -> str:
    return t(key, lang())


def apply_accessibility_css() -> None:
    css = []
    if st.session_state["large_text"]:
        css.append("html, body, [class*='st-'] { font-size: 1.15rem !important; }")
    if st.session_state["high_contrast"]:
        css.append("""
            .stApp { background-color: #000000; color: #FFFFFF; }
            .stApp [data-testid="stSidebar"] { background-color: #111111; }
            .stApp h1, .stApp h2, .stApp h3 { color: #FFFFFF; }
            .stApp label { color: #FFFFFF !important; }
            .stApp [data-testid="stCaptionContainer"] { color: #D1D5DB !important; }
            """)
    if css:
        st.markdown(f"<style>{''.join(css)}</style>", unsafe_allow_html=True)


def sample_banner(report: AirReport) -> None:
    if not report.is_live:
        st.warning(L("sample_banner"), icon="⚠️")


def source_caption(report: AirReport) -> None:
    st.caption(
        f"{report.source} · Data time: {report.current.time or '—'} IST · "
        f"Fetched: {report.fetched_at or '—'}")
    st.caption(DATA_NOTE)


def render_why(why) -> None:
    if why is not None:
        st.markdown(why_block_html(why), unsafe_allow_html=True)


def pollutant_card(label: str, value, unit: str, status: str) -> None:
    text = f"{value:g} {unit}" if value is not None else "not available"
    st.metric(label, text, help=f"Data status: {status}")


# CPCB band colours, reused wherever a chart colours by AQI band — the
# same verified colours as planner/indian_aqi.CATEGORIES, never re-themed.
CPCB_DISCRETE_COLOURS = {cat: colour for _, _, cat, colour, _, _
                         in INDIAN_CATEGORIES}

# Display names for pollutant/data keys — used by the sub-index chart,
# the sub-index table and the Data confidence table, so users never see
# raw keys like "nitrogen_dioxide" or "PM2 5". Presentation only.
POLLUTANT_LABELS = {
    "pm2_5": "PM2.5", "pm10": "PM10", "nitrogen_dioxide": "NO2",
    "ozone": "O3", "sulphur_dioxide": "SO2", "carbon_monoxide": "CO",
    "dust": "Dust", "indian_aqi": "Indian AQI", "us_aqi": "US AQI",
    "european_aqi": "European AQI", "weather": "Weather",
}


def pollutant_label(key: str) -> str:
    """Human-readable label for a pollutant/data key."""
    return POLLUTANT_LABELS.get(key, key.replace("_", " ").title())


def labelled_basis(basis: str) -> str:
    """Replace raw pollutant keys inside the averaging-basis sentence
    with display labels, so users never see 'pm2_5' or
    'nitrogen_dioxide'. Longest keys first, so no partial replacement
    can occur. Presentation only — the stored basis is untouched."""
    out = basis
    for key, label in sorted(POLLUTANT_LABELS.items(),
                             key=lambda kv: -len(kv[0])):
        out = out.replace(key, label)
    return out


# Plotly modebar hidden on all charts: the grey toolbar cluttered the
# white chart cards; the same data is always in a table or the legend.
PLOTLY_CONFIG = {"displayModeBar": False}
# Continuous scale with HARD edges at the CPCB band limits (0/50/100/200/
# 300/400/500 over a 0–500 range), so a coloured marker always falls in
# its real CPCB band instead of blending between bands.
CPCB_COLORSCALE = [
    (0.0, "#00B050"), (0.10, "#00B050"),
    (0.10, "#92D050"), (0.20, "#92D050"),
    (0.20, "#FFFF00"), (0.40, "#FFFF00"),
    (0.40, "#FF9900"), (0.60, "#FF9900"),
    (0.60, "#FF0000"), (0.80, "#FF0000"),
    (0.80, "#C00000"), (1.0, "#C00000"),
]


def theme_fig(fig, legend_below: bool = False):
    """Shared Plotly styling: theme font, transparent paper (the chart
    sits on a white CSS card), soft gridlines, tidy margins. Legends sit
    inside the plot (short entries) or below it (long band names, which
    clip inside)."""
    legend = (dict(bgcolor="rgba(255,255,255,0.85)",
                   bordercolor="#D1E7DC", borderwidth=1,
                   orientation="h", yanchor="top", y=-0.2,
                   xanchor="center", x=0.5)
              if legend_below else
              dict(bgcolor="rgba(255,255,255,0.85)",
                   bordercolor="#D1E7DC", borderwidth=1,
                   x=0.99, xanchor="right", y=0.99, yanchor="top"))
    fig.update_layout(
        font=dict(family="Inter, 'Segoe UI', system-ui, sans-serif",
                  size=13, color="#1F2937"),
        title=dict(font=dict(size=15, color="#0A5C44")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=legend,
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#D1E7DC",
                        font_size=12),
        # A below-chart legend needs bottom room, else it sits inside
        # the frame's bottom edge.
        margin=dict(l=10, r=10, t=40, b=60 if legend_below else 10))
    fig.update_xaxes(gridcolor="#E5E7EB", zerolinecolor="#E5E7EB")
    fig.update_yaxes(gridcolor="#E5E7EB", zerolinecolor="#E5E7EB")
    return fig


def aqi_chart(hourly, title: str):
    """Hourly PM2.5 + Indian AQI chart (Plotly)."""
    times = [p.time[11:16] for p in hourly]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=[p.pm2_5 for p in hourly], name="PM2.5 (µg/m³)",
        mode="lines+markers", line=dict(color="#0E7490", width=2.5),
        marker=dict(size=5)))
    fig.add_trace(go.Scatter(
        x=times, y=[p.indian_aqi for p in hourly],
        name="Indian AQI*", mode="lines",
        line=dict(color="#C2410C", dash="dash", width=2)))
    fig.update_layout(title=title, xaxis_title="Time (IST)",
                      yaxis_title="PM2.5 (µg/m³) / AQI", height=320)
    return theme_fig(fig)


def _gauge_arc(cx: float, cy: float, r: float, start_deg: float,
               end_deg: float) -> str:
    """SVG arc path for one gauge band (angles in degrees, 180 = left,
    360 = right, over the top of the dial)."""
    x1 = cx + r * math.cos(math.radians(start_deg))
    y1 = cy + r * math.sin(math.radians(start_deg))
    x2 = cx + r * math.cos(math.radians(end_deg))
    y2 = cy + r * math.sin(math.radians(end_deg))
    return f"M {x1:.1f} {y1:.1f} A {r} {r} 0 0 1 {x2:.1f} {y2:.1f}"


def aqi_gauge_html(indian) -> str:
    """Animated AQI gauge dial (inline SVG). The needle sweeps from the
    left to the real AQI value on load (CSS animation in the theme).
    Band arcs use the CPCB colours; the badge next to it stays the
    accessible, labelled reading."""
    value = indian.value if indian.available else None
    if value is None:
        return ""
    clamped = max(0.0, min(500.0, float(value)))
    angle = (clamped / 500.0) * 180.0 - 90.0
    arcs = "".join(
        f'<path d="{_gauge_arc(100, 100, 80, 180 + 30 * i, 210 + 30 * i)}" '
        f'stroke="{colour}" stroke-width="14" fill="none" '
        f'stroke-linecap="butt"/>'
        for i, (_, _, _, colour, _, _) in enumerate(INDIAN_CATEGORIES))
    return (
        '<div class="sv-gauge" role="img" aria-label="Calculated Indian AQI '
        f'gauge: {indian.value:g}, {indian.category}">'
        '<svg viewBox="0 0 200 122" aria-hidden="true">'
        f"{arcs}"
        '<g class="gauge-needle" style="--gauge-angle: '
        f'{angle:.1f}deg">'
        '<line x1="100" y1="100" x2="100" y2="32" stroke="#1F2937" '
        'stroke-width="3" stroke-linecap="round"/></g>'
        '<circle cx="100" cy="100" r="7" fill="#1F2937"/>'
        '<circle cx="100" cy="100" r="3" fill="#FFFFFF"/>'
        f'<text x="100" y="118" text-anchor="middle" class="gauge-value">'
        f'{indian.value:g}</text>'
        '<text x="22" y="118" text-anchor="middle" class="gauge-tick">0</text>'
        '<text x="178" y="118" text-anchor="middle" class="gauge-tick">500</text>'
        "</svg>"
        f'<div class="gauge-category" style="margin-top:-6px;">'
        f"{indian.symbol} {indian.category}</div></div>"
    )


def sub_index_chart(indian):
    """Vertical bar chart of the CPCB sub-index per pollutant — the
    visual answer to 'why is the AQI this value?'. Bars are coloured by
    their CPCB band; values are the real calculated sub-indices, largest
    first so the dominant pollutant leads (same order as the table
    below). Vertical, mirroring the 5-day trend chart: the earlier
    horizontal version rendered its value labels microscopically in the
    deployed app despite textfont size 14, while the vertical 5-day
    chart's labels are legible — so this chart copies that proven
    structure exactly."""
    items = sorted(indian.sub_indices.items(), key=lambda kv: -kv[1])
    labels = [pollutant_label(key) for key, _ in items]
    values = [sub for _, sub in items]
    cats = [indian_category_for(sub)[0] for sub in values]
    fig = px.bar(x=labels, y=values, color=cats,
                 color_discrete_map=CPCB_DISCRETE_COLOURS,
                 labels={"x": "Pollutant", "y": "Sub-index (CPCB)",
                         "color": "CPCB band"},
                 # Discrete colour groups re-order the x-axis unless
                 # pinned: keep the largest-first order.
                 category_orders={"x": labels})
    fig.update_layout(height=320, showlegend=True,
                      legend=dict(title="CPCB band"))
    # Value labels on top of each bar (same pattern as the 5-day chart),
    # with headroom so the tallest label is never clipped.
    top = max(values) if values else 0
    if top > 0:
        fig.update_yaxes(range=[0, top * 1.15])
    fig.update_traces(marker_line_width=0, texttemplate="%{y:.0f}",
                      textposition="outside",
                      textfont=dict(size=14, color="#1F2937"),
                      hovertemplate="%{x}: %{y:.0f}<extra></extra>")
    return theme_fig(fig, legend_below=True)


# ---------------------------------------------------------------------------
# Sidebar: city, language, accessibility, navigation
# ---------------------------------------------------------------------------

PAGES = [
    ("nav_home", "home"), ("nav_locations", "locations"),
    ("nav_forecast", "forecast"), ("nav_routine", "routine"),
    ("nav_activity", "activity"), ("nav_indoor", "indoor"),
    ("nav_alternatives", "alternatives"), ("nav_whatif", "whatif"),
    ("nav_ai", "ai"), ("nav_compare", "compare"),
    ("nav_alerts", "alerts"), ("nav_family", "family"),
    ("nav_equipment", "equipment"), ("nav_awareness", "awareness"),
    ("nav_community", "community"), ("nav_analytics", "analytics"),
    ("nav_plan", "plan"), ("nav_learn", "learn"),
]

with st.sidebar:
    st.markdown(f"## 🌿 {APP_NAME}")
    st.caption(L("tagline"))
    now = ist_now()
    st.caption(f"{now.strftime('%A, %d %B %Y · %I:%M %p')} IST")

    lang_choice = st.selectbox(
        L("language"), ["English", "हिंदी (Hindi)"],
        index=0 if lang() == "en" else 1, key="lang_select")
    st.session_state["lang"] = "hi" if "हिंदी" in lang_choice else "en"

    st.markdown(f"### {L('city')}")
    quick = st.selectbox(
        "Quick cities", list(QUICK_CITIES),
        index=list(QUICK_CITIES).index(st.session_state["city"]["name"])
        if st.session_state["city"]["name"] in QUICK_CITIES else 0,
        key="quick_city")
    if quick != st.session_state["city"]["name"]:
        lat, lon, _ = QUICK_CITIES[quick]
        set_city(quick, lat, lon)
        st.rerun()

    query = st.text_input("Search an Indian city", key="city_search",
                          placeholder="e.g. Varanasi, Kochi, Indore")
    if query:
        try:
            results, had_non_indian = search_cities_with_note(query)
            st.session_state["search_results"] = results
            st.session_state["search_note"] = had_non_indian and not results
        except Exception:
            st.session_state["search_results"] = []
            st.session_state["search_note"] = False
    for result in st.session_state.get("search_results", [])[:5]:
        label = f"{result.name}, {result.admin1}" if result.admin1 else result.name
        if st.button(label, key=f"search_{result.name}_{result.latitude}"):
            set_city(result.name, result.latitude, result.longitude)
            st.session_state["search_results"] = []
            st.rerun()
    if st.session_state.get("search_note"):
        st.info(INDIA_ONLY_NOTE)

    with st.expander("Browse by state"):
        state = st.selectbox("State / UT", sorted(INDIAN_CITIES),
                             key="state_select")
        city_names = [name for name, _, _ in INDIAN_CITIES[state]]
        chosen = st.selectbox("City", city_names, key="state_city_select")
        if st.button("Show this city", key="state_city_go"):
            found = city_from_bundled(chosen)
            if found:
                set_city(found.name, found.latitude, found.longitude)
                st.rerun()

    st.markdown("### Accessibility")
    st.session_state["large_text"] = st.checkbox(
        "Large text", value=st.session_state["large_text"], key="acc_large")
    st.session_state["high_contrast"] = st.checkbox(
        "High contrast", value=st.session_state["high_contrast"],
        key="acc_contrast")
    st.session_state["simple_language"] = st.checkbox(
        "Simple language", value=st.session_state["simple_language"],
        key="acc_simple")

    page_labels = [L(key) for key, _ in PAGES]
    page_ids = [pid for _, pid in PAGES]
    chosen_label = st.radio("Navigate", page_labels, key="nav_radio",
                            label_visibility="collapsed")
    page = page_ids[page_labels.index(chosen_label)]

apply_accessibility_css()
report = current_report()


# ---------------------------------------------------------------------------
# Page 1 — Home Dashboard (Module 1)
# ---------------------------------------------------------------------------


def page_home() -> None:
    now = ist_now()
    # Hero header block (same content as the old title + greeting, now a
    # designed, animated band with SVG skyline art).
    st.markdown(
        '<div class="sv-hero">'
        f'<div class="sv-hero-art">{load_hero_art()}</div>'
        '<div class="pro-header">'
        f'<span class="pro-brand">🌿 {APP_NAME}</span>'
        f'<span class="pro-tag">{L("tagline")}</span></div>'
        f"<h1>{L('nav_home')} — {report.city.name}</h1>"
        f"<p class=\"sv-hero-sub\"><b>{greeting(now.hour, lang())}</b> · "
        f"{now.strftime('%A, %d %B %Y · %I:%M %p')} IST</p>"
        "</div>",
        unsafe_allow_html=True)
    sample_banner(report)

    indian = report.indian_aqi
    value, scale, category = report.primary_aqi()
    conf = report.data_confidence()

    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.subheader(L("indian_aqi"))
        if indian.available:
            st.markdown(indian.badge_html(), unsafe_allow_html=True)
            st.markdown(aqi_gauge_html(indian), unsafe_allow_html=True)
            st.caption(INDIAN_AQI_LABEL)
            st.caption(f"Averaging basis: {labelled_basis(indian.basis)}")
            st.caption(f"Dominant pollutant: {pollutant_label(indian.dominant)}")
        else:
            st.warning(f"{indian.reason} Showing {scale} as the primary "
                       "display instead.")
            if value is not None:
                st.metric(scale, f"{value:g}", category)
        if st.session_state["simple_language"]:
            st.info(f"Simple version: the air today is **{category.lower()}**."
                    " " + ("Stay indoors as much as you can."
                           if value is not None and value > 200
                           else "Outdoor time is fine — prefer quieter streets."))
    with col_b:
        st.subheader("Secondary references (separate scales)")
        us_band = aqi_mod.us_band(report.current.us_aqi)
        eu_band = aqi_mod.eu_band(report.current.european_aqi)
        c1, c2 = st.columns(2)
        c1.metric("US AQI", report.current.us_aqi if report.current.us_aqi is not None else "—",
                  us_band.category)
        c2.metric("European AQI", report.current.european_aqi if report.current.european_aqi is not None else "—",
                  eu_band.category)
        st.caption("US and European AQI are shown separately — they are "
                   "different scales and are never mixed into the Indian AQI.")

    # Pollutant cards — 3x3 grid so every row is even (the old 4-column
    # layout left the fourth column one card taller than the rest).
    st.subheader("Pollutants (µg/m³)")
    current = report.current
    # Columns fill top-to-bottom, so the cards are arranged for rows to
    # read PM2.5 / PM10 / NO2, then O3 / SO2 / CO, then Dust / NH3 / Pb.
    cols = st.columns(3)
    with cols[0]:
        pollutant_card("PM2.5", current.pm2_5, "µg/m³", conf["pm2_5"])
        pollutant_card("O3", current.ozone, "µg/m³", conf["ozone"])
        pollutant_card("Dust", current.dust, "µg/m³", conf["dust"])
    with cols[1]:
        pollutant_card("PM10", current.pm10, "µg/m³", conf["pm10"])
        pollutant_card("SO2", current.sulphur_dioxide, "µg/m³", conf["sulphur_dioxide"])
        st.metric("NH3", "not available",
                  help="Ammonia is not provided by Open-Meteo — never invented.")
    with cols[2]:
        pollutant_card("NO2", current.nitrogen_dioxide, "µg/m³", conf["nitrogen_dioxide"])
        pollutant_card("CO", current.carbon_monoxide, "µg/m³", conf["carbon_monoxide"])
        st.metric("Lead (Pb)", "not available",
                  help="Lead is not provided by Open-Meteo — never invented.")
    st.caption("CO is converted from µg/m³ to mg/m³ (÷1000) before the CPCB "
               "breakpoints are applied.")

    # Sub-index chart + table — WHY the AQI is what it is
    if indian.available and indian.sub_indices:
        st.subheader("Why is the AQI this value? Sub-index per pollutant")
        st.plotly_chart(sub_index_chart(indian), width="stretch",
                        config=PLOTLY_CONFIG)
        rows = []
        for key, sub in sorted(indian.sub_indices.items(),
                               key=lambda item: -item[1]):
            mean = indian.means.get(key)
            hours = indian.hours_used.get(key, 0)
            rows.append({"Pollutant": pollutant_label(key),
                         "Averaged value": (f"{mean:.1f}" if mean is not None else "—"),
                         "Hours used": hours,
                         "Sub-index": sub,
                         "Dominant": "Yes" if key == indian.dominant else ""})
        st.table(rows)

    # Weather
    st.subheader("Weather")
    weather = report.weather
    w1, w2, w3, w4 = st.columns(4)
    w1.metric("Temperature", f"{weather.temperature_c:.0f}°C" if weather.temperature_c is not None else "—")
    w2.metric("Humidity", f"{weather.humidity_pct:.0f}%" if weather.humidity_pct is not None else "—")
    w3.metric("Wind", f"{weather.wind_kmh:.0f} km/h {weather.wind_compass()}" if weather.wind_kmh is not None else "—")
    code_label = WEATHER_CODE_LABELS.get(weather.weather_code or -1, "—")
    w4.metric("Conditions", code_label)
    if weather.precipitation_mm:
        st.caption(f"Precipitation: {weather.precipitation_mm} mm — rain "
                   "usually washes particles out of the air.")
    st.caption("Weather–pollution link: still air traps pollution near the "
               "ground; wind disperses it; rain washes particles out.")

    # Health advisory
    st.subheader("Health advisory")
    if value is not None:
        if value > 300:
            st.error("Very poor / severe air — everyone should limit outdoor "
                     "time; sensitive groups should stay indoors. Wear a "
                     "fitted N95/FFP2 mask for essential trips.")
        elif value > 200:
            st.warning("Poor air — limit long outdoor exertion; sensitive "
                       "groups should stay indoors as much as possible.")
        elif value > 100:
            st.info("Moderate air — sensitive groups should shorten outdoor "
                    "exertion; others can carry on normally.")
        else:
            st.success("Air is in a good range — enjoy outdoor time, and "
                       "prefer quieter streets.")
    st.caption(L("health_disclaimer"))

    # Smart Morning Briefing
    st.subheader("Smart Morning Briefing")
    briefing = morning_briefing(report, st.session_state["profile"])
    st.write(f"**{briefing['headline']}**")
    st.write(f"Weather: {briefing['weather']}")
    if briefing["timing"]:
        st.write(briefing["timing"])
    st.write(f"Top of today's plan: {briefing['routine']}")
    voice_lang = st.selectbox("Listen to the briefing", list(VOICE_LANGUAGES),
                              key="briefing_voice_lang")
    if st.button("Play briefing audio", key="briefing_voice_go"):
        audio = speak(briefing_script(briefing, VOICE_LANGUAGES[voice_lang]),
                      VOICE_LANGUAGES[voice_lang])
        if audio:
            st.audio(audio, format="audio/mp3")
        else:
            st.info("Voice audio is unavailable right now (it needs "
                    "internet for the free text-to-speech service). The "
                    "briefing text above is the full version.")

    # Alerts (compact)
    st.subheader("Alerts")
    alerts = build_alerts(report, st.session_state["profile"])
    for alert in alerts[:4]:
        icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(alert.severity, "ℹ️")
        st.write(f"{icon} **{alert.title}** — {alert.message} {alert.action}")

    # Hourly chart + 5-day trend
    st.subheader("Today's hourly forecast")
    today = report.today_hours()
    if today:
        st.plotly_chart(aqi_chart(today, "PM2.5 and indicative Indian AQI today (IST)"),
                        width="stretch", config=PLOTLY_CONFIG)
    best = report.best_hour_today()
    worst = report.worst_hour_today()
    b1, b2 = st.columns(2)
    if best is not None and best.primary_aqi is not None:
        b1.success(f"Best hour today: {hour_label(best.time)} "
                   f"(AQI {best.primary_aqi:g})")
    if worst is not None and worst.primary_aqi is not None:
        b2.warning(f"Worst hour today: {hour_label(worst.time)} "
                   f"(AQI {worst.primary_aqi:g})")

    st.subheader("5-day trend (max indicative Indian AQI per day)")
    trend = report.daily_trend()
    if trend:
        trend_values = [(ind if ind is not None else us)
                        for _, us, _, ind in trend]
        day_labels = [day_label(day) for day, _, _, _ in trend]
        fig = px.bar(
            x=day_labels,
            y=trend_values,
            labels={"x": "Day", "y": "Max AQI"},
            color=[indian_category_for(v)[0] for v in trend_values],
            color_discrete_map=CPCB_DISCRETE_COLOURS,
            # Discrete colour groups re-order the x-axis unless pinned:
            # keep the days chronological.
            category_orders={"x": day_labels})
        fig.update_layout(height=320, showlegend=True,
                          legend=dict(title="CPCB band"))
        # Value labels on top of each bar, with headroom so the
        # tallest label is never clipped.
        top = max((v for v in trend_values if v is not None),
                  default=0)
        if top > 0:
            fig.update_yaxes(range=[0, top * 1.15])
        fig.update_traces(texttemplate="%{y:.0f}",
                          textposition="outside",
                          textfont=dict(size=12, color="#1F2937"))
        st.plotly_chart(theme_fig(fig, legend_below=True),
                        width="stretch", config=PLOTLY_CONFIG)

    st.subheader("Data confidence")
    # A clean table, not a raw JSON dict — same data, readable labels.
    st.table([{"Data": pollutant_label(key), "Status": status}
              for key, status in conf.items()])
    st.caption("modelled = Open-Meteo CAMS value · estimated = calculated "
               "in-app from modelled data · missing = not available · "
               "sample = offline fallback values.")
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 2 — My Locations (Module 2)
# ---------------------------------------------------------------------------


def page_locations() -> None:
    st.title(L("nav_locations"))
    sample_banner(report)
    store = get_store()
    st.caption("Favourites, recent cities and saved locations are stored in "
               "a local SQLite file (with a session fallback). On Streamlit "
               "Community Cloud the filesystem is ephemeral, so saved data "
               "may reset when the app sleeps or reboots.")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Favourite cities")
        favs = store.favourites()
        if not favs:
            st.write("No favourites yet. Add the current city below.")
        for fav in favs:
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{fav['name']}**")
            if c2.button("Open", key=f"fav_open_{fav['name']}"):
                set_city(fav["name"], fav["lat"], fav["lon"])
                st.rerun()
            if c2.button("Remove", key=f"fav_rm_{fav['name']}"):
                store.remove_favourite(fav["name"])
                st.rerun()
        city = st.session_state["city"]
        if st.button(f"Add {city['name']} to favourites", key="fav_add"):
            store.add_favourite(city)
            st.rerun()

        st.subheader("Recently searched")
        for recent in store.recent_cities():
            if st.button(f"{recent['name']}", key=f"recent_{recent['name']}"):
                set_city(recent["name"], recent["lat"], recent["lon"])
                st.rerun()
    with col_b:
        st.subheader("Multiple location tracking — Home, Office, School")
        locs = store.locations()
        for label in ("Home", "Office", "School"):
            saved = locs.get(label)
            st.write(f"**{label}:** {saved['name'] if saved else 'not set'}")
            options = ["—"] + list(QUICK_CITIES)
            picked = st.selectbox(f"Set {label} to", options,
                                  key=f"loc_{label}")
            if picked != "—" and st.button(f"Save {label}", key=f"loc_save_{label}"):
                lat, lon, _ = QUICK_CITIES[picked]
                store.set_location(label, {"name": picked, "lat": lat, "lon": lon})
                st.rerun()
        if locs:
            st.subheader("Air at your saved locations")
            for label, saved in locs.items():
                loc_report = load_report(saved["name"], saved["lat"], saved["lon"])
                value, scale, category = loc_report.primary_aqi()
                st.write(f"**{label} — {saved['name']}:** "
                         f"{scale} {value:g} ({category})" if value is not None
                         else f"**{label} — {saved['name']}:** no reading")

    st.subheader("Travel destination check")
    dest = st.selectbox("Check the air before you travel", list(QUICK_CITIES),
                        key="travel_dest")
    if st.button("Check destination", key="travel_go"):
        lat, lon, _ = QUICK_CITIES[dest]
        dest_report = load_report(dest, lat, lon)
        value, scale, category = dest_report.primary_aqi()
        best = dest_report.best_hour_today()
        st.write(f"**{dest}:** {scale} {value:g} ({category})"
                 if value is not None else f"**{dest}:** no reading")
        if best is not None and best.primary_aqi is not None:
            st.write(f"Cleanest hour there today: {hour_label(best.time)} "
                     f"(AQI {best.primary_aqi:g}).")
        if not dest_report.is_live:
            st.warning("Sample data — live data unavailable for this city "
                       "right now.")
    st.caption("Tip: you can also enter latitude/longitude directly by "
               "searching a city name in the sidebar — the app resolves it "
               "through the geocoding API.")


# ---------------------------------------------------------------------------
# Page 3 — Forecast & Predictor (Module 3)
# ---------------------------------------------------------------------------


def page_forecast() -> None:
    st.title(L("nav_forecast"))
    sample_banner(report)
    st.subheader("Hourly forecast (IST)")
    today = report.today_hours()
    if today:
        st.plotly_chart(aqi_chart(today, "PM2.5 and indicative Indian AQI (IST)"),
                        width="stretch", config=PLOTLY_CONFIG)
        rows = [{"Hour": p.time[11:16],
                 "Indian AQI*": (f"{p.indian_aqi:g}"
                                 if p.indian_aqi is not None else "—"),
                 "US AQI": (f"{p.us_aqi:g}"
                            if p.us_aqi is not None else "—"),
                 "PM2.5": (f"{p.pm2_5:.1f}"
                           if p.pm2_5 is not None else "—"),
                 "PM10": (f"{p.pm10:.1f}"
                          if p.pm10 is not None else "—")} for p in today]
        st.table(rows)
        st.caption("* Indicative single-hour Indian AQI — a single hour's "
                   "concentrations standing in for the CPCB means. The "
                   "official-style calculation on the Home page uses 24-hr "
                   "and 8-hr means.")
    best = report.best_hour_today()
    worst = report.worst_hour_today()
    if best is not None and best.primary_aqi is not None:
        st.success(f"Best outdoor hour today: {hour_label(best.time)} "
                   f"(AQI {best.primary_aqi:g})")
    if worst is not None and worst.primary_aqi is not None:
        st.warning(f"Worst outdoor hour today: {hour_label(worst.time)} "
                   f"(AQI {worst.primary_aqi:g})")

    st.subheader("5-day pollution trend")
    trend = report.daily_trend()
    if trend:
        trend_values = [(ind if ind is not None else us)
                        for _, us, _, ind in trend]
        day_labels = [day_label(day) for day, _, _, _ in trend]
        fig = px.bar(
            x=day_labels,
            y=trend_values,
            labels={"x": "Day", "y": "Max AQI"},
            color=[indian_category_for(v)[0] for v in trend_values],
            color_discrete_map=CPCB_DISCRETE_COLOURS,
            # Discrete colour groups re-order the x-axis unless pinned:
            # keep the days chronological.
            category_orders={"x": day_labels})
        fig.update_layout(height=320, showlegend=True,
                          legend=dict(title="CPCB band"))
        # Value labels on top of each bar, with headroom so the
        # tallest label is never clipped.
        top = max((v for v in trend_values if v is not None),
                  default=0)
        if top > 0:
            fig.update_yaxes(range=[0, top * 1.15])
        fig.update_traces(texttemplate="%{y:.0f}",
                          textposition="outside",
                          textfont=dict(size=12, color="#1F2937"))
        st.plotly_chart(theme_fig(fig, legend_below=True),
                        width="stretch", config=PLOTLY_CONFIG)
        st.table([{"Day": day_label(day),
                   "Max US AQI": (f"{us:g}" if us is not None else "—"),
                   "Mean PM2.5": (f"{pm:.1f}" if pm is not None else "—"),
                   "Max Indian AQI*": (f"{ind:g}" if ind is not None else "—")}
                  for day, us, pm, ind in trend])

    st.subheader("AI Pollution Predictor")
    st.caption(PREDICTOR_NOTE)
    spikes = detect_spikes(report)
    if spikes:
        for spike in spikes:
            st.warning(f"**{spike.day}:** forecast AQI {spike.aqi:g} "
                       f"({spike.category}), up {spike.rise_pct:.0f}% on the "
                       f"previous day. {spike.advice}")
    else:
        st.write("No sharp pollution spikes are forecast in the next 5 days.")

    st.subheader("Anomaly detection")
    anomalies = detect_anomalies(report)
    if anomalies:
        for anomaly in anomalies:
            st.info(f"**{anomaly.title}** — {anomaly.message}")
    else:
        st.write("No unusual changes vs the recent 24-hour trend.")
    st.caption("Forecast freshness: data time "
               f"{report.current.time or '—'} IST. Forecast values are "
               "modelled estimates and can change as new model runs arrive.")
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 4 — My Routine (Module 4)
# ---------------------------------------------------------------------------


def page_routine() -> None:
    st.title(L("nav_routine"))
    sample_banner(report)
    profile = st.session_state["profile"]
    st.subheader("Your profile")
    with st.form("profile_form"):
        c1, c2 = st.columns(2)
        sensitivity = c1.selectbox(
            "Sensitivity", SENSITIVITIES,
            index=SENSITIVITIES.index(profile.sensitivity))
        commute_mode = c2.selectbox(
            "Commute mode", COMMUTE_MODES,
            index=COMMUTE_MODES.index(profile.commute_mode))
        c3, c4 = st.columns(2)
        commute_km = c3.slider("Commute distance (one way, km)", 0.0, 50.0,
                               float(profile.commute_km), 0.5)
        workplace = c4.selectbox(
            "Workplace", WORKPLACES,
            index=WORKPLACES.index(profile.workplace))
        c5, c6 = st.columns(2)
        household_type = c5.selectbox(
            "Household type", HOUSEHOLD_TYPES,
            index=HOUSEHOLD_TYPES.index(profile.household_type))
        has_purifier = c6.checkbox("I have an air purifier",
                                   value=profile.has_purifier)
        c7, c8 = st.columns(2)
        exercises = c7.checkbox("I exercise outdoors",
                                value=profile.exercises_outdoors)
        exercise_minutes = c8.slider("Exercise minutes", 10, 120,
                                     profile.exercise_minutes, 5)
        notes = st.text_area(
            "Anything else? (optional — treated as preferences only, max 300 chars)",
            value=profile.notes, max_chars=300)
        submitted = st.form_submit_button("Build my plan for today")
    if submitted:
        st.session_state["profile"] = Profile(
            sensitivity=sensitivity, commute_mode=commute_mode,
            commute_km=commute_km, workplace=workplace,
            household_type=household_type, has_purifier=has_purifier,
            exercises_outdoors=exercises, exercise_minutes=exercise_minutes,
            notes=notes)
        profile = st.session_state["profile"]
        plan = build_day_plan(profile, report)
        st.session_state["plan"] = plan
        st.session_state["plan_report_time"] = report.current.time
        try:
            get_store().set_json(
                "saved_routine",
                {"city": report.city.name, "date": date.today().isoformat(),
                 "headline": plan.headline,
                 "items": [{"title": i.title, "action": i.action,
                            "window": i.window, "impact": i.impact}
                           for i in plan.items]})
            get_store().log_history(report.city.name, "routine", plan.headline)
        except Exception:
            pass

    plan = st.session_state.get("plan")
    if plan is None:
        plan = build_day_plan(profile, report)
        st.session_state["plan"] = plan
        st.session_state["plan_report_time"] = report.current.time
    # Dynamic Daily Plan: flag when the forecast has moved on.
    if st.session_state.get("plan_report_time") and \
            st.session_state["plan_report_time"] != report.current.time:
        st.info("The forecast has updated since this plan was built — "
                "press 'Build my plan for today' to refresh it with the "
                "latest data. (Dynamic Daily Plan)")

    st.subheader("Your plan for today")
    st.write(f"**{plan.headline}**")
    for item in plan.items:
        with st.expander(item.title + (f" — {item.window}" if item.window else ""),
                         expanded=False):
            st.write(item.action)
            render_why(item.why_or_default())
    st.subheader("Today's sustainability checklist")
    for entry in plan.checklist:
        st.checkbox(entry, key=f"checklist_{entry}")
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 5 — Activity Planner (Module 5)
# ---------------------------------------------------------------------------


def page_activity() -> None:
    st.title(L("nav_activity"))
    sample_banner(report)
    st.write("Pick an activity and a time — the app answers from today's "
             "hourly forecast.")
    profile = st.session_state["profile"]
    c1, c2 = st.columns(2)
    activity = c1.selectbox("Activity", sorted(ACTIVITIES),
                            key="activity_select")
    hour = c2.slider("Hour of day (IST)", 5, 22, 7, key="activity_hour")
    verdict = assess(activity, hour, profile, report)
    st.subheader(f"{activity} at {hour_label(hour)} — {verdict.verdict}")
    if verdict.aqi_at_hour is not None:
        st.metric(verdict.scale, f"{verdict.aqi_at_hour:g}")
    st.write(verdict.advice)
    if verdict.better_time:
        st.write(f"Cleanest hour today: **{verdict.better_time}**.")
    render_why(verdict.why)
    if verdict.verdict in ("Caution", "Avoid"):
        st.info("Indoor alternative: the same activity indoors — a home "
                "workout, yoga at home, or indoor play — gives the benefit "
                "without the exposure.")
    st.caption(L("health_disclaimer"))
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 6 — Indoor Air (Module 6)
# ---------------------------------------------------------------------------


def page_indoor() -> None:
    st.title(L("nav_indoor"))
    sample_banner(report)
    outdoor_pm25 = report.current.pm2_5 if report.current.pm2_5 is not None else 50.0

    st.subheader("Indoor PM2.5 estimator (ESTIMATE — not a measurement)")
    with st.form("indoor_form"):
        c1, c2 = st.columns(2)
        ventilation = c1.selectbox(
            "Ventilation", ["Windows closed", "Windows cracked / trickle vent",
                            "Windows open"],
            key="indoor_vent")
        purifier_on = c2.checkbox("Purifier running", key="indoor_purifier")
        c3, c4 = st.columns(2)
        cooking = c3.selectbox(
            "Cooking", ["No cooking right now", "Electric / induction cooking",
                        "Gas cooking", "Frying / grilling"], key="indoor_cooking")
        room_size = c4.selectbox(
            "Room size", ["Small (under 150 sq ft)", "Medium (150–400 sq ft)",
                          "Large (over 400 sq ft)"], index=1, key="indoor_room")
        c5, c6 = st.columns(2)
        occupants = c5.slider("People in the room", 1, 8, 2, key="indoor_occ")
        frequency = c6.selectbox(
            "Cooking frequency", ["Once today", "Twice today",
                                  "Three or more times today"], key="indoor_freq")
        smoking = st.checkbox("Someone smokes indoors", key="indoor_smoking")
        go = st.form_submit_button("Estimate indoor PM2.5")
    if go:
        estimate = estimate_indoor_pm25(outdoor_pm25, ventilation, purifier_on,
                                        cooking, room_size, occupants,
                                        frequency, smoking)
        st.metric("Estimated indoor PM2.5",
                  f"{estimate.estimated_pm25:.0f} µg/m³",
                  estimate.risk_category)
        st.write(estimate.summary())
        st.write(estimate.risk_advice)
        current_est, improved_est, reduction = improvement_comparison(
            outdoor_pm25, ventilation, purifier_on, cooking,
            room_size=room_size, occupants=occupants,
            cooking_frequency=frequency, smoking=smoking)
        st.write(f"**Before/after:** windows closed + purifier running "
                 f"would give about {improved_est.estimated_pm25:.0f} µg/m³ — "
                 f"a {reduction:.0f}% reduction from "
                 f"{current_est.estimated_pm25:.0f} µg/m³.")
    st.caption(ASSUMPTIONS_TEXT)

    st.subheader("Ventilation Timing Advisor")
    advice = ventilation_advice(report)
    st.write(f"**{advice['verdict']}**")
    st.write(advice["detail"])

    st.subheader("Room-by-Room Air Planner")
    room = st.selectbox("Room", ROOMS, key="room_select")
    purifier = st.checkbox("Purifier in this room", key="room_purifier")
    plan = room_plan(room, outdoor_pm25, purifier)
    st.write(f"**{room}:** estimated {plan.estimated_pm25:.0f} µg/m³ "
             f"({plan.category})")
    st.write(f"Risk: {plan.risk}")
    st.write(f"Advice: {plan.advice}")

    st.subheader("Cooking Pollution Advisor")
    for title, tip in COOKING_TIPS:
        st.write(f"- **{title}:** {tip}")

    st.subheader("Indoor Pollution Source Checklist")
    for source, note in SOURCE_CHECKLIST:
        st.checkbox(f"{source} — {note}", key=f"source_{source}")

    st.subheader("Home Clean-Air Score")
    v_good = st.checkbox("I ventilate at the cleanest hour", key="score_vent")
    v_pur = st.checkbox("I have a purifier in the main room", key="score_pur")
    v_chim = st.checkbox("I use the chimney every time I cook", key="score_chim")
    v_src = st.checkbox("No incense/coils/smoking indoors", key="score_src")
    v_dust = st.checkbox("I wet-mop or vacuum (no dry sweeping)", key="score_dust")
    score, verdict, improvements = home_clean_air_score(
        v_good, v_pur, v_chim, v_src, v_dust)
    st.metric("Home Clean-Air Score", f"{score}/100", verdict)
    for item in improvements:
        st.write(f"- {item}")
    st.caption("The score reflects habits you report — it is not a measurement.")

    st.subheader("Indoor hacks")
    for title, what, why_this, impact in INDOOR_HACKS:
        with st.expander(title):
            st.write(what)
            st.write(f"**Why this?** {why_this}")
            st.write(f"**What impact?** {impact}")
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 7 — Alternatives & Impact (Module 7)
# ---------------------------------------------------------------------------


def page_alternatives() -> None:
    st.title(L("nav_alternatives"))
    sample_banner(report)
    profile = st.session_state["profile"]
    st.write("Swaps tailored to your commute and city. Each one shows its "
             "estimated CO2 saving and how practical it is locally. All "
             "figures are ESTIMATES with disclosed assumptions — never "
             "measured emissions.")
    swaps = swaps_for(profile.commute_mode, profile.commute_km)
    adopted = st.session_state["adopted"]
    categories: dict[str, list] = {}
    for swap in swaps:
        categories.setdefault(swap.category, []).append(swap)
    for category, items in categories.items():
        st.subheader(category)
        for swap in items:
            checked = st.checkbox(
                f"{swap.title} — {swap.impact}", value=swap.title in adopted,
                key=f"adopt_{swap.title}")
            if checked:
                adopted.add(swap.title)
            else:
                adopted.discard(swap.title)
            with st.expander(f"Why? — {swap.title}"):
                st.write(swap.action)
                st.write(f"**Why this?** {swap.why_or_default()}")
                st.write(f"**Practicality:** {swap.practicality}")
    st.session_state["adopted"] = adopted

    st.subheader("Impact calculator")
    km = st.slider("Daily commute (one way, km)", 0.0, 50.0,
                   float(profile.commute_km), 0.5, key="impact_km")
    mode = st.selectbox("Compare your current mode", COMMUTE_MODES,
                        key="impact_mode")
    rows = compare_modes(km, mode)
    best_mode = lowest_emission_mode(rows)
    st.table([{"Mode": r.mode, "CO2/day (kg)": f"{r.co2_per_day_kg:.2f}",
               "CO2/week (kg)": f"{r.co2_per_week_kg:.2f}",
               "Saving vs current (kg/week)":
                   f"{r.saving_vs_current_kg_week:.2f}",
               "Exposure": r.exposure_level} for r in rows])
    if best_mode is not None:
        st.success(f"Lowest-emission option for this trip: **{best_mode.mode}** "
                   f"({best_mode.co2_per_week_kg} kg CO2/week).")
    st.caption("Emission factors: petrol/diesel car 0.17, auto-rickshaw "
               "0.08, two-wheeler 0.06, bus 0.05, metro 0.03, EV 0.05, "
               "carpool 0.085, cycle/walk/WFH 0 kg CO2 per passenger-km "
               "(typical Indian grid and fleet averages — estimates).")
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 8 — What If Simulator (Module 8)
# ---------------------------------------------------------------------------


def page_whatif() -> None:
    st.title(L("nav_whatif"))
    sample_banner(report)
    profile = st.session_state["profile"]
    st.write("Compare choices side by side, using today's real forecast and "
             "the impact model. Assumptions are shown with every result.")

    st.subheader("What if I change my commute?")
    km = st.slider("Commute distance (one way, km)", 0.0, 50.0,
                   float(profile.commute_km), 0.5, key="whatif_km")
    rows = compare_modes(km, profile.commute_mode)
    st.table([{"Mode": r.mode,
               "CO2/week (kg)": f"{r.co2_per_week_kg:.2f}",
               "Saving vs current (kg/week)":
                   f"{r.saving_vs_current_kg_week:.2f}",
               "Exposure": f"{r.exposure_level} — {r.exposure_note}"}
              for r in rows])

    st.subheader("What if I go out at a different time?")
    c1, c2 = st.columns(2)
    hour_a = c1.slider("First hour", 5, 22, 7, key="whatif_hour_a")
    hour_b = c2.slider("Second hour", 5, 22, 18, key="whatif_hour_b")
    comparison = compare_times(report, hour_a, hour_b)
    st.write(f"**{hour_label(hour_a)}:** AQI "
             f"{comparison.aqi_a:g}" if comparison.aqi_a is not None else
             f"**{hour_label(hour_a)}:** no forecast")
    st.write(f"**{hour_label(hour_b)}:** AQI "
             f"{comparison.aqi_b:g}" if comparison.aqi_b is not None else
             f"**{hour_label(hour_b)}:** no forecast")
    st.write(comparison.recommendation)

    st.subheader("What if I improve cooking ventilation?")
    outdoor_pm25 = report.current.pm2_5 if report.current.pm2_5 is not None else 50.0
    cooking = cooking_ventilation_scenario(outdoor_pm25)
    st.write(f"Without a chimney: about {cooking.without_chimney_pm25:.0f} "
             f"µg/m³ indoors while cooking. With a working chimney: about "
             f"{cooking.with_chimney_pm25:.0f} µg/m³ — a "
             f"{cooking.reduction_pct:.0f}% reduction.")
    st.caption(cooking.note)

    st.subheader("Environmental Impact Score")
    score = impact_score(profile.commute_mode,
                         habits_this_week(st.session_state["habit_log"]),
                         0, 0, len(st.session_state["adopted"]))
    st.metric("Your Impact Score", f"{score.total}/100", grade_for(score.total))
    st.write(f"Commute: {score.commute_points}/30 · Habits: "
             f"{score.habits_points}/30 · Checklist: "
             f"{score.checklist_points}/20 · Adopted swaps: "
             f"{score.swaps_points}/20")
    for suggestion in score.suggestions:
        st.write(f"- {suggestion}")
    series = co2_savings_series(profile.commute_km)
    st.bar_chart(series)
    st.caption("Daily CO2 saving (kg) if this trip switched from a petrol "
               "car to the metro — an estimate, not a measurement.")
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 9 — AI Assistant (Module 9)
# ---------------------------------------------------------------------------


def page_ai() -> None:
    st.title(L("nav_ai"))
    sample_banner(report)
    profile = st.session_state["profile"]
    st.caption(EXPLAINABILITY_TEXT)
    language = st.selectbox("Language", AI_LANGUAGES, key="ai_language")
    api_key = get_api_key()
    if api_key:
        st.caption(f"Gemini connected (free tier). AI calls used this "
                   f"session: {st.session_state['ai_calls']}/"
                   f"{MAX_AI_CALLS_PER_SESSION}.")
    else:
        st.info("No Gemini key configured — the assistant uses the offline "
                "rule-based fallback. To enable Gemini, set GEMINI_API_KEY "
                "as an environment variable or in Streamlit secrets.")

    st.subheader("Personalised advice for today")
    if st.button("Get AI advice", key="ai_advice_go"):
        if api_key and st.session_state["ai_calls"] < MAX_AI_CALLS_PER_SESSION:
            try:
                advice = generate_advice(profile, report, api_key,
                                         language=language)
                st.session_state["ai_calls"] += 1
                st.markdown(advice)
            except Exception as exc:
                st.warning(f"Gemini unavailable ({exc}) — showing the "
                           "offline advice instead.")
                st.markdown(local_advice(profile, report, language))
        else:
            if api_key:
                st.warning("AI call cap reached for this session (5) — "
                           "showing the offline advice instead.")
            st.markdown(local_advice(profile, report, language))
    else:
        st.markdown(local_advice(profile, report, language))

    st.subheader("Ask a follow-up")
    question = st.text_input("Your question", key="ai_question",
                             placeholder="e.g. Can my child play outside at 4 PM?")
    if st.button("Ask", key="ai_ask_go") and question.strip():
        if api_key and st.session_state["ai_calls"] < MAX_AI_CALLS_PER_SESSION:
            try:
                answer = generate_followup(
                    profile, report, st.session_state["chat_history"],
                    question, api_key, language=language)
                st.session_state["ai_calls"] += 1
            except Exception as exc:
                answer = (f"Gemini unavailable ({exc}). Offline answer: "
                          + local_advice(profile, report, language))
        else:
            answer = local_advice(profile, report, language)
        st.session_state["chat_history"].append((question, answer))
    for q, a in st.session_state["chat_history"][-4:]:
        st.write(f"**You:** {q}")
        st.write(a)

    st.subheader("Report Explainer")
    st.write("Upload a pollution report (PDF, TXT or CSV) and get a "
             "plain-language explanation plus a short Hindi summary. "
             "Images need Gemini to read.")
    uploaded = st.file_uploader("Upload a report", type=["pdf", "txt", "csv",
                                                         "png", "jpg", "jpeg"],
                                key="report_upload")
    if uploaded is not None:
        file_bytes = uploaded.read()
        text, note = extract_report_text(file_bytes, uploaded.name)
        st.write(f"File: {uploaded.name} — {note}")
        if note == "image":
            st.info("Images need Gemini to read. Configure a Gemini key to "
                    "explain image reports; text is always available as a "
                    "fallback.")
        elif text:
            if api_key and st.session_state["ai_calls"] < MAX_AI_CALLS_PER_SESSION:
                if st.button("Explain with AI", key="report_explain_go"):
                    try:
                        explanation = generate_report_explanation(
                            text, api_key, language)
                        st.session_state["ai_calls"] += 1
                        st.markdown(explanation)
                    except Exception as exc:
                        st.warning(f"Gemini unavailable ({exc}).")
                        st.markdown(offline_report_summary(text))
            else:
                st.markdown(offline_report_summary(text))
        else:
            st.warning(note)
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 10 — Compare & Map (Module 10)
# ---------------------------------------------------------------------------


def page_compare() -> None:
    st.title(L("nav_compare"))
    sample_banner(report)
    st.write("Compare Indian cities on the SAME scale and the SAME data "
             "time where possible. All values are the latest available "
             "modelled estimates.")
    options = list(QUICK_CITIES)
    chosen = st.multiselect("Cities to compare (2–4)", options,
                            default=["Delhi", "Mumbai", "Bengaluru", "Kolkata"],
                            max_selections=4, key="compare_cities")
    if len(chosen) < 2:
        st.info("Pick at least 2 cities to compare.")
        return
    rows = []
    trend_data = {}
    for name in chosen:
        lat, lon, _ = QUICK_CITIES[name]
        city_report = load_report(name, lat, lon)
        value, scale, category = city_report.primary_aqi()
        best = city_report.best_hour_today()
        rows.append({
            "City": name,
            "Indian AQI*": (city_report.indian_aqi.value
                            if city_report.indian_aqi.available else "—"),
            "US AQI": (city_report.current.us_aqi
                       if city_report.current.us_aqi is not None else "—"),
            "PM2.5": (f"{city_report.current.pm2_5:.1f}"
                      if city_report.current.pm2_5 is not None else "—"),
            "PM10": (f"{city_report.current.pm10:.1f}"
                     if city_report.current.pm10 is not None else "—"),
            "Dominant": (pollutant_label(city_report.indian_aqi.dominant)
                         if city_report.indian_aqi.dominant else "—"),
            "Cleanest hour": hour_label(best.time) if best else "—",
            "Data time": city_report.current.time,
            "Live": "yes" if city_report.is_live else "sample",
        })
        trend_data[name] = city_report.daily_trend()
    st.table(rows)
    st.caption("* Calculated Indian AQI (CPCB method) from modelled data — "
               "not a CPCB station reading.")
    ranked = [r for r in rows if isinstance(r["Indian AQI*"], int)]
    if ranked:
        cleanest = min(ranked, key=lambda r: r["Indian AQI*"])
        st.success(f"Cleanest of these cities right now: **{cleanest['City']}** "
                   f"(Indian AQI {cleanest['Indian AQI*']}).")

    st.subheader("Pollution map of India")
    st.caption("City-level modelled values, clearly labelled — NOT station "
               "data. Each marker is the calculated Indian AQI for that city.")
    if st.button("Load map & ranking (fetches the 10 quick cities)",
                 key="map_load"):
        with st.spinner("Fetching 10 cities…"):
            map_rows = []
            for name, (lat, lon, _) in QUICK_CITIES.items():
                city_report = load_report(name, lat, lon)
                indian = city_report.indian_aqi
                map_rows.append({
                    "city": name, "lat": lat, "lon": lon,
                    "aqi": indian.value if indian.available else None,
                    "category": indian.category if indian.available else "—",
                })
        import pandas as pd
        df = pd.DataFrame([r for r in map_rows if r["aqi"] is not None])
        if not df.empty:
            fig = px.scatter_geo(
                df, lat="lat", lon="lon", color="aqi", size="aqi",
                hover_name="city", hover_data={"category": True, "aqi": True},
                color_continuous_scale=CPCB_COLORSCALE, range_color=[0, 500],
                scope="asia",
                title="Calculated Indian AQI by city (modelled data)")
            fig.update_geos(center=dict(lat=22.0, lon=79.0),
                            projection_scale=4.5, showland=True,
                            landcolor="#EAF7F0", showocean=True,
                            oceancolor="#DFF2F7", showcountries=True,
                            countrycolor="#C9EBD9", showcoastlines=True,
                            coastlinecolor="#C9EBD9")
            fig.update_layout(height=480)
            fig.update_coloraxes(colorbar=dict(title="Indian AQI",
                                               tickvals=[25, 75, 150, 250,
                                                         350, 450],
                                               ticktext=["Good", "Satisfactory",
                                                         "Moderate", "Poor",
                                                         "Very Poor", "Severe"]))
            st.plotly_chart(theme_fig(fig), width="stretch",
                          config=PLOTLY_CONFIG)
        st.subheader("City Clean-Air Ranking")
        ranked_all = sorted(map_rows, key=lambda r: (r["aqi"] is None,
                                                     r["aqi"] or 0))
        st.table([{"Rank": i + 1, "City": r["city"],
                   "Indian AQI": r["aqi"] if r["aqi"] is not None else "—",
                   "Category": r["category"]}
                  for i, r in enumerate(ranked_all)])
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 11 — Alerts (Module 11)
# ---------------------------------------------------------------------------


def page_alerts() -> None:
    st.title(L("nav_alerts"))
    sample_banner(report)
    st.write("In-app alerts only — nothing is sent anywhere, and there are "
             "no push notifications.")
    alerts = build_alerts(report, st.session_state["profile"])
    for alert in alerts:
        icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(
            alert.severity, "ℹ️")
        if alert.severity == "critical":
            st.error(f"{icon} **{alert.title}** — {alert.message} {alert.action}")
        elif alert.severity == "warning":
            st.warning(f"{icon} **{alert.title}** — {alert.message} {alert.action}")
        else:
            st.info(f"{icon} **{alert.title}** — {alert.message} {alert.action}")
    st.subheader("Forecast-based warnings")
    spikes = detect_spikes(report)
    if spikes:
        for spike in spikes:
            st.warning(f"**{spike.day}:** forecast AQI {spike.aqi:g} "
                       f"({spike.category}), up {spike.rise_pct:.0f}% on the "
                       f"previous day.")
    else:
        st.write("No forecast-based warnings for the next 5 days.")
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 12 — Family & Household (Module 12)
# ---------------------------------------------------------------------------


def page_family() -> None:
    st.title(L("nav_family"))
    sample_banner(report)
    st.subheader("Family profiles")
    st.caption("Guidance is conservative and NON-diagnostic — it adapts the "
               "same public AQI guidance to each member's sensitivity.")
    with st.form("member_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Member name", key="member_name")
        role = c2.selectbox("Role", ROLES, key="member_role")
        add = st.form_submit_button("Add member")
    if add and name.strip():
        st.session_state["members"].append(
            Member(name=name.strip(), role=role))
    members = st.session_state["members"]
    if not members:
        st.write("No family members added yet — add one above, or use the "
                 "default household below.")
        members = [Member(name="You", role="General adult")]
    for guidance in household_summary(members, report):
        st.write(f"**{guidance.member.name} ({guidance.member.role})** — "
                 f"{guidance.outdoor_verdict}")
        st.write(guidance.guidance)
    if st.session_state["members"] and st.button("Clear all members",
                                                 key="members_clear"):
        st.session_state["members"] = []
        st.rerun()

    st.subheader("7-Day Clean Air Challenge")
    st.write("One task a day, for the whole household. Tick each day off "
             "as you complete it.")
    tasks = [
        "Day 1: Check the AQI before leaving home",
        "Day 2: Take the metro or bus instead of the car",
        "Day 3: Ventilate at the cleanest hour",
        "Day 4: Cook with the chimney on, lids on",
        "Day 5: Walk or cycle for a short trip",
        "Day 6: Wet-mop the home instead of dry sweeping",
        "Day 7: Share one clean-air tip with a neighbour",
    ]
    done_days = []
    for i, task in enumerate(tasks, start=1):
        if st.checkbox(task, value=i in st.session_state["challenge_days"],
                       key=f"challenge_{i}"):
            done_days.append(i)
    st.session_state["challenge_days"] = done_days
    progress = challenge_progress(done_days)
    st.progress(progress["days_done"] / progress["days_total"])
    if progress["complete"]:
        st.success("Challenge complete — 7/7 days done! 🎉")
    else:
        st.write(f"{progress['days_done']}/7 days done "
                 f"({progress['percent']}%) — next: day "
                 f"{progress['next_day']}.")

    st.subheader("Habit tracker")
    today = date.today().isoformat()
    log = st.session_state["habit_log"]
    todays = log.get(today, [])
    for habit in HABITS:
        if st.checkbox(habit, value=habit in todays, key=f"habit_{habit}"):
            if habit not in todays:
                todays.append(habit)
        elif habit in todays:
            todays.remove(habit)
    log[today] = todays
    st.session_state["habit_log"] = log
    st.write(f"Streak: **{streak_days(log)}** day(s) · Total habits logged: "
             f"**{total_habits(log)}** · This week: "
             f"**{habits_this_week(log)}**")

    st.subheader("Achievement badges")
    for name, description, earned in badges_earned(log):
        st.write(f"{'🏅' if earned else '○'} **{name}** — {description}")

    st.subheader("Personal goal")
    goal = st.slider("Weekly CO2 saving target (kg)", 0.0, 30.0,
                     float(st.session_state["goal_kg"]), 0.5, key="goal_slider")
    st.session_state["goal_kg"] = goal
    weekly_saving = weekly_co2_saving_kg(
        st.session_state["profile"].commute_km)
    pct = goal_progress(goal, weekly_saving)
    st.write(f"Estimated saving if this trip switched car → metro: "
             f"{weekly_saving} kg/week — {pct:.0f}% of your {goal:g} kg "
             f"target." + (" 🎉 Goal reached!" if pct >= 100 else ""))

    st.subheader("Weekly progress report")
    st.text(weekly_report_text(log, f"Week of {date.today().isoformat()}"))

    st.subheader("Family Clean-Air Calendar")
    st.table([
        {"Day": "Monday", "Task": "Check the week's forecast together"},
        {"Day": "Tuesday", "Task": "Wet-mop floors and wipe surfaces"},
        {"Day": "Wednesday", "Task": "Clean the chimney filter (monthly)"},
        {"Day": "Thursday", "Task": "Wash curtains / bedding (dust control)"},
        {"Day": "Friday", "Task": "Check the purifier filter indicator"},
        {"Day": "Saturday", "Task": "Family walk in the cleanest hour"},
        {"Day": "Sunday", "Task": "Review the week's habits and badges"},
    ])

    st.subheader("School Air Safety Planner")
    plan = school_plan(report)
    st.write(f"**Today:** {plan.scale} {plan.aqi:g} ({plan.category})"
             if plan.aqi is not None else "**Today:** no reading")
    st.write(f"Assembly: {plan.assembly}")
    st.write(f"Sports: {plan.sports}")
    if plan.best_window:
        st.write(f"Best window for outdoor school activities: {plan.best_window}")
    st.write(f"**Parent summary (copy-ready):** {plan.parent_summary}")
    st.write("School awareness checklist:")
    for item in SCHOOL_CHECKLIST:
        st.checkbox(item, key=f"school_{item[:40]}")

    st.subheader("Festival Environmental Guide")
    for festival in FESTIVALS:
        with st.expander(f"{festival.name} ({festival.when})"):
            for idea in festival.ideas:
                st.write(f"- {idea}")
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 13 — Mask & Purifier Guide (Module 13)
# ---------------------------------------------------------------------------


def page_equipment() -> None:
    st.title(L("nav_equipment"))
    st.caption("EDUCATIONAL guide, not a medical prescription. If you have "
               "breathing difficulty, seek medical care promptly.")
    for title, body in EQUIPMENT_GUIDE:
        with st.expander(title, expanded=True):
            st.write(body)
    st.subheader("When is a mask useful?")
    value, scale, category = report.primary_aqi()
    if value is not None:
        st.write(f"Today's {scale} is {value:g} ({category}) in "
                 f"{report.city.name}.")
        if value > 200:
            st.warning("At this level, a well-fitting N95/FFP2 mask is "
                       "advised for any time outdoors.")
        elif value > 100:
            st.info("At this level, sensitive groups should wear an "
                    "N95/FFP2 mask outdoors; others may choose to.")
        else:
            st.success("At this level, a mask is not generally needed "
                       "outdoors.")
    st.subheader("Room-size quick check")
    room_m2 = st.slider("Room size (m²)", 5, 60, 20, key="room_m2")
    st.write(f"For a {room_m2} m² room (about {room_m2 * 2.7:.0f} m³ at a "
             f"2.7 m ceiling), look for a purifier rated for at least "
             f"{room_m2} m² — and check the CADR on the box, not just the "
             "marketing claim.")
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 14 — Awareness (Module 14)
# ---------------------------------------------------------------------------


def page_awareness() -> None:
    st.title(L("nav_awareness"))
    sample_banner(report)
    st.subheader("Diwali Pollution Mode")
    st.write(DIWALI_NOTE)
    for phase, tips in DIWALI_PHASES.items():
        with st.expander(phase):
            for tip in tips:
                st.write(f"- {tip}")

    st.subheader("Stubble Burning Awareness")
    st.write(STUBBLE_INFO["what"])
    st.write(f"**When:** {STUBBLE_INFO['when']}")
    for tip in STUBBLE_INFO["what_to_do"]:
        st.write(f"- {tip}")
    st.caption(STUBBLE_INFO["note"])

    st.subheader("Construction Dust")
    st.write(CONSTRUCTION_INFO["what"])
    for tip in CONSTRUCTION_INFO["precautions"]:
        st.write(f"- {tip}")

    st.subheader("Traffic Pollution Intelligence")
    st.write(TRAFFIC_INFO["note"])
    st.write(f"**Rush hours:** {TRAFFIC_INFO['rush_hours']}")
    for tip in TRAFFIC_INFO["tips"]:
        st.write(f"- {tip}")

    st.subheader("Seasonal Pollution Comparison")
    month = ist_now().month
    analysis = seasonal_analysis(report, month)
    st.write(f"**Current season:** {analysis['season']} "
             f"({analysis['months']})")
    st.write(analysis["pattern"])
    st.write(f"**Advice:** {analysis['advice']}")
    st.write(analysis["today"])
    st.write(analysis["forecast_note"])
    for key, info in SEASONS.items():
        with st.expander(f"{key.replace('_', ' ').title()} ({info['months']})"):
            st.write(info["pattern"])
            st.write(f"**Advice:** {info['advice']}")

    st.subheader("Pollutant Source Education")
    st.write(SOURCES_NOTE)
    for pollutant, sources in SOURCES.items():
        with st.expander(pollutant):
            for source in sources:
                st.write(f"- {source}")

    st.subheader("Indian government resources")
    for name, url, note in GOVERNMENT_RESOURCES:
        st.markdown(f"- [{name}]({url}) — {note}")
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 15 — Community (Module 15)
# ---------------------------------------------------------------------------


def page_community() -> None:
    st.title(L("nav_community"))
    sample_banner(report)
    st.subheader("Community AQI Dashboard (city-level)")
    st.caption("City-level modelled data is the honest basis here — "
               "area-wise readings need station data this app does not use.")
    rows = []
    for name in ["Delhi", "Mumbai", "Bengaluru", "Kolkata", "Chennai",
                 "Hyderabad", "Pune", "Lucknow", "Patna", "Jaipur"]:
        lat, lon, _ = QUICK_CITIES[name]
        city_report = load_report(name, lat, lon)
        indian = city_report.indian_aqi
        rows.append({"City": name,
                     "Indian AQI": indian.value if indian.available else "—",
                     "Category": indian.category if indian.available else "—"})
    st.table(rows)

    st.subheader("Community Challenges (tracked locally)")
    done = st.session_state["community_done"]
    for title, description in COMMUNITY_CHALLENGES:
        checked = st.checkbox(f"**{title}** — {description}",
                              value=title in done, key=f"comm_{title}")
        if checked:
            done.add(title)
        else:
            done.discard(title)
    st.session_state["community_done"] = done

    st.subheader("Report Local Pollution")
    st.caption(REPORT_DISCLAIMER)
    with st.form("pollution_report_form"):
        report_type = st.selectbox("What did you see?", REPORT_TYPES,
                                   key="pr_type")
        location = st.text_input("Location (area / landmark)",
                                 key="pr_location")
        description = st.text_area("What happened? (what, when, how bad)",
                                   key="pr_desc")
        reporter = st.text_input("Your name (optional)", key="pr_name")
        submitted = st.form_submit_button("Generate my report")
    if submitted:
        pollution_report = PollutionReport(
            report_type=report_type, location=location or "Not specified",
            city=report.city.name, date=date.today().isoformat(),
            description=description, reporter=reporter)
        formatted = pollution_report.formatted()
        st.text_area("Your formatted report (copy or download it)",
                     value=formatted, height=280, key="pr_output")
        st.download_button("Download report (.txt)", formatted,
                           file_name="pollution-report.txt",
                           key="pr_download")
        st.info("The app does not send this anywhere — share it with your "
                "municipal corporation, State Pollution Control Board, or "
                "through the CPCB Sameer app.")

    st.subheader("School & College Awareness Mode — Quiz")
    answers = st.session_state["quiz_answers"]
    for i, question in enumerate(QUIZ_QUESTIONS):
        choice = st.radio(question["question"], question["options"],
                          index=answers.get(i, 0), key=f"quiz_{i}")
        answers[i] = question["options"].index(choice)
    st.session_state["quiz_answers"] = answers
    if st.button("Check my answers", key="quiz_check"):
        correct, total, explanations = grade_quiz(answers)
        st.write(f"**Score: {correct}/{total}**")
        for explanation in explanations:
            st.write(f"- {explanation}")
    st.download_button(
        "Download awareness handout (.txt)",
        "SwachhVayu AI — Clean Air Awareness Handout\n\n"
        "1. Check the AQI every morning before going out.\n"
        "2. Plan outdoor time for the cleanest hour of the day.\n"
        "3. Wear a fitted N95/FFP2 mask when the AQI is Poor or worse.\n"
        "4. Use the chimney every time you cook; ventilate at the "
        "cleanest hour.\n"
        "5. Take the metro or bus, walk or cycle for short trips.\n"
        "6. Report garbage burning and uncovered construction dust to "
        "your local authority.\n",
        file_name="clean-air-handout.txt", key="handout_download")

    st.subheader("Community Leaderboard (household-local only)")
    st.caption("Scores for members of THIS household/session only — never a "
               "fake global leaderboard.")
    members = st.session_state["members"]
    if members:
        scores = {}
        for member in members:
            scores[member.name] = st.slider(
                f"{member.name}'s clean-air points this week", 0, 100, 10,
                key=f"lb_{member.name}")
        for rank, name, score in household_leaderboard(scores):
            st.write(f"**{rank}. {name}** — {score} points")
    else:
        st.write("Add family members on the Family & Household page to see "
                 "the household leaderboard.")
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 16 — Analytics (Module 16)
# ---------------------------------------------------------------------------


def page_analytics() -> None:
    st.title(L("nav_analytics"))
    sample_banner(report)
    st.subheader("Historical trends")
    days = st.slider("Days of history", 2, 14, 7, key="hist_days")
    history = fetch_past_days(
        City(name=report.city.name, latitude=report.city.latitude,
             longitude=report.city.longitude), days=days)
    if history:
        import pandas as pd
        df = pd.DataFrame(history, columns=["day", "max_us_aqi", "mean_pm25"])
        st.line_chart(df.set_index("day")[["max_us_aqi", "mean_pm25"]])
        st.table([{"Day": day,
                   "Max US AQI": (f"{aqi:g}" if aqi is not None else "—"),
                   "Mean PM2.5": (f"{pm:.1f}" if pm is not None else "—")}
                  for day, aqi, pm in history])
        st.caption("Historical data from the Open-Meteo Air Quality API "
                   "(past_days) — modelled values, not station readings.")
    else:
        st.info("Live history is unavailable right now — showing locally "
                "stored snapshots instead.")
        snapshots = get_store().snapshots(report.city.name)
        if snapshots:
            st.table(snapshots)
        else:
            st.write("No snapshots stored yet for this city.")

    st.subheader("Locally stored snapshots")
    snapshots = get_store().snapshots(report.city.name)
    if snapshots:
        st.table([{"Day": s["day"], "Indian AQI": s["indian_aqi"],
                   "US AQI": s["us_aqi"],
                   "PM2.5": (f"{s['pm25']:.1f}"
                             if s["pm25"] is not None else "—")}
                  for s in snapshots])
    else:
        st.write("No snapshots yet — each dashboard visit stores one.")

    st.subheader("Pollutant comparison (today, hourly means)")
    today = report.today_hours()
    if today:
        means = {}
        for key in ("pm2_5", "pm10", "nitrogen_dioxide", "ozone",
                    "sulphur_dioxide"):
            values = [getattr(p, key) for p in today
                      if getattr(p, key) is not None]
            means[key] = round(sum(values) / len(values), 1) if values else None
        st.bar_chart({k: v for k, v in means.items() if v is not None})
        st.caption("Mean of today's hourly modelled values (µg/m³). CO is "
                   "excluded here because its scale differs by 1000x.")

    st.subheader("Anomaly detection & data confidence")
    for anomaly in detect_anomalies(report):
        st.info(f"**{anomaly.title}** — {anomaly.message}")
    st.write(report.data_confidence())
    st.subheader("Seasonal analysis")
    analysis = seasonal_analysis(report, ist_now().month)
    st.write(f"**{analysis['season']}** ({analysis['months']}): "
             f"{analysis['pattern']}")
    st.write(f"**Advice:** {analysis['advice']}")
    st.write(analysis["today"])
    st.write(analysis["forecast_note"])
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 17 — My Plan & Reports (Module 17)
# ---------------------------------------------------------------------------


def page_plan() -> None:
    st.title(L("nav_plan"))
    sample_banner(report)
    profile = st.session_state["profile"]
    plan = st.session_state.get("plan")
    if plan is None:
        plan = build_day_plan(profile, report)
        st.session_state["plan"] = plan
    st.subheader("Today's plan")
    st.write(f"**{plan.headline}**")
    for item in plan.items:
        st.write(f"- **{item.title}** — {item.action}")
    st.subheader("Export & share")
    st.download_button("Download Markdown", plan_to_markdown(profile, report, plan),
                       file_name="my-air-quality-plan.md", key="dl_md")
    st.download_button("Download CSV", plan_to_csv(profile, report, plan),
                       file_name="my-air-quality-plan.csv", key="dl_csv")
    try:
        pdf_bytes = plan_to_pdf(profile, report, plan)
        st.download_button("Download PDF", pdf_bytes,
                           file_name="my-air-quality-plan.pdf", key="dl_pdf")
    except Exception as exc:
        st.warning(f"PDF export unavailable: {exc}")
    st.text_area("Share summary (copy-paste ready)",
                 value=share_summary(profile, report, plan),
                 height=120, key="share_text")

    st.subheader("Offline saved routine")
    st.caption("Your last downloaded plan, viewable without internet "
               "(stored locally).")
    saved = get_store().get_json("saved_routine")
    if saved:
        st.write(f"**{saved.get('city')} — {saved.get('date')}**")
        st.write(saved.get("headline", ""))
        for item in saved.get("items", []):
            st.write(f"- **{item['title']}** — {item['action']}")
    else:
        st.write("No saved routine yet — build a plan on the My Routine "
                 "page and it will be saved here automatically.")

    st.subheader("Recommendation history")
    history = get_store().history()
    if history:
        st.table(history)
    else:
        st.write("No history yet — plans you build are logged here.")

    st.subheader("Sustainability progress")
    score = impact_score(profile.commute_mode,
                         habits_this_week(st.session_state["habit_log"]),
                         0, 0, len(st.session_state["adopted"]))
    st.metric("Environmental Impact Score", f"{score.total}/100",
              grade_for(score.total))
    st.text(weekly_report_text(st.session_state["habit_log"],
                               f"Week of {date.today().isoformat()}"))
    source_caption(report)


# ---------------------------------------------------------------------------
# Page 18 — Learn & Digital Twin (Module 18)
# ---------------------------------------------------------------------------


def page_learn() -> None:
    st.title(L("nav_learn"))
    st.subheader("Indian AQI (CPCB / NAQI) explained")
    st.write("The National Air Quality Index (NAQI) is India's official "
             "scale, from the Central Pollution Control Board (CPCB). It "
             "runs 0–500: Good 0–50, Satisfactory 51–100, Moderately "
             "polluted 101–200, Poor 201–300, Very Poor 301–400, Severe "
             "401–500. Each pollutant gets a sub-index from its average "
             "concentration; the overall AQI is the worst sub-index.")
    st.write("SwachhVayu AI calculates this index in-app from Open-Meteo "
             "modelled concentrations using the CPCB method. It is labelled "
             "a CALCULATED value — not a CPCB station reading — because the "
             "app does not integrate live station data (no verified free "
             "CPCB API).")
    st.subheader("Why do apps show different numbers?")
    st.write("Three reasons: (1) different scales — Indian (CPCB), US (EPA) "
             "and European bands differ, and CPCB caps NAQI at 500 while "
             "US-method apps can show much higher numbers for the same air; "
             "(2) different averaging — CPCB uses 24-hour means for most "
             "pollutants, while other apps may use hourly values; (3) "
             "different data — station measurements vs modelled estimates. "
             "SwachhVayu AI shows all three scales, labelled, so you can "
             "compare them honestly.")
    st.subheader("Pollutant health messages")
    for key, band in [("PM2.5", "Fine particles that reach deep into the lungs — the main health driver on most Indian days."),
                      ("PM10", "Coarse dust that irritates eyes, nose and throat; high near construction and dry roads."),
                      ("NO2", "Mainly from vehicle exhaust; irritates airways and worsens asthma."),
                      ("O3", "Forms in sunlight; a summer daytime pollutant that irritates lungs."),
                      ("CO", "From incomplete combustion; reduces oxygen delivery in the blood at high levels."),
                      ("SO2", "From coal and industry; irritates airways, especially for people with asthma.")]:
        st.write(f"- **{key}:** {band}")
    st.subheader("Demo cities")
    for name, use_case in DEMO_CITIES.items():
        st.write(f"- **{name}:** {use_case}")
    st.subheader("Government resources")
    for name, url, note in GOVERNMENT_RESOURCES:
        st.markdown(f"- [{name}]({url}) — {note}")

    st.subheader("Clean Air Digital Twin (EXPERIMENTAL)")
    st.warning(TWIN_LABEL)
    c1, c2 = st.columns(2)
    traffic = c1.slider("Traffic volume change (%)", -30, 30, 0,
                        key="twin_traffic")
    green = c2.slider("More green cover (%)", 0, 30, 0, key="twin_green")
    c3, c4 = st.columns(2)
    household = c3.slider("Household emissions change (%)", -30, 30, 0,
                          key="twin_household")
    metro = c4.slider("Trips shifted to metro/bus (%)", 0, 40, 0,
                      key="twin_metro")
    result = simulate(report, traffic=traffic, green_cover=green,
                      household=household, metro_shift=metro)
    if result is not None:
        st.metric("Simulated AQI", result.simulated_aqi,
                  f"{result.delta:+d} vs today's {result.base_aqi:g}")
        st.write(result.explanation)
        for suggestion in improvement_suggestions(result):
            st.write(f"- {suggestion}")
    with st.expander("Model assumptions (disclosed)"):
        for key, info in SCENARIOS.items():
            st.write(f"- **{info['label']}:** {info['note']}")
    st.caption(L("health_disclaimer"))
    source_caption(report)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

ROUTER = {
    "home": page_home,
    "locations": page_locations,
    "forecast": page_forecast,
    "routine": page_routine,
    "activity": page_activity,
    "indoor": page_indoor,
    "alternatives": page_alternatives,
    "whatif": page_whatif,
    "ai": page_ai,
    "compare": page_compare,
    "alerts": page_alerts,
    "family": page_family,
    "equipment": page_equipment,
    "awareness": page_awareness,
    "community": page_community,
    "analytics": page_analytics,
    "plan": page_plan,
    "learn": page_learn,
}

ROUTER[page]()

# Footer on every page (celebration .pro-footer pattern): data honesty
# note + credit, always visible at the bottom.
st.markdown(
    '<div class="pro-footer">'
    f"<div><b>🌿 {APP_NAME}</b> — Urban Air Quality Assistant for India · "
    "Hack2Skill Virtual: PromptWars — Challenge 6</div>"
    "<div>Data: Open-Meteo Air Quality API (Copernicus CAMS modelled data, "
    "not live sensor data). Indian AQI calculated in-app by the CPCB method "
    "— not a CPCB station reading. Health guidance is general information, "
    "not medical advice.</div>"
    "<div>Free, no login, no account · Built by Bhavana Shah</div>"
    "</div>",
    unsafe_allow_html=True)
