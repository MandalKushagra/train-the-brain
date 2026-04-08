# Train the Brain

AI-powered interactive training generator — Shift Agentic Hackathon 2026

## What Is This?

Train the Brain auto-generates interactive training simulations from PRDs, code, and Figma designs. Instead of Academy spending 5 days making PPTs, a PM uploads existing artifacts and gets an interactive training in ~30 seconds.

Output is a responsive web link (like Lovable/Storylane) — user taps buttons, selects options, types text, answers quiz questions. All with dummy data, no real APIs. Looks exactly like the real app using Figma screenshots.

## Architecture

```
PM uploads PRD + Code + Screenshots
        │
        ▼
┌───────────────────┐
│ Agent 1: Ingestion │ → Extracts screens, elements, nav rules
└────────┬──────────┘
         ▼
┌───────────────────┐
│ Agent 2: Workflow  │ → Orders steps, finds branches
└────────┬──────────┘
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│Agent 3 │ │Agent 4 │ → Script + overlays | Quiz questions
└───┬────┘ └───┬────┘
    └─────┬────┘
          ▼
   Manifest JSON → Interactive Web Simulator
```

## Tech Stack

| Layer | Tool |
|-------|------|
| AI Pipeline | Python 3.12 + LangGraph + Gemini 2.5 Flash |
| Backend API | FastAPI + SQLite |
| Simulator | React + Tailwind CSS (responsive web) |
| PM Portal | React |
| Input Sources | Figma API, GitHub API, PRD text |

## Prerequisites

| Dependency | Version | Install |
|-----------|---------|---------|
| Python | 3.12+ | `python3 --version` |
| python3-venv | system pkg | `sudo apt install python3.12-venv` |
| pip | latest | `sudo apt install python3-pip` |
| Git | any | `sudo apt install git` |
| Node.js | 18+ (frontend) | `node --version` |

```bash
# Ubuntu/Debian system packages
sudo apt install python3.12-venv python3-pip git -y
```

## Quick Start

```bash
# Clone
git clone https://github.com/MandalKushagra/train-the-brain.git
cd train-the-brain/backend

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Add your Gemini API key
cp .env.example .env
# Edit .env → GEMINI_API_KEY=your-key-here

# Run the AI pipeline
python3 test_pipeline.py

# Run the API server
uvicorn api:app --reload --port 8000
```

## Get a Gemini API Key

1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with a personal Google account
3. Click "Create API key" → select or create a project
4. Copy the key into `.env`

Free tier: 5 RPM, 250K TPM, 20 RPD. Pipeline uses 4 calls per run = max 5 runs/day.

## Test Endpoints

```bash
curl http://localhost:8000/
curl http://localhost:8000/manifest/ftg_revamped_flow_v1 | python3 -m json.tool
curl http://localhost:8000/assessment/ftg_revamped_flow_v1 | python3 -m json.tool
```

## Python Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| langgraph | ≥0.2.0 | Multi-agent pipeline orchestration |
| langchain | ≥0.3.0 | LLM framework |
| langchain-google-genai | ≥2.0.0 | Gemini integration for LangChain |
| google-genai | ≥1.0.0 | Gemini API SDK |
| fastapi | ≥0.115.0 | HTTP API server |
| uvicorn | ≥0.32.0 | ASGI server for FastAPI |
| pdfplumber | ≥0.11.0 | PDF parsing for PRD uploads |
| moviepy | ≥1.0.3 | Video/image processing |
| Pillow | ≥10.0.0 | Image processing |
| gTTS | ≥2.5.0 | Text-to-speech |
| pydantic | ≥2.0.0 | Data models + validation |
| python-dotenv | ≥1.0.0 | Load .env files |
| httpx | ≥0.27.0 | HTTP client for APIs |

## Project Structure

```
train-the-brain/
├── backend/
│   ├── agents/
│   │   ├── ingestion.py          # Agent 1: reads PRD + code
│   │   ├── workflow.py           # Agent 2: extracts step order
│   │   ├── script_generator.py   # Agent 3: writes training script
│   │   ├── quiz_generator.py     # Agent 4: generates quiz
│   │   └── video_generator.py    # Future: video generation
│   ├── models/schemas.py         # All data models
│   ├── services/llm_service.py   # Gemini API wrapper
│   ├── pipeline.py               # LangGraph pipeline wiring
│   ├── api.py                    # FastAPI endpoints
│   ├── config.py                 # Config + security guardrails
│   ├── test_pipeline.py          # Test script
│   ├── test_data/                # Sanitized FTG test data
│   ├── .env.example              # Environment template
│   └── requirements.txt          # Python dependencies
├── frontend/                     # React simulator (TBD)
├── TEAM_CONTEXT.md               # Full context for teammates
├── TODO.md                       # Checklist
└── README.md                     # This file
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `python not found` | Use `python3` instead |
| `No module named venv` | `sudo apt install python3.12-venv` |
| `429 RESOURCE_EXHAUSTED` | Rate limited — wait 1 min, or check quota at aistudio.google.com |
| `404 model not found` | Check `config.py` — model should be `gemini-2.5-flash` |
| `.env not found` | `cp .env.example .env` and add your Gemini key |

## Team

Kushagra Mandal, Kapil Garg, Lovepreet Kaur, Avishek Jha, Lucky K

Demo Day: April 13-14, 2026
