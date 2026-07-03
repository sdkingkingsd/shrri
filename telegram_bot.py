import os, sys, asyncio, logging
sys.path.insert(0, os.path.expanduser("~/shrri"))
try:
    from shrri_config_local import BOT_TOKEN, YOUR_ID
except ImportError:
    from shrri_config import BOT_TOKEN, YOUR_ID


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from engine import SHRRIEngine

engine = SHRRIEngine()
logging.basicConfig(level=logging.WARNING)

VOICE_PID_FILE = "/tmp/shrri_voice_live.pid"


# Phase 11-16 integrations
from engine.audit_log import AuditLog
from engine.policy_engine import PolicyEngine
from engine.structured_log import StructuredLogger
from engine.tracer import Tracer
from engine.device_api import DeviceAPI
from engine.eval_dashboard import dashboard as eval_dashboard

_audit = AuditLog()
_policy = PolicyEngine()
_slog = StructuredLogger()
_tracer = Tracer()
_device = DeviceAPI()

def _voicemode_status():
    if not os.path.exists(VOICE_PID_FILE):
        return False
    try:
        with open(VOICE_PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except Exception:
        return False

async def handle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Security — only respond to you
    if update.effective_user.id != YOUR_ID:
        return


    # ── Slash commands (Phase 11-16) ──────────────────────────────
    txt = (update.message.text or "").strip()

    if txt == "/dashboard":
        _audit.log("command", "/dashboard", "ok", "user")
        await update.message.reply_text(eval_dashboard()[:4000])
        return

    if txt == "/device":
        _audit.log("command", "/device", "ok", "user")
        info = _device.system_info()
        mem  = _device.memory()
        cpu  = _device.cpu()
        bat  = _device.battery()
        disk = _device.disk()
        wifi = _device.wifi()
        lines = [
            f"🖥 *{info['hostname']}* ({info['os']} {info['machine']})",
            f"⏱ Uptime: {info.get('uptime','?')}",
            f"🔋 Battery: {bat.get('percentage','?')} ({bat.get('state','?')})",
            f"📶 WiFi: {wifi.get('ssid','?')} — {wifi.get('ip','?')}",
            f"💾 Disk: {disk.get('used','?')}/{disk.get('total','?')} ({disk.get('use_pct','?')} used)",
            f"🧠 RAM: {mem.get('used','?')}/{mem.get('total','?')} free={mem.get('free','?')}",
            f"⚡ CPU: {cpu.get('model','?')} ({cpu.get('cores','?')} cores) load={cpu.get('load_avg','?')}",
        ]
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    if txt == "/benchmark":
        _audit.log("command", "/benchmark", "ok", "user")
        await update.message.reply_text("🧪 Running benchmark...")
        import asyncio as _aio
        loop = _aio.get_event_loop()
        def _run_bench():
            from engine.self_benchmark import SelfBenchmark
            sb = SelfBenchmark()
            return sb.run(verbose=False)
        result = await loop.run_in_executor(None, _run_bench)
        bar = "█" * result["passed"] + "░" * (result["total"] - result["passed"])
        await update.message.reply_text(
            f"🧪 Benchmark: {bar} {result['passed']}/{result['total']} ({result['score']})"
        )
        return

    if txt == "/logs":
        _audit.log("command", "/logs", "ok", "user")
        await update.message.reply_text(_slog.tail_str(15))
        return

    if txt == "/audit":
        _audit.log("command", "/audit", "ok", "user")
        rows = _audit.recent(10)
        lines = ["📋 Audit Log (last 10):"]
        for r in rows:
            icon = "✅" if r["result"] == "ok" else "❌"
            lines.append(f"{icon} [{r['timestamp'][11:19]}] {r['action']} → {r['resource']}")
        await update.message.reply_text("\n".join(lines))
        return

    if txt.startswith("/policy"):
        _audit.log("command", "/policy", "ok", "user")
        import json
        summary = _policy.summary()
        lines = ["⚙️ Active Policies:"]
        for k, v in summary.items():
            lines.append(f"  {k}: {v}")
        await update.message.reply_text("\n".join(lines))
        return

    if txt == "/traces":
        _audit.log("command", "/traces", "ok", "user")
        rows = _tracer.recent(8)
        lines = ["🔍 Recent Traces:"]
        for r in rows:
            icon = "✅" if r["success"] else "❌"
            lines.append(f"{icon} {r['provider']}/{r['model']} {r['latency_ms']:.0f}ms — {r['capability']}")
        await update.message.reply_text("\n".join(lines))
        return

    if txt == "/help" or txt == "/commands":
        await update.message.reply_text(
            "🤖 *SHRRI Commands*\n\n"
            "/dashboard — eval dashboard\n"
            "/device — system status\n"
            "/benchmark — run 5-test suite\n"
            "/logs — recent structured logs\n"
            "/audit — audit trail\n"
            "/policy — active policies\n"
            "/traces — recent LLM traces\n"
            "/goal <task> — run multi-agent goal\n"
            "/editfile <path>|||<content> — edit file\n"
            "/readfile <path> — read file\n"
            "voicemode on/off — toggle voice\n",
            parse_mode="Markdown"
        )
        return

    # ── Policy check before LLM calls ─────────────────────────────
    allowed, reason = _policy.check("llm_call")
    if not allowed:
        _audit.log("llm_call", "blocked", "denied", "policy", {"reason": reason})
        await update.message.reply_text(f"❌ Blocked by policy: {reason}")
        return

    # ── Audit + log every real message ────────────────────────────
    _audit.log("message", txt[:80], "ok", "user")
    _slog.info("telegram", f"Message received", {"len": len(txt)})

    raw_text = (update.message.text or "").strip().lower()
    if raw_text in ("/voicemode on", "voice mode on", "voicemode on"):
        if _voicemode_status():
            await update.message.reply_text("Voice mode already on, da.")
        else:
            import subprocess
            proc = subprocess.Popen(
                ["python3", os.path.expanduser("~/shrri/voice_live.py")],
                stdout=open("/tmp/shrri_voice_live.log", "a"),
                stderr=subprocess.STDOUT,
                cwd=os.path.expanduser("~/shrri"),
            )
            with open(VOICE_PID_FILE, "w") as f:
                f.write(str(proc.pid))
            await update.message.reply_text("Voice mode ON da — listening continuously now.")
        return

    if raw_text in ("/voicemode off", "voice mode off", "voicemode off"):
        if not _voicemode_status():
            await update.message.reply_text("Voice mode already off, da.")
        else:
            try:
                with open(VOICE_PID_FILE) as f:
                    pid = int(f.read().strip())
                os.kill(pid, 9)
                os.remove(VOICE_PID_FILE)
                await update.message.reply_text("Voice mode OFF da.")
            except Exception as e:
                await update.message.reply_text("Couldnt stop it cleanly: " + str(e))
        return


    is_voice_input = False
    user_msg = update.message.text or ""

    if not user_msg and update.message.voice:
        is_voice_input = True
        await update.message.reply_text("\U0001F3A4 Listening...")
        voice_file = await update.message.voice.get_file()
        import tempfile, os as _os
        ogg_path = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False, dir="/tmp").name
        await voice_file.download_to_drive(ogg_path)
        from tools.voice_telegram import transcribe_ogg
        loop = asyncio.get_event_loop()
        user_msg = await loop.run_in_executor(None, transcribe_ogg, ogg_path)
        try:
            _os.remove(ogg_path)
        except Exception:
            pass
    # Photo message handler — send to Vision Agent for analysis
    if not user_msg and update.message.photo:
        await update.message.reply_text("\U0001F440 Looking at the image...")
        photo_file = await update.message.photo[-1].get_file()  # highest resolution
        import tempfile, os as _os
        img_path = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False, dir="/tmp").name
        await photo_file.download_to_drive(img_path)
        caption = update.message.caption or "Describe what you see in this image."
        from runner.agents.vision_agent import VisionAgent
        vision = VisionAgent(verbose=True)
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, lambda: vision.run({"prompt": caption, "image_path": img_path}))
        except Exception as e:
            result = f"GAP: vision agent failed — {e}"
        try:
            _os.remove(img_path)
        except Exception:
            pass
        await update.message.reply_text(result[:4000])
        return
        if not user_msg:
            await update.message.reply_text("GAP: could not understand the voice message.")
            return

    # Video message handler — send to Gemini for analysis
    if not user_msg and update.message.video:
        await update.message.reply_text("🎬 Analyzing video...")
        video_file = await update.message.video.get_file()
        import tempfile, os as _os
        mp4_path = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False, dir="/tmp").name
        await video_file.download_to_drive(mp4_path)
        caption = update.message.caption or "Summarize what is happening in this video."
        from tools.video_tool import analyze_video
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, analyze_video, mp4_path, caption)
        try:
            _os.remove(mp4_path)
        except Exception:
            pass
        await update.message.reply_text(result[:4000])
        return

    if not user_msg:
        await update.message.reply_text("Send text for now — voice coming soon!")
        return

    await update.message.reply_text("⏳ thinking...")
    # Browser commands — bypass LLM, run sync playwright in thread
    from tools.dispatcher import detect_intent, run_tool
    _intent = detect_intent(user_msg)
    from tools.self_edit import has_pending_edit, confirm_pending_edit, cancel_pending_edit, propose_edit
    if has_pending_edit():
        if user_msg.strip().lower() in ("yes", "y", "confirm", "save"):
            response = confirm_pending_edit()
        else:
            response = cancel_pending_edit()
        await update.message.reply_text(response[:4000])
        return
    if user_msg.strip().startswith("/editfile "):
        from tools.self_edit import write_file
        parts = user_msg.strip()[len("/editfile "):].split("|||", 1)
        if len(parts) != 2:
            response = "Usage: /editfile <path>|||<new content>"
        else:
            response = write_file(parts[0].strip(), parts[1])
    elif user_msg.strip().startswith("/readfile "):
        from tools.self_edit import read_file
        response = read_file(user_msg.strip()[len("/readfile "):].strip())
    elif user_msg.strip().startswith("/listbackups"):
        from tools.self_edit import list_backups
        arg = user_msg.strip()[len("/listbackups"):].strip()
        response = list_backups(arg if arg else None)
    elif user_msg.strip().startswith("/restorebackup "):
        from tools.self_edit import restore_backup
        parts = user_msg.strip()[len("/restorebackup "):].split("|||", 1)
        if len(parts) != 2:
            response = "Usage: /restorebackup <backup_filename>|||<target_path>"
        else:
            response = restore_backup(parts[0].strip(), parts[1].strip())
    elif user_msg.strip().startswith("/goal "):
        goal_text = user_msg.strip()[len("/goal "):].strip()
        loop = asyncio.get_event_loop()
        def _run_goal():
            from runner.agents.registry import build_manager
            from runner.consensus_engine import ConsensusEngine
            from runner.negotiation_engine import NegotiationEngine
            try:
                manager = build_manager(verbose=True)
                import re as _re
                # Create agent shortcut
                _dam = _re.search(r'create\s+agent:\s*(\w+)\s+that\s+(.+)', goal_text, _re.I)
                if _dam:
                    from runner.dynamic_agent_factory import DynamicAgentFactory
                    from engine.router import Router as _DRouter
                    _dag_router = _DRouter()
                    _daf = DynamicAgentFactory(_dag_router, manager)
                    return _daf.create(_dam.group(1).strip(), _dam.group(2).strip())
                # Negotiation shortcut
                _nm = _re.search(r'negotiate\s+(?:to\s+)?(?:answer|discuss|debate)?\s*:?\s*(.+)', goal_text, _re.I)
                if _nm:
                    _nq = _nm.group(1).strip()
                    _nruntime = __import__('runner.agent_runtime', fromlist=['AgentRuntime']).AgentRuntime(manager._agent_handlers)
                    from engine.router import Router as _Router
                    _nrouter = _Router()
                    _ne = NegotiationEngine(_nruntime, provider_router=_nrouter)
                    return _ne.run(_nq, agents=["research", "memory"], max_rounds=2)
                # Maps shortcut
                _mapm = _re.match(r"maps?\s*:?\s*(.+)", goal_text, _re.I | _re.S)
                if _mapm:
                    from tools.maps_tool import maps_query
                    return maps_query(_mapm.group(1).strip())

                # GitHub shortcut
                _ghm = _re.match(r"(?:github|git)\s*:?\s*(.+)", goal_text, _re.I | _re.S)
                if _ghm:
                    from tools.github_tool import github_query
                    return github_query(_ghm.group(1).strip())

                # Python/Shell exec shortcut
                _pym = _re.match(r"(?:python|exec|shell)\s*:?\s*(.+)", goal_text, _re.I | _re.S)
                if _pym:
                    _code = _pym.group(1).strip()
                    import re as _re3
                    _code = _re3.sub(r"^[`]{3}[a-z]*\n?", "", _code)
                    _code = _re3.sub(r"\n?[`]{3}$", "", _code)
                    from tools.code_sandbox import run_code
                    return run_code(_code)

                # MCP shortcut — bypass planner, go directly to mcp agent
                _mcpm = _re.match(r"mcp\s*:?\s*(.+)", goal_text, _re.I | _re.S)
                if _mcpm:
                    _mcp_prompt = _mcpm.group(1).strip()
                    from engine.mcp.mcp_client import list_tools_sync, call_tool_sync
                    import re as _re2
                    if _re2.search(r"^(list tools|list all tools|available tools|what tools|show tools)", _mcp_prompt, _re2.I):
                        _tools = list_tools_sync()
                        if not _tools:
                            return "No MCP servers connected."
                        _lines = ["MCP tools (" + str(len(_tools)) + "):"]
                        for _t in _tools:
                            _lines.append("  [" + _t["server"] + "] " + _t["name"] + " - " + _t["description"])
                        return "\n".join(_lines)
                    _m2 = _re2.match(r"(\w+):(\w+)\s*(.*)", _mcp_prompt, _re2.DOTALL)
                    if _m2:
                        _srv = _m2.group(1)
                        _tool = _m2.group(2)
                        _args_str = _m2.group(3).strip()
                        _arguments = {}
                        for _kv in _re2.findall(r"(\w+)=(\"[^\"]*\"|\S+)", _args_str):
                            _arguments[_kv[0]] = _kv[1].strip('"')
                        return call_tool_sync(_srv, _tool, _arguments)
                    return "MCP usage: /goal mcp: server:tool key=value"

                # Files shortcut — bypass planner, go directly to files agent
                _fm = _re.search(r'files?\s*:?\s*(.+)', goal_text, _re.I)
                if _fm:
                    _fq = _fm.group(1).strip()
                    from tools.file_tool import file_search, open_file
                    if "open" in _fq.lower():
                        return open_file(_fq)
                    return file_search(_fq)

                # Weather shortcut — bypass planner, go directly to weather agent
                _wm = _re.search(r'weather\s*:?\s*(?:in\s+|for\s+|at\s+)?(.+)', goal_text, _re.I)
                if _wm:
                    _loc = _wm.group(1).strip()
                    from tools.weather_tool import get_weather
                    return get_weather(_loc)

                # Consensus shortcut — bypass planner if goal explicitly requests consensus
                _cm = _re.search(r'consensus\s+(?:to\s+)?(?:answer|compare|pick)?\s*:?\s*(.+)', goal_text, _re.I)
                if _cm:
                    _q = _cm.group(1).strip()
                    _runtime = __import__('runner.agent_runtime', fromlist=['AgentRuntime']).AgentRuntime(manager._agent_handlers)
                    from engine.router import Router
                    _router = Router()
                    _ce = ConsensusEngine(_runtime, provider_router=_router)
                    return _ce.run("consensus", {"prompt": _q}, agents=["research", "memory"], strategy="llm_judge")
                result = manager.run_goal(goal_text)
            except Exception as e:
                return f"GAP: goal pipeline crashed before finishing — {type(e).__name__}: {e}"
            if result["completed"]:
                # Return the last completed task's result as the summary reply
                done_tasks = [t for t in result["tasks"] if t["status"] == "done"]
                if done_tasks:
                    return str(done_tasks[-1]["result"])
                return "Goal completed but produced no output."
            else:
                failed = [t for t in result["tasks"] if t["status"] == "failed"]
                errs = "; ".join(t["error"] for t in failed) if failed else "unknown error"
                return f"GAP: goal failed — {errs}"
        response = await loop.run_in_executor(None, _run_goal)
    elif user_msg.strip().startswith("/edit "):
        instruction = user_msg.strip()[len("/edit "):].strip()
        response = propose_edit(instruction, engine.router if hasattr(engine, "router") else engine)
    elif _intent["tool"] == "computer_use":
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: run_tool(_intent, user_msg))
        # Send screenshot as image if one was saved
        if "Screenshot saved:" in response:
            import re as _re
            _sp = _re.search(r"Screenshot saved: (.+.png)", response)
            if _sp:
                try:
                    await update.message.reply_photo(photo=open(_sp.group(1).strip(), "rb"))
                    return
                except Exception:
                    pass
    elif _intent["tool"] == "browser":
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: run_tool(_intent, user_msg))
    else:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: engine.chat(user_msg))
    if response.startswith("Screenshot saved to "):
        img_path = response.split("Screenshot saved to ")[-1].strip()
        try:
            await update.message.reply_photo(photo=open(img_path, "rb"))
        except Exception as e:
            await update.message.reply_text(f"Screenshot taken but couldn't send image: {e}")
    elif response.startswith("IMAGE_GENERATED|"):
        img_path = response.split("IMAGE_GENERATED|", 1)[-1].strip()
        try:
            await update.message.reply_photo(photo=open(img_path, "rb"))
        except Exception as e:
            await update.message.reply_text(f"Image generated but couldn't send it: {e}")
    elif is_voice_input:
        await update.message.reply_text(response[:4000])
        from tools.voice_telegram import text_to_voice_ogg
        loop = asyncio.get_event_loop()
        voice_reply_path = await loop.run_in_executor(None, text_to_voice_ogg, response)
        if voice_reply_path:
            try:
                await update.message.reply_voice(voice=open(voice_reply_path, "rb"))
            except Exception:
                pass
            try:
                import os as _os
                _os.remove(voice_reply_path)
            except Exception:
                pass
    else:
        await update.message.reply_text(response[:4000])

async def _mcp_startup(app):
    try:
        from engine.mcp.mcp_client import _startup_connect
        await _startup_connect()
        print("[mcp] All MCP servers connected at startup.")
    except Exception as e:
        print(f"[mcp] Startup connection failed: {e}")

app = ApplicationBuilder().token(BOT_TOKEN).post_init(_mcp_startup).build()
async def handle_snooze(update, ctx):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != YOUR_ID:
        return
    data = query.data  # format: "snooze|<minutes>|<task>"
    parts = data.split("|", 2)
    if len(parts) != 3 or parts[0] != "snooze":
        return
    minutes = int(parts[1])
    task = parts[2]
    from datetime import datetime, timedelta
    import pytz, subprocess
    IST = pytz.timezone("Asia/Kolkata")
    remind_time = datetime.now(IST) + timedelta(minutes=minutes)
    at_time_str = remind_time.strftime("%H:%M %Y-%m-%d")
    notify_cmd = f'python3 /home/shrridharshan/shrri/tools/telegram_notify.py "⏰ SHRRI Reminder (snoozed): {task}"'
    subprocess.run(['at', at_time_str], input=notify_cmd, text=True, capture_output=True)
    await query.edit_message_text(f"⏰ Snoozed for {minutes} minutes — I'll remind you to: {task}")

app.add_handler(MessageHandler(filters.ALL, handle))
app.add_handler(CallbackQueryHandler(handle_snooze))
print("SHRRI Telegram bot running...")
app.run_polling()
