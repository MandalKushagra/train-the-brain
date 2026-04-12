# Train the Brain — TODO Checklist

## Demo Day: April 13-14, 2026
## Updated: April 6, 2026

---

## PHASE 1: AI Pipeline Setup ✅ DONE (April 6)

- [x] GCP project created (trn-ur-brn)
- [x] Gemini 2.5 Flash API key working
- [x] Python venv + all dependencies installed
- [x] LangGraph pipeline with 4 agents running end-to-end
- [x] Agent 1 (Ingestion): PRD + code → 4 screens, 4 nav rules
- [x] Agent 2 (Workflow): 12 ordered steps, 3 branches
- [x] Agent 3 (Script): Narration + overlay text for all 12 steps
- [x] Agent 4 (Quiz): 5 MCQ questions with answers
- [x] Sanitized FTG test data (PRD + code) ready
- [x] Figma MCP connected, 4 core screenshots pulled
- [x] FastAPI mock server with /generate, /manifest, /assessment endpoints
- [x] Security guardrails in all LLM prompts
- [x] .gitignore protecting secrets

---

## PHASE 2: Pipeline Tuning (April 7-8) ← NEXT

- [ ] Test with full sanitized FTG data (`python3 test_pipeline.py --use-files`)
- [ ] Tweak Agent 1-4 prompts until output is demo-quality
- [ ] Update Agent 3 to include tap_target coordinates from Figma metadata
- [ ] Update Agent 3 to include quiz_break insertion points
- [ ] Update Agent 3 to include "tip" text for overlay tips
- [ ] Save a "golden" manifest JSON as demo fallback
- [ ] Wire FastAPI to use real pipeline (replace mock data)

---

## PHASE 2.5: Agent 5 — Screen Mapper (AI Vision) — DISCUSS LATER

**PM drops screenshots in any order, any filename. AI figures out which is which.**

- [ ] Build Agent 5: takes unordered screenshots + manifest → maps each screenshot to correct step
- [ ] Use Gemini Vision via Bifrost to analyze each screenshot
- [ ] Auto-detect: which screen is this? (packaging, identifiers, dimensions, etc.)
- [ ] Auto-detect: tap target coordinates (where is the SIOB card? where is the Next button?)
- [ ] Output: manifest with screenshot paths + tap_target coordinates filled in
- [ ] Judge pitch: "PM dumps screenshots, AI vision agent maps them automatically"

---

## PHASE 3: Interactive Simulator — Responsive Web App (April 8-10)

**Output: A responsive web link that works on phone + desktop**
**Looks like the real app — uses Figma screenshots as backgrounds**
**User-driven: taps buttons, selects options, types text — all with dummy data**

- [ ] Scaffold React + Tailwind project
- [ ] Simulator reads manifest JSON from backend API
- [ ] Full-screen Figma screenshot as background per step
- [ ] Invisible tap zones positioned over UI elements (from manifest coordinates)
- [ ] Pulsing highlight animation on current tap target
- [ ] Overlay instruction card at bottom of screen
- [ ] "Did you know" tip overlays between steps
- [ ] TAP action: user taps correct zone → next screenshot
- [ ] TYPE action: real HTML input overlaid on screenshot → user types dummy data
- [ ] SELECT action: popup with options → user picks → next screenshot
- [ ] Wrong action → error feedback message + vibrate
- [ ] Quiz breaks every 3-4 steps (MCQ from manifest)
- [ ] Quiz scoring + instant feedback per question
- [ ] Final score screen with completion status
- [ ] Responsive: works on mobile browser + desktop
- [ ] Phone frame wrapper for desktop view

---

## PHASE 4: PM Upload Portal (April 10-11)

- [ ] Simple web form: paste PRD text, paste code, upload screenshots
- [ ] "Generate Training" button → calls POST /generate
- [ ] Loading state showing pipeline progress
- [ ] Preview: shows generated steps as cards
- [ ] Edit mode: PM can tweak instructions before publishing
- [ ] Publish → generates shareable training link

---

## PHASE 5: Backend API (April 9-10)

- [ ] POST /generate → runs real pipeline, stores manifest in SQLite
- [ ] GET /training/{id} → serves manifest JSON to simulator
- [ ] GET /training/{id}/screenshots → serves screenshot images
- [ ] POST /training/{id}/complete → records completion + quiz score
- [ ] GET /dashboard/stats → completion rates for dashboard

---

## PHASE 6: Dashboard (April 11) — NICE TO HAVE

- [ ] Seed 5-10 fake operator profiles
- [ ] Completion rates chart per workflow
- [ ] Quiz scores per operator
- [ ] Step-level analytics ("40% got stuck on Step 3")
- [ ] Flagged operators for manual re-training

---

## PHASE 7: Demo Prep (April 12)

- [ ] End-to-end dry run: upload → generate → interactive training → dashboard
- [ ] Pre-generate golden manifest (don't rely on live Gemini during demo)
- [ ] Backup video recording of full demo
- [ ] 1-slide before/after comparison
- [ ] Rehearse 5-minute demo script
- [ ] Test on demo machine/projector
- [ ] Prepare judge Q&A answers

---

## SECURITY CHECKLIST

- [x] No real PII in demo data
- [x] No production API keys in code
- [x] Gemini key in .env (not hardcoded)
- [x] .env in .gitignore
- [x] Security guardrails in all LLM prompts
- [ ] No internal URLs exposed
- [ ] Dummy data only in simulator + dashboard

---

## TECH STACK

| Layer | Tool |
|-------|------|
| AI Pipeline | Python + LangGraph + Gemini 2.5 Flash |
| Backend API | FastAPI + SQLite |
| Simulator | React + Tailwind CSS (responsive web) |
| PM Portal | React (simple upload form) |
| Dashboard | React + Recharts |
| Input Sources | Figma API, GitHub API, PRD text |
| Observability | Langfuse (optional) |

---

## TEAM SPLIT

| Person | Owns |
|--------|------|
| Person 1 | AI Pipeline + Backend API |
| Person 2 | Interactive Simulator (React web) |
| Person 3 | PM Upload Portal |
| Person 4 | Quiz UI + scoring + completion |
| Person 5 | Dashboard + demo prep + presentation |
