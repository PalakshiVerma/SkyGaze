# SkyGaze 🔭

> A voice-guided stargazing assistant. Eyes on the sky, phone face-down.

You ask out loud — "Where is Jupiter?" — and SkyGaze answers out loud. No bright screens. No menu-hunting in the dark.

## How it works

1. Microphone captures your voice
2. Whisper (local) transcribes it to text
3. Gemma (local LLM) parses the intent
4. Deterministic astronomy code computes the position
5. Text-to-speech speaks the answer back

The LLM never calculates positions — only interprets requests. All core astronomy works offline.

## Quick start (local)

```bash
# 1. Clone the repo
git clone <repo-url>
cd SkyGaze

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the backend
uvicorn api.main:app --reload

# 5. Run the UI (separate terminal)
streamlit run ui/app.py
```

## Prepare for offline use

Before heading outdoors, fetch weather, aurora and TLE data:

```bash
curl -X POST http://localhost:8000/prepare
```

## Project structure

```
SkyGaze/
├── tools/
│   ├── astronomy.py       # Celestial position calculations
│   ├── satellites.py      # TLE + SGP4 satellite tracking
│   └── weather_cache.py   # Reads cached weather/aurora data
├── api/
│   └── main.py            # FastAPI backend
├── ui/
│   └── app.py             # Streamlit frontend
├── cache/                 # Runtime data (weather, aurora, TLEs)
├── tests/                 # Unit and integration tests
├── schemas/               # Intent schema definitions
├── spatial.py             # Degrees → human-readable phrases
├── llm.py                 # Gemma intent parser
├── requirements.txt
└── .env                   # API keys (never commit)
```

## Stack

| Layer | Technology |
|-------|-----------|
| UI | Streamlit |
| Backend | FastAPI |
| Speech-to-text | Whisper (local) |
| LLM intent parsing | Gemma via Ollama (local) |
| Astronomy | astronomy-engine |
| Satellites | sgp4 + TLE data |
| Weather/aurora | SerpApi (cached) |
| TTS | pyttsx3 (offline) + ElevenLabs (optional) |
| Hosting | Render |

## Offline demo

SkyGaze is designed to work with no internet once prepared. Run `POST /prepare` while online to cache weather, aurora and TLE data, then disconnect. Core astronomy, satellite tracking and cached weather all continue to work.
