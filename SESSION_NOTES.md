# Session Notes — April 12, 2026

## What's Working

### Backend (AI Pipeline)
- 4 LangGraph agents running end-to-end on Gemini 2.5 Flash
- Works via Bifrost (Delhivery gateway) AND direct Gemini (personal key)
- FastAPI server with real pipeline wired up: POST /generate-with-defaults
- Test: `cd backend && source venv/bin/activate && python3 test_pipeline.py`
- API: `uvicorn api:app --reload --port 8000`

### Frontend (React Simulator)
- Menu screen with "Demo Mode" (hardcoded) and "Generate Live" (calls backend)
- Simulator shows Figma screenshots with tap zones, arrows, quiz breaks
- 9 steps across 3 screens + 3 quiz breaks with 5 questions
- Run: `cd frontend && npm run dev` → http://localhost:5173

## Last Issue Before Restart
- Bifrost timed out (ConnectTimeout to bifrost.delhivery.com)
- Likely VPN/network issue
- Fix: either disconnect VPN, or comment out BIFROST_VIRTUAL_KEY in .env to fall back to personal Gemini key

## How to Resume After Restart

### Start backend:
```bash
cd ~/Documents/Hackerthon/train-the-brain/backend
source venv/bin/activate
uvicorn api:app --reload --port 8000
```

### Start frontend:
```bash
cd ~/Documents/Hackerthon/train-the-brain/frontend
npm run dev
```

### Open browser:
http://localhost:5173

### If Bifrost times out:
Edit backend/.env — comment out BIFROST_VIRTUAL_KEY:
```
# BIFROST_VIRTUAL_KEY=your-key
GEMINI_API_KEY=AIzaSyAYatmeYs2wu8qdjGlTa_H8QNZBCXIeYO8
```
Restart backend.

## What's Left to Do

### Immediate (cosmetic)
- Fix simulator styles (overlay positioning, arrow accuracy, tip bar)
- Add more screenshots for all screen states
- Adjust tap_target coordinates to match actual screenshot positions

### Next Phase
- Agent 5: AI Vision screen mapper (auto-map screenshots to steps)
- PM Upload Portal (React form → calls POST /generate)
- Dashboard with seeded data
- Demo prep + rehearsal

## Key Files
- backend/.env — API keys (BIFROST_VIRTUAL_KEY or GEMINI_API_KEY)
- backend/config.py — model name, base URLs
- backend/services/llm_service.py — Bifrost vs direct Gemini switching
- frontend/src/App.tsx — menu + mode switching
- frontend/src/Simulator.tsx — interactive training UI
- frontend/src/manifest.ts — hardcoded FTG manifest (demo fallback)
- frontend/public/screens/ — Figma screenshots (ftg_01.png through ftg_11.png)
