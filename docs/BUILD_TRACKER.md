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
- ✅ Agent Registry + Telegram /goal command (tested — full ManagerAgent/GoalPlanner/ExecutionScheduler pipeline now triggerable live from Telegram, confirmed end-to-end with real multi-step haiku+translate goal through Telegram chat, logs show all 5 agents registered + planner + scheduler firing correctly)
- ✅ Manager Agent (tested — orchestrates GoalPlanner + ExecutionScheduler end-to-end, registers specialist agents via register_agent(), confirmed working with real multi-step goal through unified engine)
- ✅ Research Agent (tested — confirmed real web search context injection via Router, cited live sources with timestamps for a current-price question, survived a tool dispatcher error + provider timeouts via existing failover)
- ✅ Coding Agent (tested — routes through coding capability list, confirmed working code output; noted the LLM's own example didn't match its code's actual behavior — a model accuracy issue, not an agent bug)
- ✅ Browser Agent (tested — real Playwright browsing confirmed against example.com, correctly extracted actual page heading, not a hallucinated guess)
- ✅ Vision Agent (tested — added real image support to GoogleProvider + NvidiaProvider via chat_with_image(), confirmed both correctly identify a test image's shape/color, built-in failover between vision providers); ALSO wired to real messaging channels: added chat_with_image() to GoogleProvider+NvidiaProvider, added WhatsApp image download support in wa_bridge (Baileys downloadMediaMessage), added Telegram photo handler — confirmed end-to-end with a real Telegram photo (detailed comic page correctly described, including transcribing Tamil script); found+fixed two unrelated live bugs along the way: Telegram bot was crash-looping for hours on a placeholder token (config import pointed to the wrong file), and YOUR_ID mismatch was silently blocking all messages)
- ✅ Planning Agent (this IS the Goal Planner from Phase 4 — a step-by-step task breakdown specialist is functionally the same as the planner already built; no separate agent needed, avoiding duplicate logic)
- ✅ Memory Agent (tested — save_fact + recall via Memory singleton, confirmed end-to-end through Telegram /goal: a 'remember X' goal correctly saved a fact, a separate 'recall X' goal correctly retrieved it and answered from real stored memory, not generic knowledge)
- ✅ Automation Agent (tested — routes to existing reminder_tool/scheduler.py, confirmed end-to-end through Telegram /goal: set a real one-shot reminder, listed real cron/at state including pre-existing automations, and delete tested; found+fixed a pre-existing bug along the way — telegram_notify.py was regex-scraping BOT_TOKEN/YOUR_ID from telegram_bot.py's source text, but that file only imports those values from shrri_config_local.py, so every cron/at-triggered reminder was silently failing to deliver; fixed by importing creds directly, same pattern telegram_bot.py itself uses)
- ✅ Security Agent (tested — thin wrapper around real PermissionEngine/AuditLogger/doctor.py, confirmed end-to-end through Telegram /goal: correctly reported restricted-tier vs main-only tools, correctly read real (empty) audit log for denials, and ran a live 12/12 system health check via doctor.py; also handled a combined multi-part question by having the planner split it into parallel security steps + a synthesis step on its own)
- ✅ Testing Agent (tested — thin wrapper around real code_sandbox.py Docker execution + SHRRI's own test_suite.py, confirmed end-to-end through Telegram /goal: actually ran a bare code snippet through the isolated no-network Docker sandbox and got the real computed output (5), and ran the full regression suite live — reported real results (11/12 passed), surfacing a genuine pre-existing dispatcher bug where 'send message to X' non-email phrasing incorrectly routes; fixed one gap along the way — Testing Agent originally required a code-fence or 'test this:' prefix, but the Goal Planner strips wrapper text and passes bare code as the prompt, so added a fallback that runs prompts that look like code directly since the planner already decided it's a testing step)
- ✅ Documentation Agent (tested — no existing doc tool to wrap, so uses Router (like Coding Agent) for generation + tools.self_edit for safe read/write with automatic backups; confirmed end-to-end through Telegram /goal: generated a real usage guide for the /goal command, grounded in actual grepped source rather than hallucinating generic SaaS-goal-tracker behavior, and honestly flagged what the grepped snippet didn't reveal instead of inventing an answer; known limitation — grounding only greps for the literal term mentioned in the prompt (e.g. '/goal'), so it won't automatically pull in related files like goal_planner.py/manager_agent.py unless they're also named; acceptable for a thin-wrapper agent, deeper multi-hop codebase search would be scope creep here)
- ✅ Linux Agent (tested — thin wrapper around tools.system_tool.system_control(), real subprocess-level control confirmed end-to-end through Telegram /goal: volume actually changed via pactl; fixed two pre-existing bugs found along the way — (1) planner was misrouting immediate system-control requests like 'set volume' to automation instead of linux, fixed by clarifying the type description to explicitly state automation is only for recurring/reminder tasks; (2) system_tool.py's volume/brightness regexes required the number to immediately follow the word (e.g. 'volume 40') and failed on natural phrasing like 'volume to 40 percent', fixed by allowing optional 'to'/'at' in between)
- ✅ Android Agent (tested — no existing Android integration in the codebase, so installed real adb (Android Debug Bridge) and built the agent around it directly: list connected devices, battery, screenshot, install/uninstall APK, list apps; confirmed end-to-end through Telegram /goal that it honestly reports 'No Android device connected' with real pairing instructions rather than fabricating device state, since no phone is currently paired; fixed one bug found during testing — adb's first-run daemon-startup lines ('daemon not running; starting now...') were being misparsed as device entries, fixed by filtering to only real device-table lines)
- ✅ GitHub Agent (tested — thin wrapper around the real, already-authenticated gh CLI (repo/workflow/gist/read:org scopes) plus plain git subprocess calls on the local ~/shrri repo; confirmed end-to-end through Telegram /goal: real 'git status --short --branch' correctly showed actual uncommitted changes, and real 'gh issue list' correctly returned the repo's true (empty) issue state rather than a fabricated answer; also supports commit/push, PR list/create, issue create, and repo info, all backed by the real CLI)
- ✅ Calendar Agent (tested — thin wrapper around existing tools.calendar_tool, which already does real Google Calendar API work via the same OAuth token as Gmail: read today/upcoming/specific-date events, create (with auto Meet links), search, update, delete, recurring events, join upcoming Meet; confirmed end-to-end through Telegram /goal — real API call, honest empty result matching actual calendar state, not fabricated)
- ✅ Email Agent (tested — thin wrapper around existing tools.gmail, which already does real Gmail API work: read unread/recent, search, send, reply, mark read, archive, delete, save draft, download attachments; confirmed end-to-end through Telegram /goal — real unread inbox pulled back live, including actual current placement/internship notifications, not fabricated)
- ✅ Finance Agent (tested — no finance tool existed inside the SHRRI repo itself, only in separate JARVIS HUD scripts; reimplemented the same proven no-API-key approach directly (Yahoo Finance chart endpoint for stocks/indices/gold, CoinGecko for crypto), with honest failure messages instead of fabricated prices when a lookup fails; confirmed end-to-end through Telegram /goal — real live NIFTY index price and % change returned, not invented; fixed a duplicate-text glitch in goal_planner.py's type description introduced by a repeated sed run during wiring, cleaned before committing)
- ✅ IoT Agent (tested — no IoT/smart-home integration existed anywhere and no MQTT broker or devices are configured; installed real paho-mqtt and built the agent around it directly (publish on/off/toggle commands, subscribe for device status), honestly reporting 'No MQTT broker configured' with real setup instructions rather than pretending to control a nonexistent device — confirmed end-to-end through Telegram /goal; ready to control real devices the moment MQTT_BROKER_HOST is added to shrri_config_local.py, same pattern as BOT_TOKEN/YOUR_ID)

## Phase 6 — Conversation Broker
- ✅ Agent Communication / Message Bus (tested — new MessageBus (runner/message_bus.py) is a thread-safe in-process pub/sub scoped per workflow_id, with subscribe(topic, cb), publish(topic, payload), history()/latest(); wired into ExecutionScheduler so every workflow auto-publishes workflow_start/task_start/task_done/task_failed/workflow_done, and every handler payload gets bus + workflow_id injected for free — zero changes needed to any of the 18 existing Phase 5 agents; ManagerAgent creates the bus and returns it in run_goal()'s result; found+fixed one real bug during testing — the live bus object was leaking into checkpoint JSON via task payload and crashing json.dumps, fixed by sanitizing a copy in _checkpoint() only, leaving the live payload untouched for handlers; confirmed end-to-end with a real single-step goal — all 4 event types fired in correct order with correct payloads)
- ✅ Agent Communication — AgentRuntime (tested — new AgentRuntime (runner/agent_runtime.py) wraps ManagerAgent's existing handlers dict directly (single source of truth, no separate registry), exposing call_agent(task_type, payload) so any agent handler can synchronously invoke another registered agent mid-task; publishes agent_call_start/agent_call_done/agent_call_failed on the same workflow MessageBus so nested calls are visible in history; injected into every task payload via ExecutionScheduler alongside bus/workflow_id, with the same checkpoint-sanitize fix applied proactively since AgentRuntime isn't JSON-serializable either; confirmed end-to-end with a real orchestrator agent calling the real Memory agent mid-task — nested call actually executed, actually saved a fact, and both agent_call_start/agent_call_done fired correctly around it in bus history)
- ✅ Retry + SupervisorAgent (tested — ExecutionScheduler now retries a failed task once (max_attempts=2) before giving up, publishing task_retry on the bus for the first failure and task_failed only after both attempts are exhausted, so transient errors self-heal instead of killing the whole workflow; confirmed with a flaky handler that fails once then succeeds — workflow completed=True, call_count=2 — and a permanently-broken handler — correctly still ends failed=True after 2 attempts; new SupervisorAgent (runner/agents/supervisor_agent.py) subscribes to task_failed on every workflow's bus (auto-attached in ManagerAgent.run_goal) and sends an immediate Telegram alert via tools/telegram_notify.send_message with workflow id, step type, and error — confirmed end-to-end with a real failing task: alert actually arrived on Telegram the moment the task failed, not just at the end of the run)
- ✅ Scratchpad (tested — new Scratchpad (runner/scratchpad.py) is a thread-safe shared key-value store scoped per workflow_id, with get/set/all/delete; injected into every task payload via ExecutionScheduler alongside bus/runtime/workflow_id (same checkpoint-sanitize treatment since it's not JSON-serializable), and created/exposed by ManagerAgent.run_goal() same as bus/runtime; confirmed end-to-end with two independent tasks (no depends_on link between them) — one wrote 'found_city: Tokyo' to the scratchpad, the other read it back correctly, proving shared state works even without a direct dependency edge, unlike {output_of_<step_id>} substitution which only sees the direct dependency chain; also confirmed checkpointing still works cleanly with scratchpad present, no serialization crash)
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
