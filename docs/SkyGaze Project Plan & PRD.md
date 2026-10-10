# SkyGaze: Project Plan & PRD

*Product requirements and build plan for the Hacktoberfest Week 1 submission. Assumptions are marked so you can correct them.*

## 1. Overview

**Product:** SkyGaze, a voice-guided stargazing assistant that answers "where is it in the sky?" out loud, so users keep their eyes dark-adapted and off the screen.

**Challenge fit:** An open-weight local model (Gemma) sits at the core, interpreting voice commands, while deterministic astronomy code does the calculations. The story: the core experience keeps working when the user has no connectivity, which is exactly when people go stargazing.

**Deadline:** The shared chat says Week 1 closes on **October 11**. Please verify this against the official challenge page.

## 2. Problem & goals

**Problem.** Planetarium apps use a bright screen, which disrupts night vision (20 to 30 minutes to fully adapt). Users also lose time hunting through menus in the dark.

**Goals**

1. Let a user ask about any bright sky object by voice and hear a clear direction.
2. Compute positions deterministically, not with the LLM.
3. Work with the internet off for core astronomy (demonstrated, not just claimed).
4. Ship a polished demo and a clear write-up before the deadline.

**Non-goals (for this submission)**

- All 88 constellations, individual Starlink tracking
- User accounts, auth, databases, RAG
- Perfect face-down sensing and always-on background listening
- Running a large model on a phone

## 3. Users & scenarios

**Primary user:** a casual stargazer outdoors at night who wants quick, hands-free answers.

**Scenarios**

- "Where is Jupiter?" gets a spoken direction and elevation.
- "Is Jupiter visible right now?" combines altitude, sun position and cached cloud cover.
- "When does the ISS pass over?" gives the next pass time and direction.
- "Can I see stars tonight?" summarises cached weather, moon phase and darkness.

## 4. Scope & requirements

### Must have (MVP)

| ID | Requirement | Acceptance test |
| --- | --- | --- |
| M1 | Capture the user's location and current time | Coordinates and time shown/logged correctly |
| M2 | Locate Sun, Moon and 8 planets (azimuth, altitude) | Values match a reference tool within about 1 degree |
| M3 | Convert angles to spoken phrases (e.g. "east-northeast, 37 degrees up") | Unit tests on compass and altitude mapping |
| M4 | Voice input with speech-to-text | Spoken "Where is Mars?" is transcribed correctly in a quiet room |
| M5 | Local LLM turns text into a structured intent and tool call | Correct intent on a set of 20+ test phrasings |
| M6 | Spoken response (TTS) | Answer is audible end to end |
| M7 | Core flow works with internet disconnected | Demo with Wi-Fi off still answers M2 questions |

### Should have

| ID | Requirement |
| --- | --- |
| S1 | ISS pass prediction from cached TLE data via SGP4 |
| S2 | Cached cloud and aurora data fetched while online (SerpApi) |
| S3 | Visibility answer combining altitude, sun position and cached cloud cover |
| S4 | ElevenLabs voice as an optional upgrade with a local TTS fallback |

### Could have

- Tap-to-talk plus a "night mode" black screen
- Bright stars and a few famous constellations
- Latency and tool-call logging for the write-up

### Later (not in this submission)

- True PWA with face-down detection, installable on phones
- On-device model inference

## 5. Architecture & stack

**Recommended for this build (a working assumption, please confirm):**

| Layer | Choice | Why |
| --- | --- | --- |
| UI | Streamlit | Fastest route to a working demo in Python |
| Backend | FastAPI | Clean API; Python fits the AI and astronomy libraries |
| Speech-to-text | Whisper (local) | Open weights, runs offline |
| LLM | Gemma (local, e.g. via Ollama) | Open weights; intent parsing and phrasing |
| Astronomy | Astronomy Engine or Skyfield | Deterministic positions, no internet |
| Satellites | TLE data + SGP4 | Deterministic orbit maths |
| Fresh data | SerpApi | Cloud and aurora info, fetched once while online |
| Voice out | ElevenLabs with local TTS fallback | Natural voice online, still speaks offline |
| Hosting | Render (demo) | Simple deploy from GitHub |

**Design rules**

1. The LLM never calculates positions; tools do.
2. The LLM output is structured intent only (for example `LOCATE_OBJECT` with object = Jupiter).
3. Internet use happens in a **prepare while online** step, never per question.
4. Every online dependency has an offline fallback.

**Honest deployment note.** A model running on Render is self-hosted but not offline for the user. Free hosting tiers may not have the memory to run Whisper and Gemma. Plan: run the full local-AI version on a laptop for the offline demo, and use a lighter or fallback path for the hosted link.

## 6. Key API endpoints (FastAPI)

| Endpoint | Purpose |
| --- | --- |
| `POST /transcribe` | Audio in, text out (Whisper) |
| `POST /ask` | Text in, intent, tool call and spoken-style answer out |
| `GET /sky/{object}` | Azimuth and altitude for one object |
| `GET /satellite/{name}/passes` | Upcoming passes from cached TLE |
| `POST /prepare` | Fetch and cache weather, aurora and TLEs while online |
| `GET /health` | Status, cache age and online/offline state |

## 7. Build plan

| Phase | Deliverable | Done when |
| --- | --- | --- |
| 1 | Astronomy script | Prints Jupiter's azimuth and altitude for your location |
| 2 | Spatial converter plus unit tests | Angles become correct phrases |
| 3 | FastAPI endpoints for sky objects | `/sky/jupiter` returns correct JSON |
| 4 | Streamlit UI with text input | Typed question returns an answer |
| 5 | Voice input (Whisper) | Spoken question becomes text |
| 6 | Gemma intent parsing and tool calling | 20+ phrasings map to the right tool |
| 7 | Text-to-speech output | Full voice round trip works |
| 8 | Satellites (TLE + SGP4) | ISS pass answer works |
| 9 | Online cache (SerpApi data) and offline test | Wi-Fi off, core features still work |
| 10 | Deploy, demo recording, DEV write-up | Public link, video and article ready |

**Timeline principle.** Work backwards from the deadline: reserve the final 2 days for the demo, recording and article. If you fall behind, cut S3, S4 and phase 8 before touching M1 to M7.

## 8. Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Local models too heavy for hosting | Demo the AI locally; hosted version uses a fallback |
| Browser/phone limits on mic and sensors | Use tap-to-talk; do not promise always-on listening |
| Streamlit cannot do face-down sensing | Scope it out; mention it as future work |
| Stale TLE or weather data | Show cache age; refresh in the prepare step |
| LLM misreads intents | Small fixed intent list, structured output, test set |
| Overbuilding too many technologies | Hold to the MVP list; add only after M1 to M7 pass |
| Claiming "offline" when TTS needs internet | Local TTS fallback; describe the system accurately |

## 9. Success metrics

- M2 position accuracy within about 1 degree of a reference source
- 90%+ correct intents on the 20-phrase test set
- End-to-end answer time under about 5 seconds locally (target, to be measured)
- Core demo works with Wi-Fi off, shown on video
- Submission delivered on time with a clear write-up

## 10. Open questions for you

- Is the deadline really October 11, and which challenge category are you targeting?
- Will the offline demo run on a laptop, or do you need it on a phone?
- Do you want Streamlit for the demo, or a PWA front end later?
- Which partner tools (Gemma, ElevenLabs, SerpApi) do you want to feature in the write-up?
