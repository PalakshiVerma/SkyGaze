# -*- coding: utf-8 -*-
"""
ui/app.py
─────────
SkyGaze Streamlit frontend.

Night-mode stargazing assistant UI. Dark screen, dim red controls,
minimal brightness — keeps your eyes dark-adapted.

Run:
    uvicorn api.main:app --reload --port 8000        (terminal 1)
    streamlit run ui/app.py                          (terminal 2)
"""

import sys
import os
from pathlib import Path

import requests
import streamlit as st

# ── Path so we can import from project root if needed ────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE = os.environ.get("SKYGAZE_API_URL", "http://localhost:8000")

SUPPORTED_OBJECTS = [
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune",
]

QUICK_QUESTIONS = [
    "Where is Jupiter?",
    "Where is the Moon?",
    "Where is Mars?",
    "Where is Saturn?",
    "Is Venus visible?",
    "Is Mars visible tonight?",
    "When does the ISS pass?",
    "Can I see stars tonight?",
]

# ── Page config (must be first Streamlit call) ────────────────────────────────

st.set_page_config(
    page_title="SkyGaze 🔭",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Night-mode CSS ────────────────────────────────────────────────────────────

NIGHT_CSS = """
<style>
/* ── Base ── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #080808 !important;
    color: #cc4444 !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #0d0d0d !important;
    border-right: 1px solid #2a0000;
}
[data-testid="stSidebar"] * { color: #993333 !important; }

/* ── Inputs ── */
input, textarea, select {
    background-color: #110000 !important;
    color: #cc4444 !important;
    border: 1px solid #440000 !important;
    border-radius: 4px !important;
}
input::placeholder { color: #552222 !important; }

/* ── Buttons ── */
button[kind="primary"], button[kind="secondary"] {
    background-color: #1a0000 !important;
    color: #cc4444 !important;
    border: 1px solid #660000 !important;
    border-radius: 6px !important;
    font-size: 0.9rem !important;
}
button:hover {
    background-color: #2a0000 !important;
    border-color: #cc4444 !important;
}

/* ── Metrics / Answer card ── */
[data-testid="stMetric"] {
    background-color: #0d0000 !important;
    border: 1px solid #2a0000 !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
}
[data-testid="stMetricValue"] { color: #ff6666 !important; }
[data-testid="stMetricLabel"] { color: #884444 !important; }

/* ── Dividers ── */
hr { border-color: #2a0000 !important; }

/* ── Number inputs ── */
[data-testid="stNumberInput"] input {
    background-color: #110000 !important;
    color: #cc4444 !important;
}

/* ── Answer card custom ── */
.answer-card {
    background: linear-gradient(135deg, #0d0000 0%, #110808 100%);
    border: 1px solid #440000;
    border-radius: 12px;
    padding: 24px 28px;
    margin: 16px 0;
}
.answer-object {
    font-size: 1.6rem;
    font-weight: 700;
    color: #ff6666;
    margin-bottom: 8px;
    letter-spacing: 0.04em;
}
.answer-sentence {
    font-size: 1.15rem;
    color: #ddbbbb;
    line-height: 1.6;
    margin-bottom: 16px;
}
.answer-meta {
    font-size: 0.82rem;
    color: #664444;
}
.badge-visible {
    display: inline-block;
    background: #0a2a0a;
    color: #44cc44;
    border: 1px solid #1a4a1a;
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.78rem;
    margin-left: 10px;
}
.badge-hidden {
    display: inline-block;
    background: #2a0a0a;
    color: #cc4444;
    border: 1px solid #4a1a1a;
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.78rem;
    margin-left: 10px;
}
.api-error {
    background: #1a0000;
    border: 1px solid #660000;
    border-radius: 8px;
    padding: 14px 18px;
    color: #ff6666;
    font-size: 0.9rem;
}
</style>
"""

st.markdown(NIGHT_CSS, unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────

if "lat" not in st.session_state:
    st.session_state.lat = 28.6139   # default: New Delhi
if "lon" not in st.session_state:
    st.session_state.lon = 77.2090
if "last_answer" not in st.session_state:
    st.session_state.last_answer = None
if "last_question" not in st.session_state:
    st.session_state.last_question = ""
if "question_input" not in st.session_state:
    st.session_state.question_input = ""
if "api_ok" not in st.session_state:
    st.session_state.api_ok = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def check_api() -> bool:
    """Ping the API. Returns True if reachable."""
    try:
        r = requests.get(f"{API_BASE}/", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def call_ask(text: str, lat: float, lon: float) -> dict:
    """POST /ask and return the response dict, or an error dict."""
    try:
        r = requests.post(
            f"{API_BASE}/ask",
            json={"text": text, "lat": lat, "lon": lon},
            timeout=10,
        )
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the SkyGaze API. Make sure the backend is running on port 8000."}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


def call_sky(object_name: str, lat: float, lon: float) -> dict:
    """GET /sky/{object} and return the response dict."""
    try:
        r = requests.get(
            f"{API_BASE}/sky/{object_name.lower()}",
            params={"lat": lat, "lon": lon},
            timeout=10,
        )
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the SkyGaze API."}
    except Exception as e:
        return {"error": str(e)}


def call_health() -> dict:
    """GET /health."""
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        return r.json()
    except Exception:
        return {}


def render_answer_card(answer_data: dict, question: str):
    """Render the spoken answer as a styled card."""
    if not answer_data:
        return

    if "error" in answer_data:
        st.markdown(
            f'<div class="api-error">⚠️ {answer_data["error"]}</div>',
            unsafe_allow_html=True,
        )
        return

    answer_text  = answer_data.get("answer", "")
    intent       = answer_data.get("intent", "")
    obj          = answer_data.get("object", "")

    # Determine display name and visibility from answer text
    is_visible   = obj and "below the horizon" not in answer_text.lower()
    badge        = (
        '<span class="badge-visible">✅ Visible</span>' if is_visible and obj
        else '<span class="badge-hidden">❌ Below horizon</span>' if obj
        else ""
    )

    # Object heading
    obj_heading = obj.capitalize() if obj else "SkyGaze"
    if "moon" in (obj or "").lower():
        obj_heading = "the Moon"

    heading_html = f'<div class="answer-object">🔭 {obj_heading}{badge}</div>'

    # Main sentence
    sentence_html = f'<div class="answer-sentence">{answer_text}</div>'

    # Meta line
    meta = f'Asked: "{question}"'
    if intent and intent != "UNKNOWN":
        meta += f' &nbsp;·&nbsp; Intent: {intent}'
    meta_html = f'<div class="answer-meta">{meta}</div>'

    st.markdown(
        f'<div class="answer-card">{heading_html}{sentence_html}{meta_html}</div>',
        unsafe_allow_html=True,
    )

    # Show numeric values in metrics if it was a sky object lookup
    if intent in ("LOCATE_OBJECT", "CHECK_VISIBILITY") and obj:
        sky = call_sky(obj, st.session_state.lat, st.session_state.lon)
        if "error" not in sky and sky:
            c1, c2, c3 = st.columns(3)
            c1.metric("Azimuth", f"{sky.get('azimuth_deg', '—')}°",
                      sky.get("direction", ""))
            c2.metric("Altitude", f"{sky.get('altitude_deg', '—')}°",
                      sky.get("altitude_phrase", ""))
            c3.metric("Visible", "Yes ✅" if sky.get("is_visible") else "No ❌")


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔭 SkyGaze")
    st.markdown("*Eyes on the sky. Phone face-down.*")
    st.divider()

    # API status
    if st.button("Check API status", use_container_width=True):
        st.session_state.api_ok = check_api()

    if st.session_state.api_ok is True:
        st.success("API online ✅")
    elif st.session_state.api_ok is False:
        st.error("API offline ❌ — run uvicorn")
    else:
        st.caption("Press button to check API status")

    st.divider()

    # Location
    st.markdown("#### 📍 Your location")
    st.caption("Decimal degrees. North/East positive.")

    lat_input = st.number_input(
        "Latitude", min_value=-90.0, max_value=90.0,
        value=float(st.session_state.lat), step=0.0001, format="%.4f",
        key="lat_input",
    )
    lon_input = st.number_input(
        "Longitude", min_value=-180.0, max_value=180.0,
        value=float(st.session_state.lon), step=0.0001, format="%.4f",
        key="lon_input",
    )

    if st.button("Set location", use_container_width=True):
        st.session_state.lat = lat_input
        st.session_state.lon = lon_input
        st.success(f"Location set: {lat_input:.4f}, {lon_input:.4f}")

    # Browser geolocation component
    st.markdown(
        """
        <small style="color:#664444">
        Or use your browser's location:
        </small>
        """,
        unsafe_allow_html=True,
    )
    geo_html = """
    <div style="margin-top:4px">
    <button onclick="
        navigator.geolocation.getCurrentPosition(function(pos){
            var lat = pos.coords.latitude.toFixed(4);
            var lon = pos.coords.longitude.toFixed(4);
            document.getElementById('geo_result').innerText =
                'Got: ' + lat + ', ' + lon + ' — paste above ↑';
        }, function(err){
            document.getElementById('geo_result').innerText =
                'Permission denied. Enter manually.';
        });
    "
    style="background:#1a0000;color:#cc4444;border:1px solid #440000;
           border-radius:6px;padding:6px 14px;cursor:pointer;font-size:0.82rem;">
        📍 Use my location
    </button>
    <p id="geo_result" style="color:#884444;font-size:0.78rem;margin-top:6px;"></p>
    </div>
    """
    st.components.v1.html(geo_html, height=70)

    st.divider()

    # Quick-tap object buttons
    st.markdown("#### ⭐ Quick ask")
    st.caption("Tap any object to locate it instantly")
    for obj in SUPPORTED_OBJECTS:
        if st.button(f"Find {obj}", key=f"quick_{obj}", use_container_width=True):
            question = f"Where is {obj}?"
            result = call_ask(question, st.session_state.lat, st.session_state.lon)
            st.session_state.last_answer   = result
            st.session_state.last_question = question

    st.divider()
    st.markdown(
        "<small style='color:#442222'>SkyGaze v0.1 · Phase 3<br>"
        "Backend: <code style='color:#663333'>localhost:8000</code></small>",
        unsafe_allow_html=True,
    )


# ── Main content ──────────────────────────────────────────────────────────────

st.markdown(
    "<h1 style='color:#cc4444;font-size:2.2rem;margin-bottom:0'>🔭 SkyGaze</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='color:#664444;font-size:1rem;margin-top:4px'>"
    "Ask about anything in the sky. Eyes on the stars, not the screen."
    "</p>",
    unsafe_allow_html=True,
)

st.divider()

# ── Question input ────────────────────────────────────────────────────────────

col_input, col_btn = st.columns([5, 1])

with col_input:
    question = st.text_input(
        label="Ask the sky",
        placeholder='e.g. "Where is Jupiter?" or "Is Mars visible tonight?"',
        label_visibility="collapsed",
        key="question_box",
    )

with col_btn:
    ask_clicked = st.button("Ask →", type="primary", use_container_width=True)

# Submit on button click or Enter key (text_input submits on Enter by default
# when there's only one text input on the page)
if ask_clicked and question.strip():
    with st.spinner("Looking up..."):
        result = call_ask(question.strip(), st.session_state.lat, st.session_state.lon)
    st.session_state.last_answer   = result
    st.session_state.last_question = question.strip()

elif ask_clicked and not question.strip():
    st.warning("Type a question first, e.g. 'Where is Jupiter?'")

# ── Answer card ───────────────────────────────────────────────────────────────

if st.session_state.last_answer:
    st.divider()
    render_answer_card(st.session_state.last_answer, st.session_state.last_question)

# ── Sky at a glance (shown when no question has been asked yet) ───────────────

if not st.session_state.last_answer:
    st.markdown(
        "<h3 style='color:#882222;margin-top:24px'>🌌 Sky at a glance</h3>",
        unsafe_allow_html=True,
    )
    st.caption(
        f"Current sky for lat={st.session_state.lat:.2f}°, "
        f"lon={st.session_state.lon:.2f}° — "
        "visible objects only"
    )

    visible_objects = []
    with st.spinner("Fetching sky positions..."):
        for obj in SUPPORTED_OBJECTS:
            data = call_sky(obj, st.session_state.lat, st.session_state.lon)
            if "error" not in data and data.get("is_visible"):
                visible_objects.append(data)

    if visible_objects:
        cols = st.columns(min(len(visible_objects), 3))
        for i, obj_data in enumerate(visible_objects):
            with cols[i % 3]:
                st.markdown(
                    f"""
                    <div style="background:#0d0000;border:1px solid #2a0000;
                                border-radius:10px;padding:14px;margin-bottom:10px">
                        <div style="color:#ff6666;font-size:1.05rem;font-weight:600">
                            {obj_data['display_name']}
                        </div>
                        <div style="color:#884444;font-size:0.82rem;margin-top:4px">
                            {obj_data['direction'].capitalize()} ·
                            {obj_data['altitude_deg']}° up
                        </div>
                        <div style="color:#553333;font-size:0.76rem;margin-top:2px">
                            Az {obj_data['azimuth_deg']}°
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.markdown(
            "<div style='color:#553333;font-size:0.9rem'>"
            "No planets visible right now from this location. "
            "Try asking about a specific object — it might still be near the horizon."
            "</div>",
            unsafe_allow_html=True,
        )

# ── Current location display (bottom of main) ────────────────────────────────

st.divider()
st.markdown(
    f"<small style='color:#442222'>📍 Observer: "
    f"{st.session_state.lat:.4f}°N, {st.session_state.lon:.4f}°E &nbsp;·&nbsp; "
    f"Update in the sidebar ←</small>",
    unsafe_allow_html=True,
)
