# Train the Brain — Team Context Document
## Updated: April 6, 2026 | Demo Day: April 13-14

---

## What Are We Building?

An AI-powered platform that auto-generates interactive training simulations from PRDs, code, and Figma designs. Instead of Academy spending 5 days making PPTs, a PM uploads their existing artifacts and gets an interactive training in ~30 seconds.

## What's Done (Phase 1 — April 6)

The AI pipeline is built and working end-to-end:
- 4 LangGraph agents running on Gemini 2.5 Flash
- Input: PRD text + source code → Output: training manifest JSON + quiz
- Tested with real FTG (dimension capture) flow data
- Results: 12 training steps, 3 branches, 8 error scenarios, 5 quiz questions
- FastAPI backend scaffolded with mock endpoints
- Figma MCP connected, screenshots pulled

## What the Output Looks Like

NOT a video. It's an interactive web simulation — like Lovable/Storylane:
- User opens a link on their phone or desktop
- Sees real app screens (Figma screenshots)
- Taps buttons, selects options, types into fields (all dummy data)
- Gets guided with overlay instructions + tips
- Every 3-4 steps: quiz break with MCQ
- Final score at the end

The simulation looks exactly like the real app because it uses actual Figma screenshots as backgrounds, with interactive elements overlaid on top.

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
│Script  │ │Quiz    │   (run in parallel)
└───┬────┘ └───┬────┘
    └─────┬────┘
          ▼
   Manifest JSON
          │
          ▼
┌───────────────────┐
│ Interactive Web    │ → Responsive simulator
│ Simulator (React)  │   reads manifest, renders training
└───────────────────┘
```

## Tech Stack

- AI: Python + LangGraph + Gemini 2.5 Flash (free tier, personal key for now)
- Backend: FastAPI + SQLite
- Simulator: React + Tailwind CSS (responsive web link)
- PM Portal: React (upload form + preview)
- Dashboard: React + Recharts
- APIs: Figma MCP, GitHub API

## How to Run What Exists

```bash
cd train-the-brain/backend
source venv/bin/activate
python3 test_pipeline.py          # runs AI pipeline, prints manifest + quiz
uvicorn api:app --reload --port 8000  # starts API server
```

## Key Files

```
train-the-brain/
├── backend/
│   ├── agents/
│   │   ├── ingestion.py          # Agent 1: reads PRD + code
│   │   ├── workflow.py           # Agent 2: extracts step order
│   │   ├── script_generator.py   # Agent 3: writes training script
│   │   ├── quiz_generator.py     # Agent 4: generates quiz
│   │   └── video_generator.py    # (deprecated — replaced by web simulator)
│   ├── models/schemas.py         # All data models
│   ├── services/llm_service.py   # Gemini API wrapper
│   ├── pipeline.py               # LangGraph wiring
│   ├── api.py                    # FastAPI endpoints
│   ├── config.py                 # API keys + security guardrails
│   ├── test_pipeline.py          # Test script
│   └── test_data/                # Sanitized FTG PRD + code
├── frontend/                     # (to be built — React simulator)
├── TODO.md                       # Full checklist
└── TEAM_CONTEXT.md               # This file
```

## What Each Person Needs to Do Next

| Person | Task | Start With |
|--------|------|------------|
| Person 1 | Tune AI pipeline prompts, wire FastAPI to real pipeline | Run test_pipeline.py, review output, tweak prompts |
| Person 2 | Build interactive simulator (React + Tailwind) | Scaffold React app, render first screenshot with overlay |
| Person 3 | Build PM upload portal | Simple React form that calls POST /generate |
| Person 4 | Quiz UI + scoring inside simulator | Quiz dialog component, score tracking |
| Person 5 | Dashboard + presentation | Seed fake data, build charts, prep demo script |

## Security Reminders
- No real PII in any data
- No production API keys
- Gemini key stays in .env (never commit)
- All LLM prompts include security guardrails
- Dummy/synthetic data only
