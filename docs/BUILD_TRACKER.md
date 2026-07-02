# SHRRI AI OS v2 — Build Tracker

Master checklist from the full architecture doc. Update status as we go.
Legend: ✅ done | 🔄 in progress | ⏳ not started

---

## Phase 1 — SHRRI Runner (spine)
- ✅ Session Manager
- ✅ Context Builder
- ✅ Policy & Permission Engine (real tool-level enforcement)
- ✅ Session persistence (survive restart)
- ✅ Audit logging (log denied/allowed tool calls)
- ✅ DM pairing flow (restricted -> main upgrade path)

## Phase 2 — Input Layer
- ✅ Wake Word Engine (hey_jarvis placeholder — hey_shree custom training pending)
- ✅ Speech To Text (Whisper.cpp, multilingual base model)
- ✅ Language Detection Engine
- ✅ Conversation Controller
- 🔄 Notification Center (interface only — delivery pending Phase 15/16)

## Phase 3 — Provider Router
- ✅ Multi-provider routing (wired into Runner via provider_router.py adapter)
- ✅ Local AI first (Ollama fallback confirmed working, qwen2.5:3b)
- ✅ Model Selection logic (tested — keyword classifier infers capability from raw prompt across 16 categories, 9/9 test cases pass, confirmed wired end-to-end through ProviderRouter)
- ✅ Provider Ranking (tested — demotes failing provider after 1 failure, confirmed via stats file + reorder check)
- ✅ Automatic Failover (tested — confirmed falls through on provider error)
- ✅ Offline First mode (tested — local wins even when cloud provider has perfect track record, confirmed policy overrides ranking)
- ✅ Hybrid Routing (tested — local model triages prompt first, simple prompts answered local-only, complex prompts correctly escalate to cloud, confirmed both paths working end-to-end)

## Phase 4 — Workflow Engine
- ✅ Goal Planner (tested — LLM decomposes goal into dependency-ordered JSON plan, parsed into WorkflowGraph, output-substitution placeholder bug found and fixed, full pipeline confirmed end-to-end with real provider calls; also found+fixed a dead nvidia/riva-translate-4b-instruct provider along the way)
- ✅ Workflow Graph Builder (tested — diamond dependency graph A→B,A→C,B+C→D resolves correctly step by step, cycle detection confirmed on forced circular dependency)
- ✅ Execution Scheduler (tested — dependency-ordered execution confirmed, mixed custom+LLM handlers work, checkpoint auto-cleans on success and persists on failure, stop-on-failure confirmed blocks downstream tasks)
- ✅ Task Queue (tested — FIFO ordering, status lifecycle pending/running/done/failed, result/error tracking all confirmed)
- ✅ Checkpoint Manager (tested — state survives simulated restart via fresh SQLite connection, task statuses preserved, delete cleans up correctly)

## Phase 4.5 — Engine Unification
- ✅ Router Adapter (tested — wraps live engine.router.Router behind ProviderRouter-compatible interface, GoalPlanner + ExecutionScheduler now run through the same engine as production WhatsApp bot, confirmed end-to-end with real haiku+translate workflow)

## Phase 5 — Multi Agent System
- ✅ Manager Agent (tested — orchestrates GoalPlanner + ExecutionScheduler end-to-end, registers specialist agents via register_agent(), confirmed working with real multi-step goal through unified engine)
- ✅ Research Agent (tested — confirmed real web search context injection via Router, cited live sources with timestamps for a current-price question, survived a tool dispatcher error + provider timeouts via existing failover)
- ✅ Coding Agent (tested — routes through coding capability list, confirmed working code output; noted the LLM's own example didn't match its code's actual behavior — a model accuracy issue, not an agent bug)
- ✅ Browser Agent (tested — real Playwright browsing confirmed against example.com, correctly extracted actual page heading, not a hallucinated guess)
- ✅ Vision Agent (tested — added real image support to GoogleProvider + NvidiaProvider via chat_with_image(), confirmed both correctly identify a test image's shape/color, built-in failover between vision providers); ALSO wired to real messaging channels: added chat_with_image() to GoogleProvider+NvidiaProvider, added WhatsApp image download support in wa_bridge (Baileys downloadMediaMessage), added Telegram photo handler — confirmed end-to-end with a real Telegram photo (detailed comic page correctly described, including transcribing Tamil script); found+fixed two unrelated live bugs along the way: Telegram bot was crash-looping for hours on a placeholder token (config import pointed to the wrong file), and YOUR_ID mismatch was silently blocking all messages)
- ⏳ Planning Agent
- ⏳ Memory Agent
- ⏳ Automation Agent
- ⏳ Security Agent
- ⏳ Testing Agent
- ⏳ Documentation Agent
- ⏳ Linux Agent
- ⏳ Android Agent
- ⏳ GitHub Agent
- ⏳ Calendar Agent
- ⏳ Email Agent
- ⏳ Finance Agent
- ⏳ IoT Agent

## Phase 6 — Conversation Broker
- ⏳ Agent Communication / Message Bus
- ⏳ Consensus Engine
- ⏳ Negotiation Engine
- ⏳ Shared Context
- ⏳ Dynamic Agent Creation

## Phase 7 — Tool Ecosystem
- ✅ Gmail (read, send, search — existing)
- ✅ Google Calendar (create, list, upcoming — existing)
- ✅ WhatsApp (Baileys bridge — existing)
- ✅ Telegram (full bot — existing)
- ✅ Math tool (deterministic AST-safe — existing)
- ⏳ MCP (standard protocol, not custom mcp_client.py)
- ⏳ GitHub tool
- ⏳ Python/Shell/Linux exec (sandboxed)
- ⏳ ADB (Android)
- ⏳ Playwright (browser automation)
- ⏳ SQLite tool
- ⏳ Files tool
- ⏳ Weather tool
- ⏳ Maps tool
- ⏳ IoT tool

## Phase 8 — Computer Use Engine
- ⏳ Desktop Controller
- ⏳ Browser Controller
- ⏳ Mouse/Keyboard Controller
- ⏳ Clipboard
- ⏳ Window Manager
- ⏳ OCR (route to cloud vision — CPU-only risk flagged)
- ⏳ Vision / Screen Understanding (route to cloud vision)
- ⏳ Verification Engine
- ⏳ Recovery Engine

## Phase 9 — Memory System
- ✅ Long-term memory (RAG + FTS5 — existing)
- ✅ Background consolidation (dream_cycle.py, curator.py, weekly_consolidator.py — existing)
- ⏳ Working Memory (in-session, separate from long-term)
- ⏳ Short-term Memory formalized
- ⏳ Semantic Memory / Episodic Memory split
- ⏳ Experience Memory
- ⏳ Vector Database (proper, not just FTS5)
- ⏳ Memory Ranking
- ⏳ Memory Compression
- ⏳ Memory Forgetting
- ⏳ Memory Timeline (browsable UI)
- ⏳ Daily session log persistence

## Phase 10 — Reasoning System
- 🔄 Reasoning Engine (reasoning.py exists, needs upgrade)
- ⏳ Reflection Engine
- ⏳ Self Critic
- ⏳ Verifier
- ⏳ Confidence Scoring
- ⏳ ReAct pattern
- ⏳ Tree Search (future/stretch)

## Phase 11 — Learning Engine
- ⏳ Experience Replay
- ⏳ Skill Generator
- ⏳ Skill Evolution
- ⏳ Workflow Recorder
- ⏳ Dream Mode (extends existing dream_cycle.py)
- ⏳ AI DNA
- ⏳ Memory Optimizer
- ⏳ Prompt Optimizer
- ⏳ Self Benchmark

## Phase 12 — Evaluation System
- ⏳ Benchmarks
- ⏳ Tracing
- ⏳ Metrics
- ⏳ Prompt Versions
- ⏳ Experiments
- ⏳ Latency tracking
- ⏳ Model Comparison
- ⏳ Dashboard

## Phase 13 — Security System
- ✅ Permission Engine (Phase 1, done)
- ⏳ Sandbox (Docker/isolated exec)
- ⏳ Secrets Manager
- ⏳ Encryption
- ⏳ Authentication
- ⏳ Authorization (beyond basic tier)
- ⏳ Policy Engine (broader than tool gating)
- ⏳ Audit Logs

## Phase 14 — Plugin System
- ⏳ Plugin SDK
- ⏳ Extension SDK
- ⏳ Marketplace
- ⏳ Auto Discovery
- ⏳ Plugin Registry

## Phase 15 — Device Abstraction Layer
- ⏳ Device API (unified)
- ⏳ Linux Backend
- ⏳ Android Backend
- ⏳ Future Windows Backend
- ⏳ Future macOS Backend

## Phase 16 — Output Layer
- ✅ Text (Telegram/WhatsApp — existing)
- 🔄 Voice (Piper TTS — existing, needs Tamil-script prompt fix)
- ⏳ Desktop Notification
- ⏳ Android Notification
- ⏳ API Response format
- ⏳ Dashboard
- ⏳ Logs (structured)

---

## Notes
- CPU-only laptop (Ryzen 5 5500U, 16GB RAM) — Vision/OCR/Computer-Use should route
  through cloud providers (Gemini/Groq vision), not local inference. Flagged risk,
  not a blocker.
- Existing SHRRI v1 code to port (not rebuild from scratch): multi_router.py,
  capability_map.py, free_models.py, memory.py, dream_cycle.py, curator.py,
  weekly_consolidator.py, math_tool.py, Gmail/Calendar/WhatsApp/Telegram integrations.
- Update this file's status markers as each item ships. Commit it with the code.
