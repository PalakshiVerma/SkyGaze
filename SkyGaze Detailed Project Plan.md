# SkyGaze — Detailed Project Plan

> **What is SkyGaze?**
> A voice-guided stargazing assistant. You ask out loud ("Where is Jupiter?") and it answers out loud ("Jupiter is about 35 degrees above the eastern horizon"). The phone sits face-down with a black screen — your eyes stay dark-adapted and on the sky.
>
> **Core idea:** Astronomy software + a voice interface + a small AI layer. The AI does **not** calculate where planets are — deterministic code does. The AI only understands what you asked and helps phrase the answer.

---

## Project at a Glance

| Phase | Name | Goal | Priority |
|-------|------|------|----------|
| 1 | Foundation & Astronomy Core | Prove the math works | 🔴 Must |
| 2 | Backend API | Wrap astronomy in a clean API | 🔴 Must |
| 3 | Streamlit UI (Text Input) | Working UI, typed questions | 🔴 Must |
| 4 | Voice Input — Whisper STT | Spoken question → text | 🔴 Must |
| 5 | Local LLM Intent Parsing — Gemma | Natural language → tool call | 🔴 Must |
| 6 | Text-to-Speech Output | Full voice round-trip | 🔴 Must |
| 7 | Satellite Tracking — ISS & TLE/SGP4 | ISS pass predictions | 🟡 Should |
| 8 | Online Cache & Offline Mode | Weather/aurora + Wi-Fi-off demo | 🟡 Should |
| 9 | Polish, Deploy & Submission | Public link, video, article | 🔴 Must |

**Deadline:** October 11 — reserve the final 2 days (Oct 9–11) for Phase 9.

---

## Cut Line

If time runs short, cut in this order **before touching Phases 1–6**:

1. ElevenLabs voice upgrade → keep local TTS
2. Phase 7 (satellites)
3. Visibility combining with cached cloud data
4. Render hosting → demo locally instead

Never cut M1–M7. That is the submission.

---

---

## Phase 1 — Foundation & Astronomy Core

### What this phase is about

Before touching AI, voice, or UI, you need to prove the core maths work. This phase is pure Python. You are building the engine that every other phase depends on: given an object name (e.g., "Jupiter"), your location (latitude/longitude), and the current time, output the azimuth (compass direction, 0–360°) and altitude (angle above the horizon, 0–90°).

You also build the spatial converter here — the module that turns raw degree numbers into human-readable phrases like "east-northeast, about 37 degrees up." This is what the voice response will actually say.

**Why first?** If the astronomy numbers are wrong, nothing downstream can save the product. Get this verified against a reference (e.g., Stellarium) before moving on.

---

### Subtasks

#### 1.1 Set up the project structure

Create the folder layout for the whole project now, so every later phase has a home:

```
SkyGaze/
├── tools/
│   ├── astronomy.py
│   ├── satellites.py
│   └── weather_cache.py
├── api/
│   └── main.py
├── cache/
│   └── .gitkeep
├── ui/
│   └── app.py
├── spatial.py
├── llm.py
├── requirements.txt
└── README.md
```

- Initialize a Python virtual environment (`python -m venv .venv`)
- Create `requirements.txt` and add initial dependencies
- Add a `.gitignore` (exclude `__pycache__`, `.venv`, `cache/`)

---

#### 1.2 Install and explore the astronomy library

Choose one of:
- **`astronomy-engine`** — pure Python, well-documented, good for planets and Moon
- **`Skyfield`** — more powerful, also pure Python

Install via pip. Open a scratch script and:
- Import the library
- Print today's date in the library's time format
- Print the Sun's azimuth and altitude for a hardcoded lat/lon (use your own location)
- Confirm the numbers look sane (Sun should be below horizon at night)

---

#### 1.3 Write `tools/astronomy.py`

This is the main astronomy tool. It must support these celestial objects at minimum:

- **Sun, Moon**
- **Planets:** Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune

Function signature to aim for:

```python
def get_position(object_name: str, lat: float, lon: float, time_utc: datetime) -> dict:
    """
    Returns:
      {
        "object": "Jupiter",
        "azimuth_deg": 82.3,
        "altitude_deg": 37.1,
        "is_visible": True   # altitude > 0
      }
    """
```

Subtasks inside this file:
- Map common name strings (e.g., "jupiter", "the moon") to library-specific body constants
- Handle case-insensitive input
- Return `is_visible: False` when altitude ≤ 0 (object is below the horizon)
- Return a clear error for unknown object names

---

#### 1.4 Smoke test against a reference

- Open Stellarium (free, stellarium.org) or any planetarium app
- Set it to your location and current time
- Look up Jupiter, Mars, and the Moon
- Run your `astronomy.py` for the same objects, same time
- Values should match within approximately 1 degree
- Fix any coordinate system issues (azimuth conventions differ between libraries)

---

#### 1.5 Write `spatial.py` — degrees to phrases

This module converts raw numbers into what the voice will say.

Two functions to build:

**`compass_direction(azimuth_deg: float) -> str`**

Maps azimuth to 16-point compass:

| Range | Label |
|-------|-------|
| 348.75 – 11.25 | north |
| 11.25 – 33.75 | north-northeast |
| 33.75 – 56.25 | northeast |
| 56.25 – 78.75 | east-northeast |
| 78.75 – 101.25 | east |
| ... and so on | ... |

**`altitude_phrase(altitude_deg: float) -> str`**

Maps altitude to a natural description:

| Range | Phrase |
|-------|--------|
| ≤ 0 | "below the horizon" |
| 1 – 10 | "very low on the horizon" |
| 11 – 25 | "low in the sky" |
| 26 – 45 | "about a third of the way up" |
| 46 – 65 | "about halfway up the sky" |
| 66 – 80 | "high in the sky" |
| 81 – 90 | "nearly overhead" |

**`describe_position(azimuth_deg: float, altitude_deg: float) -> str`**

Combines both into a single sentence:
> "Jupiter is to the east-northeast, about a third of the way up the sky."

---

#### 1.6 Unit test the spatial converter

Write a test file `tests/test_spatial.py` and cover:
- All 16 compass points with boundary values
- All altitude buckets
- The combined `describe_position` output format
- Edge cases: azimuth = 0.0, azimuth = 360.0, altitude = 0.0, altitude = 90.0

Run tests with `pytest`. All must pass before moving to Phase 2.

---

**Phase 1 complete when:**
- `python tools/astronomy.py` prints a correct, phrase-formatted position for Jupiter
- Values match Stellarium within ~1°
- All spatial unit tests pass

---

---

## Phase 2 — Backend API

### What this phase is about

Wrap the astronomy core in a FastAPI backend. This creates clean, testable URLs that the UI (Phase 3), voice input (Phase 4), and LLM (Phase 5) will all call. FastAPI is chosen because Python is the right language for AI and astronomy libraries, and FastAPI produces fast, well-documented APIs with automatic Swagger UI at `/docs`.

The goal of this phase is to have every astronomy feature accessible via HTTP, even before there's any UI.

---

### Subtasks

#### 2.1 Scaffold `api/main.py`

- Install FastAPI and Uvicorn (`pip install fastapi uvicorn`)
- Create the FastAPI app instance
- Add a root endpoint `GET /` that returns `{"status": "SkyGaze API running"}`
- Start the server: `uvicorn api.main:app --reload`
- Confirm `/docs` loads the Swagger UI in the browser

---

#### 2.2 Add `GET /sky/{object}`

This is the core endpoint.

**Request:** `GET /sky/jupiter?lat=51.5&lon=-0.1`

**Response:**
```json
{
  "object": "jupiter",
  "azimuth_deg": 82.3,
  "altitude_deg": 37.1,
  "is_visible": true,
  "direction": "east-northeast",
  "altitude_phrase": "about a third of the way up the sky",
  "spoken_description": "Jupiter is to the east-northeast, about a third of the way up the sky."
}
```

Subtasks:
- Accept `lat` and `lon` as query parameters
- Use current server time if no time is provided
- Call `astronomy.py` and `spatial.py` from this endpoint
- Return a 404 with a helpful message for unknown objects

---

#### 2.3 Add `POST /ask` (placeholder)

This endpoint will later be wired to the LLM (Phase 5). For now, it accepts raw text and returns a placeholder response.

**Request body:**
```json
{ "text": "Where is Jupiter?", "lat": 51.5, "lon": -0.1 }
```

**Response (placeholder):**
```json
{ "intent": "LOCATE_OBJECT", "object": "jupiter", "answer": "TODO: LLM not yet wired" }
```

This lets the Streamlit UI (Phase 3) start calling something real.

---

#### 2.4 Add `GET /health`

Returns the current state of the system — useful for debugging and the submission write-up.

```json
{
  "status": "ok",
  "online": true,
  "cache_age_minutes": 45,
  "models_loaded": ["whisper", "gemma"]
}
```

For now, `online` can be hardcoded to `true` and `models_loaded` can be an empty list. Fill in properly in later phases.

---

#### 2.5 Manual API testing

- Test all endpoints using the Swagger UI at `/docs`
- Test with `curl` from the command line:
  ```
  curl "http://localhost:8000/sky/jupiter?lat=51.5&lon=-0.1"
  ```
- Confirm error handling works: try unknown objects, missing parameters

---

**Phase 2 complete when:**
- `GET /sky/jupiter` returns correct JSON with azimuth, altitude, and spoken phrase
- `/docs` shows all endpoints with correct schemas
- `/health` returns a valid response

---

---

## Phase 3 — Streamlit UI (Text Input)

### What this phase is about

Build the user interface. Streamlit lets you write a Python script that becomes a web app — fast for demos, requires no JavaScript. The goal here is a working UI where you can **type** a question and get a correct answer. Voice comes in Phase 4.

This phase also establishes the visual style: dark background, minimal brightness, because the user is outdoors at night.

---

### Subtasks

#### 3.1 Scaffold `ui/app.py`

- Install Streamlit (`pip install streamlit`)
- Create the app with a title: "🔭 SkyGaze"
- Add a dark theme by setting Streamlit config or using custom CSS
- Run: `streamlit run ui/app.py`
- Confirm a blank dark page loads

---

#### 3.2 Add location input

The user's location is required for all astronomy calculations.

Options (implement both, let the user choose):
- **Manual entry:** two number inputs for latitude and longitude
- **Browser geolocation:** use `streamlit-javascript` or a Streamlit component to request `navigator.geolocation` from the browser

Store the resolved lat/lon in `st.session_state` so it persists across questions.

---

#### 3.3 Add text input and question submission

- Text input field with placeholder: "Ask about the sky... e.g. Where is Jupiter?"
- Submit button (or press Enter to submit)
- On submit, call `POST /ask` with the text and current lat/lon
- Display the returned `spoken_description` as the answer

---

#### 3.4 Display the answer card

Show the result in a styled card:
- Object name (large)
- Spoken description (e.g., "Jupiter is to the east-northeast…")
- Azimuth and altitude in smaller text
- A "visible / not visible" badge

Example layout:
```
🪐 Jupiter
─────────────────────────────
Jupiter is to the east-northeast,
about a third of the way up the sky.

Azimuth: 82.3°  |  Altitude: 37.1°  |  ✅ Visible
```

---

#### 3.5 Night mode styling

- Black or very dark background (`#0a0a0a`)
- Red or dim amber text for controls (preserves night vision)
- Minimal use of bright whites
- Hide the Streamlit menu bar and footer to reduce clutter

Apply via a `<style>` block injected with `st.markdown(..., unsafe_allow_html=True)`.

---

**Phase 3 complete when:**
- Typing "Where is Mars?" in the browser returns a correct, readable answer
- The UI is dark and usable in a dim environment
- Location is correctly captured and passed to the API

---

---

## Phase 4 — Voice Input (Whisper STT)

### What this phase is about

Replace typing with speaking. Whisper is an open-weight speech-to-text model that runs entirely on your machine — no audio ever leaves the device. The user taps a button, speaks their question, and the audio is transcribed to text which then feeds into the existing `POST /ask` pipeline.

**Important design decision:** use **tap-to-talk**, not always-on listening. Browser microphone access requires a user gesture anyway, and continuous background audio is unreliable in browser contexts.

---

### Subtasks

#### 4.1 Install and test Whisper locally

- Install: `pip install openai-whisper`
- Download a model (start with `base` or `small` for speed): `whisper.load_model("base")`
- Write a quick test script: record a 5-second `.wav` file (use Audacity or any recorder), run Whisper on it, print the transcript
- Confirm "Where is Jupiter?" transcribes correctly in a quiet room

---

#### 4.2 Add `POST /transcribe` to the API

**Request:** multipart form with an audio file (`audio/wav` or `audio/webm`)

**Response:**
```json
{ "transcript": "Where is Jupiter?" }
```

Subtasks:
- Accept the audio file upload in FastAPI
- Save it temporarily (use Python's `tempfile`)
- Run Whisper on it
- Return the transcript
- Delete the temp file after transcription

---

#### 4.3 Add microphone recording in the Streamlit UI

Use `streamlit-webrtc` or `audio-recorder-streamlit` to capture microphone input:

- Show a "🎙 Tap to ask" button
- On tap: start recording
- On release (or second tap): stop recording, send audio to `POST /transcribe`
- Display the transcript in the text field
- Auto-submit to `POST /ask` after transcription

---

#### 4.4 Handle errors gracefully

- Microphone permission denied → show a clear message, fall back to text input
- Audio too short or silent → show "Could not hear you, please try again"
- Whisper timeout (slow device) → show a loading spinner with timeout message

---

#### 4.5 End-to-end voice test

Test the full path:
1. Tap the mic button
2. Say "Where is Mars?"
3. See the transcript appear
4. See the answer appear

Test at least 5 different phrasings. Fix any transcription failures (usually punctuation or capitalization — normalize input before passing to the LLM).

---

**Phase 4 complete when:**
- Spoken "Where is Mars?" is transcribed correctly in a quiet room
- The transcribed text automatically flows into the answer pipeline
- A tap-to-talk fallback works reliably

---

---

## Phase 5 — Local LLM Intent Parsing (Gemma)

### What this phase is about

Right now, `POST /ask` receives raw text like "Find Jupiter for me" and doesn't really know what to do with it. This phase wires in Gemma — a small, open-weight language model — to interpret natural language and produce a **structured intent**.

The LLM's job is deliberately narrow:

> Natural language text in → structured intent out (e.g., `LOCATE_OBJECT(Jupiter)`)

The LLM **never** calculates positions, times, or orbital data. That is always done by the deterministic tools.

---

### Subtasks

#### 5.1 Install Ollama and pull Gemma

- Install Ollama from [ollama.com](https://ollama.com)
- Pull a small Gemma model: `ollama pull gemma:2b` (or `gemma:7b` if memory allows)
- Test from the command line: `ollama run gemma:2b "What is 2+2?"`
- Confirm the model responds

---

#### 5.2 Define the intent schema

Create a fixed list of intents SkyGaze supports. A strict, small list is better than a fuzzy large one:

| Intent | Parameters | Example trigger |
|--------|-----------|-----------------|
| `LOCATE_OBJECT` | `object: str` | "Where is Jupiter?" |
| `CHECK_VISIBILITY` | `object: str` | "Can I see Mars tonight?" |
| `GET_ISS_PASS` | _(none)_ | "When does the ISS pass?" |
| `WEATHER_SUMMARY` | _(none)_ | "Can I see stars tonight?" |
| `UNKNOWN` | _(none)_ | Anything else |

Document this schema in a `schemas/intents.py` file.

---

#### 5.3 Write `llm.py`

Build the LLM wrapper:

```python
def parse_intent(user_text: str) -> dict:
    """
    Sends user_text to Gemma with a structured prompt.
    Returns: { "intent": "LOCATE_OBJECT", "object": "jupiter" }
    """
```

The system prompt should:
- Tell Gemma it is a stargazing assistant
- Show it the exact list of intents and their parameters
- Ask for JSON output only, no extra text
- Give 2–3 examples (few-shot prompting)

Example prompt structure:
```
You are a stargazing assistant. Parse the user's request into one of these intents:
LOCATE_OBJECT(object), CHECK_VISIBILITY(object), GET_ISS_PASS, WEATHER_SUMMARY, UNKNOWN

Return ONLY a JSON object. Examples:
"Where is Jupiter?" → {"intent": "LOCATE_OBJECT", "object": "jupiter"}
"Can I see Venus?" → {"intent": "CHECK_VISIBILITY", "object": "venus"}
"When does the ISS pass?" → {"intent": "GET_ISS_PASS"}

User: "{user_text}"
```

Parse the JSON response carefully — add a fallback to `UNKNOWN` if Gemma returns malformed output.

---

#### 5.4 Wire the tool router in `POST /ask`

Build a tool router that maps intents to tool calls:

```python
def route_intent(intent: dict, lat: float, lon: float) -> dict:
    if intent["intent"] == "LOCATE_OBJECT":
        return astronomy.get_position(intent["object"], lat, lon)
    elif intent["intent"] == "GET_ISS_PASS":
        return satellites.get_next_pass(lat, lon)
    # ... etc
```

Update `POST /ask` to:
1. Call `llm.parse_intent(text)`
2. Call `route_intent(intent, lat, lon)`
3. Call `spatial.describe_position(...)` on the result
4. Return the full response

---

#### 5.5 Build the 20-phrase test set

Create `tests/test_intents.py` with at least 20 varied phrasings:

```python
test_cases = [
    ("Where is Jupiter?", "LOCATE_OBJECT", "jupiter"),
    ("Find Jupiter for me", "LOCATE_OBJECT", "jupiter"),
    ("Show me where Jupiter is", "LOCATE_OBJECT", "jupiter"),
    ("Is Mars visible tonight?", "CHECK_VISIBILITY", "mars"),
    ("Can I see Saturn?", "CHECK_VISIBILITY", "saturn"),
    ("When will the ISS fly over?", "GET_ISS_PASS", None),
    ("Will it be clear tonight?", "WEATHER_SUMMARY", None),
    # ... 13+ more
]
```

Run the test set, measure the pass rate. Target: **90%+**. If Gemma misses common phrasings, refine the system prompt.

---

#### 5.6 Confirm LLM never does maths

Add a check in `llm.py`: if the LLM response contains numbers that look like azimuth or altitude values, log a warning. The LLM output should only be intent + object name — never coordinates.

---

**Phase 5 complete when:**
- 20+ varied phrasings all route to the correct tool call
- `POST /ask` returns a full spoken answer end to end
- LLM output is always structured JSON, never raw coordinates

---

---

## Phase 6 — Text-to-Speech Output (TTS)

### What this phase is about

Close the voice loop. The user speaks a question; SkyGaze speaks the answer. After this phase, the phone can sit face-down on the grass and the whole interaction is audio-only.

**Design rule:** always have a local TTS fallback. ElevenLabs requires internet; the user is often outdoors with no connectivity. Local TTS may sound less natural but must always work.

---

### Subtasks

#### 6.1 Implement local TTS fallback

Two options, implement whichever fits your stack:

**Option A — Browser `speechSynthesis` (simplest):**
- Use Streamlit's `st.components.v1.html` to inject a small JavaScript block that calls `window.speechSynthesis.speak()`
- No Python dependencies
- Works on most modern browsers

**Option B — `pyttsx3` (Python, truly offline):**
- Install: `pip install pyttsx3`
- Runs on Windows (SAPI5), macOS (NSSpeechSynthesizer), Linux (espeak)
- Generates audio on the server, streams back to the browser

Recommended: start with Option A for speed; switch to Option B if browser TTS is too robotic.

---

#### 6.2 Add `POST /speak` to the API (Option B path)

**Request:**
```json
{ "text": "Jupiter is to the east-northeast, about a third of the way up the sky." }
```

**Response:** audio file (`audio/mp3` or `audio/wav`)

Subtasks:
- Generate audio with `pyttsx3` or `gTTS` to a temp file
- Return it as a streaming response
- Play it in the Streamlit UI using `st.audio`

---

#### 6.3 (Optional) Add ElevenLabs as an upgrade

- Sign up for ElevenLabs API key (free tier available)
- Add `ELEVENLABS_API_KEY` to a `.env` file (never commit this)
- In `POST /speak`, check if the key is set and if the system is online
- If yes: use ElevenLabs for natural-sounding voice
- If no: fall back to local TTS

This should be a transparent swap — the rest of the code doesn't change.

---

#### 6.4 Wire TTS into the full pipeline

Update the Streamlit UI:
1. User taps mic → speaks question
2. Audio → `/transcribe` → transcript
3. Transcript → `/ask` → answer text
4. Answer text → `/speak` → audio plays automatically

Add a small visual indicator while audio is playing (e.g., a waveform icon or "Speaking…" text).

---

#### 6.5 Full voice round-trip test

Test the complete loop with no keyboard interaction:
1. Tap mic
2. Say "Where is Jupiter?"
3. Wait ~3–5 seconds
4. Hear the spoken answer

Test with the screen face-down (phone flat on a table). The audio should still play. Measure the approximate end-to-end latency and note it for the write-up.

---

**Phase 6 complete when:**
- Asking "Where is Jupiter?" out loud produces a spoken answer with no typing
- The fallback TTS works with no internet connection
- End-to-end latency is measured and noted

---

---

## Phase 7 — Satellite Tracking (ISS & TLE/SGP4)

### What this phase is about

Add the ability to answer "When does the ISS pass over?" The ISS is the most-requested satellite for casual observers and it's a high-wow-factor demo.

**How it works:**
- **TLE (Two-Line Element set):** two lines of text that describe a satellite's orbit at a specific moment. Think of it as the raw input data.
- **SGP4:** the standard algorithm that takes a TLE and computes where the satellite is at any future time.
- Combined with your lat/lon, you get azimuth and altitude for the ISS at every moment.

TLEs go stale (decay over days), so you fetch fresh ones whenever online and cache them locally.

---

### Subtasks

#### 7.1 Install SGP4 and fetch TLE data

- Install: `pip install sgp4`
- Fetch ISS TLE from CelesTrak: `https://celestrak.org/SOCRATES/query.php` or the simpler `https://celestrak.org/satcat/tle.php?CATNR=25544`
- Save the two-line element set to `cache/iss_tle.txt`
- Print the raw TLE to confirm it looks correct (two lines starting with `1 ` and `2 `)

---

#### 7.2 Write `tools/satellites.py`

```python
def get_next_pass(lat: float, lon: float, satellite_name: str = "ISS") -> dict:
    """
    Returns the next visible pass for a satellite.
    {
      "satellite": "ISS",
      "next_pass_utc": "2026-10-07T22:14:00Z",
      "max_elevation_deg": 62.3,
      "direction_rise": "southwest",
      "direction_set": "northeast",
      "duration_minutes": 6
    }
    """
```

Subtasks:
- Load TLE from cache file
- Use SGP4 to propagate the orbit in 10-second steps
- Find the next window where altitude > 10° (high enough to be visible over trees)
- Return rise/set azimuth as compass directions using `spatial.py`

---

#### 7.3 Add `GET /satellite/{name}/passes` to the API

**Request:** `GET /satellite/iss/passes?lat=51.5&lon=-0.1`

**Response:**
```json
{
  "satellite": "ISS",
  "next_pass_utc": "2026-10-07T22:14:00Z",
  "max_elevation_deg": 62.3,
  "direction_rise": "southwest",
  "direction_set": "northeast",
  "duration_minutes": 6,
  "spoken_description": "The ISS will pass over at 10:14 PM, rising in the southwest and reaching 62 degrees before setting in the northeast. The pass lasts about 6 minutes."
}
```

---

#### 7.4 Wire satellite intent through the LLM router

- Add `GET_ISS_PASS` intent to the test set in `tests/test_intents.py`
- Update `route_intent()` in `POST /ask` to call `satellites.get_next_pass()` for this intent
- Test: ask "When does the ISS fly over?" and hear the spoken pass prediction

---

#### 7.5 Handle TLE staleness

- In `GET /health`, include `tle_age_hours` and a warning if > 48 hours old
- In the `POST /prepare` endpoint (Phase 8), re-fetch TLEs automatically
- If TLE file is missing, return a helpful error: "Satellite data not yet downloaded. Connect to the internet and run /prepare."

---

**Phase 7 complete when:**
- "When does the ISS pass?" returns a correct upcoming pass time and direction
- The spoken description is natural and accurate
- TLE staleness is tracked and reported

---

---

## Phase 8 — Online Cache & Offline Mode

### What this phase is about

SkyGaze's whole story is "works when you're offline in a field." This phase implements the cache system that makes that true, and formally verifies the offline mode works.

**The pattern:**
- While you have internet: fetch weather forecasts, aurora alerts, and fresh TLEs → store in local files
- While offline: read from those files
- Never fetch live data per question

---

### Subtasks

#### 8.1 Write `tools/weather_cache.py`

This module reads from cached files. It does not fetch — fetching is done by `/prepare`.

```python
def get_cloud_forecast(lat: float, lon: float) -> dict:
    """ Reads cached cloud cover data. Returns coverage % and source timestamp. """

def get_aurora_alert() -> dict:
    """ Reads cached aurora Kp index and alert level. """
```

---

#### 8.2 Add `POST /prepare` to the API

This is the "go online and stock up" endpoint. Call it once before going outdoors.

**What it does:**
1. Fetch weather/cloud forecast from SerpApi (or OpenWeatherMap as a free alternative)
2. Fetch aurora Kp index (e.g., from NOAA Space Weather)
3. Fetch fresh ISS TLE from CelesTrak
4. Store all three to the `cache/` directory with timestamps
5. Return a summary of what was fetched

**Response:**
```json
{
  "status": "prepared",
  "weather_cached_at": "2026-10-07T18:30:00Z",
  "aurora_cached_at": "2026-10-07T18:30:00Z",
  "tle_cached_at": "2026-10-07T18:30:00Z"
}
```

Add a "Prepare for tonight" button in the Streamlit UI that calls this endpoint.

---

#### 8.3 Add visibility combining (S3)

This answers "Can I see stars tonight?" by combining:
- Current altitude of the Moon (more moonlight = worse conditions)
- Sun position (is it fully dark? — civil/nautical/astronomical twilight)
- Cached cloud cover percentage

```python
def assess_visibility(lat, lon, cloud_cover_pct, moon_altitude_deg, sun_altitude_deg) -> str:
    """ Returns a natural summary like: "Conditions look good. Cloud cover is 20%, 
        the Moon is low, and it's fully dark." """
```

Wire this to the `CHECK_VISIBILITY` intent when no specific object is named, and to `WEATHER_SUMMARY`.

---

#### 8.4 Update `/health` with cache status

```json
{
  "status": "ok",
  "online": false,
  "weather_cache_age_minutes": 95,
  "tle_cache_age_hours": 2.1,
  "aurora_cache_age_minutes": 95,
  "models_loaded": ["whisper", "gemma"]
}
```

---

#### 8.5 Formal offline test

This is the most important test in the project. Do it in this order:

1. Run `POST /prepare` while connected to Wi-Fi
2. Confirm all three cache files exist in `cache/`
3. **Disconnect Wi-Fi completely** (turn off network adapter)
4. Run the full question pipeline for:
   - "Where is Jupiter?" (astronomy)
   - "Where is the Moon?" (astronomy)
   - "When does the ISS pass?" (satellites + TLE)
   - "Can I see stars tonight?" (weather cache)
5. All four must return correct spoken answers
6. Record this for the demo video

---

**Phase 8 complete when:**
- All four offline test questions answer correctly with Wi-Fi off
- `/health` shows accurate cache ages
- The "Prepare for tonight" button works in the UI

---

---

## Phase 9 — Polish, Deploy & Submission

### What this phase is about

Turn a working project into a polished submission. This phase is reserved for the final 2 days (October 9–11). No new features — only deploy, record, write, and submit.

---

### Subtasks

#### 9.1 Pre-deploy checklist

Before pushing to Render:
- [ ] All secrets in `.env` file, never hardcoded
- [ ] `.env` is in `.gitignore`
- [ ] `requirements.txt` is up to date (`pip freeze > requirements.txt`)
- [ ] `README.md` explains how to run the project locally
- [ ] All `TODO` comments resolved or noted as future work
- [ ] `/health` endpoint returns correct status

---

#### 9.2 Deploy FastAPI to Render

- Create a new Web Service on Render
- Connect GitHub repository
- Set build command: `pip install -r requirements.txt`
- Set start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- Add environment variables (API keys) in Render's dashboard
- **Check memory limits** — if Whisper + Gemma don't fit, set up a lightweight fallback path that skips local models and uses a template-based response

---

#### 9.3 Deploy Streamlit UI to Render (or Streamlit Cloud)

- Create a second Web Service (or use [share.streamlit.io](https://share.streamlit.io))
- Set the API base URL as an environment variable so the UI points to the deployed FastAPI
- Confirm the full flow works on the hosted URL

---

#### 9.4 Record the demo video

The demo video must show:
1. The "Prepare for tonight" button being pressed (online fetch)
2. A spoken question → spoken answer on the hosted URL
3. **Wi-Fi off** (show the network indicator) → spoken question → spoken answer still works
4. The ISS pass prediction (if Phase 7 is complete)
5. A brief screen showing `/health` with cache ages

Keep the video under 3 minutes. Speak slowly and clearly for the offline demo segment.

---

#### 9.5 Write the DEV.to article / submission write-up

Structure:
1. **Hook:** what problem does SkyGaze solve? (Night vision, the dark field, the glowing screen)
2. **Architecture diagram:** show the full pipeline (voice in → Whisper → Gemma → tool router → astronomy → spatial → TTS → voice out)
3. **The offline-first design:** explain the prepare/cache pattern and why it matters
4. **Technology choices:** why each tool was chosen (Gemma, Whisper, Astronomy Engine, SGP4)
5. **Honest limitations:** Streamlit constraints, phone browser limits, model size vs. hosting
6. **What I'd build next:** PWA, on-device inference, constellation overlays

Include the demo video link, the GitHub repo link, and the live demo URL.

---

#### 9.6 Accuracy and latency measurements

For the write-up, include:
- Position accuracy: compare 3 objects against Stellarium, report delta in degrees
- End-to-end latency: time from tap-to-talk release to audio start, measured 5 times, report average
- Intent accuracy: report the test set pass rate (target 90%+)

---

#### 9.7 Final submission

- [ ] Submit via the challenge submission form before midnight October 11
- [ ] Confirm the GitHub repo is public
- [ ] Confirm the live demo URL is accessible
- [ ] Double-check all required fields are filled in the submission form

---

**Phase 9 complete when:**
- Public link is live and accessible
- Demo video is recorded and uploaded
- Article is published on DEV.to
- Submission form is submitted before October 11 midnight

---

---

## Key Files Summary

| File | Phase | Purpose |
|------|-------|---------|
| `tools/astronomy.py` | 1 | Object + location + time → azimuth & altitude |
| `spatial.py` | 1 | Degrees → human phrases ("east-northeast, 37° up") |
| `api/main.py` | 2 | FastAPI — all endpoints |
| `ui/app.py` | 3 | Streamlit UI |
| `llm.py` | 5 | Text → structured intent via Gemma |
| `tools/satellites.py` | 7 | TLE + SGP4 → pass predictions |
| `tools/weather_cache.py` | 8 | Reads cached weather/aurora data |
| `tests/test_spatial.py` | 1 | Unit tests for compass and altitude phrases |
| `tests/test_intents.py` | 5 | 20+ phrase intent accuracy test set |
| `cache/` | 8 | Stores weather, aurora, and TLE data |
| `.env` | 9 | API keys (never commit) |
| `requirements.txt` | All | Python dependencies |

---

## Technology Reference

| Technology | Role | AI? | Needs Internet? |
|-----------|------|-----|----------------|
| Streamlit | Python web UI | No | Needs a server |
| FastAPI | Backend API | No | Needs a server |
| Whisper | Speech-to-text | Yes (open weights) | No, runs locally |
| Gemma (via Ollama) | Intent parsing | Yes (open weights) | No, runs locally |
| Astronomy Engine / Skyfield | Celestial position maths | No | No |
| SGP4 + TLE | Satellite orbit maths | No | No (TLE needs periodic refresh) |
| SerpApi / OpenWeatherMap | Weather & aurora data | No | Yes (fetch once, cache) |
| ElevenLabs | Natural TTS voice | Yes | Yes |
| pyttsx3 / browser speechSynthesis | Offline TTS fallback | No | No |
| Render | App hosting | No | Yes |

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Local models too heavy for Render | Demo breaks on hosted URL | Demo AI locally; hosted version uses template fallback |
| Browser mic restrictions on phone | Voice input fails | Use tap-to-talk; never promise always-on |
| Streamlit can't do face-down sensing | Feature missing | Scope it out; call it future work in the article |
| TLE data goes stale | Wrong ISS pass times | Show cache age; re-fetch in `/prepare` |
| Gemma misreads intents | Wrong tool called | Small fixed intent list + 20-phrase test set |
| Overbuilding past the deadline | Miss submission | Hold to M1–M7; add S-tier only after MVP passes |
| ElevenLabs needs internet | No voice offline | Local TTS fallback always wired in |
| Claiming "offline" when TTS needs internet | Dishonest submission | Test offline mode explicitly in Phase 8 |

---

*Last updated: October 7, 2026*
