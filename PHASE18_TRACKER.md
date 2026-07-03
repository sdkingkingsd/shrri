# SHRRI AI OS — Phase 18 Tracker: Chat-Centric UI/UX

**Goal:** Turn the existing webui (Phase 17: React + FastAPI, 6 tabs) into a chat-first
interface where every SHRRI capability is accessible from one screen — not buried in tabs.

**Base:** `~/shrri/webui/frontend` (React + Vite) + `~/shrri/webui/` (FastAPI backend)
**Status legend:** `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked

---

## 0. Pre-flight
- [ ] Confirm Phase 17 webui runs clean: `bash shrri_webui.sh` → `http://localhost:7788`
- [ ] Confirm backend routes for: agents list, goal planner, memory, scheduler status
- [ ] Snapshot current `webui/` before restructuring: `cp -r ~/shrri/webui ~/shrri/webui_backup_$(date +%F)`

## 1. Layout skeleton
- [ ] Left sidebar: agent/tool list (18 agents), collapsible groups (System / Comms / Dev / IoT)
- [ ] Center: persistent chat panel (main `/goal` entry point, streaming responses)
- [ ] Right drawer (toggle): context panel — active task, scheduler queue, memory hits
- [ ] Top bar: model/provider status (Groq/NIM/Cerebras/Ollama), connection health dot

## 2. Chat panel core
- [ ] Message list component with role bubbles (user / shrri / tool-call / tool-result)
- [ ] Streaming token renderer (SSE or websocket from FastAPI)
- [ ] Inline tool-call cards (collapsed by default, expand to show raw args/result)
- [ ] Slash-command palette (`/goal`, `/agent`, `/memory`, `/schedule`) with autocomplete
- [ ] Voice input toggle (reuse faster-whisper pipeline if still present)

## 3. Feature surfacing (map every backend capability to a UI affordance)
- [ ] Agent picker chips above input — manually pin an agent (Linux/adb/gh/Calendar/Email/Finance/MQTT/…)
- [ ] Live agent activity feed (right drawer) — which agent is running, ETA
- [ ] Memory panel — long-term facts, session notes, search box, consolidation status
- [ ] Scheduler view — pending/duplicate reminders visible here (helps kill the Level 6 dup bug visually)
- [ ] Browser automation viewer — inline screenshot preview when Playwright tool fires
- [ ] Gmail panel — inbox snapshot, draft/reply actions surfaced as buttons, not just chat text

## 4. Conversation Broker hook (ties into your Phase 6 backend work)
- [ ] UI subscribes to broker events (agent handoffs) and renders as a mini timeline per goal
- [ ] Show planner classification (conditional vs sequential) as a debug badge — helps you
      visually catch the determinism bug you're chasing

## 5. Styling / UX polish
- [ ] Dark theme base (match existing `#11111b` bg from index.html)
- [ ] Responsive: usable at laptop width, no fixed px layouts
- [ ] Empty states for each panel (no agents running, no memory hits, etc.)

## 6. Build & ship
- [ ] `npm run build` → confirm output lands in `webui/static/`
- [ ] `git add -f` anything gitignored intentionally (static build output)
- [ ] Commit + push per phase, not one giant commit
- [ ] Update root `shrri_webui.sh` if new routes/ports needed

## 7. Known bugs to keep visible during this phase (don't silently fix, verify in UI)
- [ ] `mark_read` nondeterminism (agentic loop)
- [ ] Planner prompt determinism (conditional vs sequential misclassification)
- [ ] Level 6 duplicate-reminder bug
- [ ] Decide: ReAct-style loop restructure — yes/no, log decision here once made

---

## Next session starting point
Once this tracker is committed, next command block starts at **Section 1: Layout skeleton**.
