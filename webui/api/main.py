"""
SHRRI Web UI — FastAPI backend
Serves metrics, traces, logs, device status, memory browser.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os, sys, asyncio
sys.path.insert(0, os.path.expanduser("~/shrri"))

app = FastAPI(title="SHRRI AI OS", version="2.0")
from engine import SHRRIEngine
_shrri_engine = SHRRIEngine()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/api/goal")
async def api_goal(payload: dict):
    message = payload.get("goal", "")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: _shrri_engine.chat(message))
    return {"result": result}

@app.get("/api/status")
def status():
    from engine.device_api import DeviceAPI
    d = DeviceAPI()
    return {
        "system": d.system_info(),
        "memory": d.memory(),
        "cpu": d.cpu(),
        "battery": d.battery(),
        "disk": d.disk(),
        "wifi": d.wifi(),
    }

@app.get("/api/metrics")
def metrics():
    from engine.metrics import get_provider_metrics, get_benchmark_metrics, get_tool_usage_metrics
    return {
        "providers": get_provider_metrics(),
        "benchmarks": get_benchmark_metrics(),
        "tools": get_tool_usage_metrics(),
    }

@app.get("/api/traces")
def traces(n: int = 20):
    from engine.tracer import Tracer
    return Tracer().recent(n)

@app.get("/api/logs")
def logs(n: int = 30, level: str = None):
    from engine.structured_log import StructuredLogger
    return StructuredLogger().tail(n, level)

@app.get("/api/audit")
def audit(n: int = 30):
    from engine.audit_log import AuditLog
    return AuditLog().recent(n)

@app.get("/api/memory")
def memory_browser():
    from engine.memory import Memory
    m = Memory()
    facts = m.get_all_facts()
    return {"facts": facts, "count": len(facts)}

@app.get("/api/benchmark/run")
def run_benchmark():
    from engine.self_benchmark import SelfBenchmark
    return SelfBenchmark().run(verbose=False)

@app.get("/api/plugins")
def plugins():
    from engine.plugin_registry import PluginRegistry
    return PluginRegistry().list_all()

@app.get("/api/experiments")
def experiments():
    from engine.experiments import Experiments
    return Experiments().list_all()

@app.get("/api/dashboard")
def dashboard():
    from engine.eval_dashboard import dashboard as _d
    return {"text": _d()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7788, reload=True)

# Serve React build
import os as _os
_static = _os.path.join(_os.path.dirname(__file__), "..", "static")
if _os.path.exists(_static):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    app.mount("/assets", StaticFiles(directory=_os.path.join(_static, "assets")), name="assets")

    @app.get("/")
    def root():
        return FileResponse(_os.path.join(_static, "index.html"))
