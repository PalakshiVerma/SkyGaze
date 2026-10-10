# SkyGaze: Project & Technology Explained

*A plain-language guide to what SkyGaze is, how it works, and what every technology in the stack actually does.*

## 1. What is SkyGaze?

SkyGaze is a **voice-guided stargazing assistant**. Instead of staring at a bright planetarium app, you ask out loud ("Where is Jupiter?") and it answers out loud ("Jupiter is about 35 degrees above the eastern horizon"). The phone can sit face-down on the grass with a black screen.

**Why it exists.** Human eyes need roughly 20 to 30 minutes in darkness to reach full night vision. A glowing phone screen, even with a red filter, partly resets that. SkyGaze keeps your eyes on the sky and your phone out of the way.

**The one idea to remember:**

> SkyGaze = astronomy software + a voice interface + a small AI layer.

The AI does **not** calculate where planets are. Normal, deterministic code does. The AI only understands what you asked and helps phrase the answer.

## 2. How one request flows

Example: you say *"Where is Jupiter?"*

1. **Microphone** captures your voice.
2. **Speech-to-text (Whisper)** turns audio into the text "Where is Jupiter?"
3. **Local LLM (Gemma)** reads the text and decides: *intent = locate an object, object = Jupiter*.
4. **Tool router** (your own code) calls the astronomy tool for Jupiter.
5. **Astronomy engine** computes azimuth (compass direction) and altitude (angle above horizon) for your location and the current time, e.g. 82 degrees and 37 degrees.
6. **Spatial converter** turns numbers into words: 82 degrees is east, 37 degrees is about a third of the way up the sky.
7. **Response builder** (LLM or a template) writes the sentence.
8. **Text-to-speech** speaks it to you.

The key design rule: **the LLM chooses the tool, the tool does the maths.** If someone asks "how do you know where Jupiter is?", the honest answer is "a deterministic astronomy library computes it from time and location; the model only interprets the request."

## 3. The technologies, one by one

| Technology | What it does | Is it AI? | Needs internet? |
| --- | --- | --- | --- |
| Streamlit | Builds the Python web UI quickly | No | Needs a server |
| FastAPI | Backend API that connects everything | No | Needs a server |
| Whisper | Speech to text | Yes (open weights) | No, if run locally |
| Gemma (local LLM) | Understands the request, picks the tool | Yes (open weights) | No, if run locally |
| Astronomy Engine / Skyfield | Computes positions of Sun, Moon, planets, stars | No | No |
| TLE data | Orbital description of a satellite | No (data) | Needs periodic refresh |
| SGP4 | Turns a TLE into a satellite position | No (algorithm) | No |
| SerpApi | Fetches fresh web info (clouds, aurora) | No | Yes |
| ElevenLabs | Natural-sounding text to speech | Yes | Yes, normally |
| Render | Hosts your app online | No | Yes |

### Streamlit (frontend)

A Python library that turns scripts into web apps. Great for hackathon demos and quick prototypes. **Limit:** it is not built for phone sensors, background audio or installable offline apps, so features like true face-down detection are out of reach with Streamlit alone.

### FastAPI (backend)

A Python framework for building an API: a set of URLs like `/ask` or `/satellite/iss` that the UI calls. Your AI, astronomy and satellite code all live behind it. Python is a natural fit because the AI and astronomy libraries are Python-first.

### Whisper (speech to text)

An open-weight speech recognition model. It runs on your own machine, so audio never has to leave it.

### Gemma (local LLM)

A small open-weight language model you download and run yourself (for example through a tool like Ollama). Its job here is deliberately small: turn natural sentences into structured intents such as `LOCATE_OBJECT(Jupiter)`, and optionally phrase friendly answers. You do **not** need a huge model.

### Astronomy Engine / Skyfield

Libraries that compute celestial positions from time and observer latitude/longitude. Output is just numbers (azimuth, altitude). This is geometry, not AI. It works with no internet.

### TLE and SGP4 (satellites)

- **TLE (Two-Line Element set):** two lines of text describing a satellite's orbit at a moment in time. Think of it as the input data.
- **SGP4:** the standard algorithm that takes a TLE and computes where the satellite is now.
- Combined with your location, you get azimuth and altitude for, say, the ISS. TLEs go stale over days, so you refresh them whenever you have internet and cache them.

### SerpApi (fresh information)

A search API. Astronomy maths cannot tell you if it will be cloudy tonight, so you fetch cloud forecasts and aurora alerts **once, while online**, and store them. Offline, SkyGaze answers from that cache. It should never be called on every question.

### ElevenLabs (voice output)

Produces natural, calm speech. Because it needs internet, treat it as an **optional upgrade**. Have a fallback (browser or local text-to-speech) so SkyGaze can still talk offline.

### Render (hosting)

A platform that deploys your code from GitHub and gives it a public URL. FastAPI and Streamlit can each run as a web service.

## 4. The most important concept: two meanings of "local"

|  | Local to the **server** | Local to the **user's device** |
| --- | --- | --- |
| Where the model runs | On Render's machine | On the phone or laptop |
| Calls a third-party AI API? | No | No |
| Works with no internet for the user? | **No** | **Yes** |
| Difficulty | Moderate | High (mobile browsers are limited) |

If Gemma runs inside your Render service, it is self-hosted but **not offline for the user**. True offline means the model, astronomy and cache all run on the user's own device.

For the hackathon, a sensible and honest framing is:

- **Online preparation:** fetch weather, aurora and TLEs, then cache them.
- **Offline mode (demonstrated on a laptop):** local Whisper, local Gemma, astronomy and SGP4 all run with the internet disconnected.
- **Public demo on Render:** works online; heavy models may need a lighter setup or a fallback.

## 5. System design at a glance

**Online phase:** SerpApi, TLE source and aurora source feed a **local cache**.

**Request phase:** Microphone, then Whisper, then Gemma (intent), then Tool Router. The router calls one of: Astronomy tool, Satellite tool (TLE + SGP4), or Weather tool (reads cache). The result goes through the Spatial Converter, then the Response Builder, then Text-to-Speech, then audio.

**Key components to build:**

- `tools/astronomy.py`: object name, time and location in; azimuth and altitude out.
- `tools/satellites.py`: TLE in; pass predictions out.
- `tools/weather_cache.py`: reads stored forecast data.
- `spatial.py`: converts degrees to phrases like "east-northeast, about 37 degrees up".
- `llm.py`: sends text to Gemma, returns a structured intent.
- `main.py` (FastAPI): exposes the endpoints.
- `app.py` (Streamlit): the UI.

## 6. Honest limitations to know up front

- **Streamlit cannot do the full vision.** Face-down sensing, continuous background listening and installable offline behaviour need a PWA (for example React/Next.js). Streamlit is the right choice for a fast demo, not the full product.
- **Phone browsers restrict** microphone use, background execution and sensors. Plan a **tap-to-talk fallback** rather than promising always-on listening.
- **Model size vs hosting.** Running Whisper and Gemma on a small free hosting tier may not fit in memory. Check resource limits before committing, and be ready to demo the AI locally.
- **Do not call it fully offline** unless everything, including speech output, works with no internet.

## 7. What to learn, in order

1. Run an astronomy library in a plain Python script and print Jupiter's azimuth and altitude.
2. Wrap it in a FastAPI endpoint.
3. Put a Streamlit UI on top.
4. Add voice input with Whisper.
5. Add Gemma for intent parsing and tool calling.
6. Add satellites (TLE + SGP4).
7. Add the online cache (weather, aurora).
8. Add text-to-speech.
9. Deploy and polish.

Do not learn everything at once. Get one question ("Where is Jupiter?") working end to end first; every later feature reuses the same pipeline.
