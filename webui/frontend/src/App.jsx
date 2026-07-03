import { useState, useEffect } from "react"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from "recharts"
import { Cpu, Battery, Wifi, HardDrive, MemoryStick, Activity, Shield, Database, Layers, Terminal } from "lucide-react"

const API = ""

function useFetch(url, interval = 0) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const load = () => fetch(API + url).then(r => r.json()).then(d => { setData(d); setLoading(false) }).catch(() => setLoading(false))
  useEffect(() => { load(); if (interval) { const t = setInterval(load, interval); return () => clearInterval(t) } }, [url])
  return { data, loading, reload: load }
}

function Card({ title, icon: Icon, children, color = "#6366f1" }) {
  return (
    <div style={{ background: "#1e1e2e", border: "1px solid #313244", borderRadius: 12, padding: 20, marginBottom: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14, color }}>
        {Icon && <Icon size={18} />}
        <span style={{ fontWeight: 600, fontSize: 14, letterSpacing: 0.5 }}>{title}</span>
      </div>
      {children}
    </div>
  )
}

function Stat({ label, value, sub }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <span style={{ color: "#a6adc8", fontSize: 12 }}>{label}: </span>
      <span style={{ color: "#cdd6f4", fontWeight: 600 }}>{value}</span>
      {sub && <span style={{ color: "#6c7086", fontSize: 11, marginLeft: 6 }}>{sub}</span>}
    </div>
  )
}

function Badge({ ok }) {
  return <span style={{ background: ok ? "#a6e3a1" : "#f38ba8", color: "#1e1e2e", borderRadius: 4, padding: "1px 6px", fontSize: 11, fontWeight: 700 }}>{ok ? "OK" : "FAIL"}</span>
}

// ── Tabs ──
const TABS = ["Overview", "Metrics", "Traces", "Logs", "Audit", "Memory"]

export default function App() {
  const [tab, setTab] = useState("Overview")
  const { data: status } = useFetch("/api/status", 10000)
  const { data: metrics } = useFetch("/api/metrics", 30000)
  const { data: traces } = useFetch("/api/traces?n=20", 15000)
  const { data: logs } = useFetch("/api/logs?n=30", 15000)
  const { data: audit } = useFetch("/api/audit?n=20", 20000)
  const { data: memory } = useFetch("/api/memory", 60000)

  const tabStyle = (t) => ({
    padding: "8px 18px", cursor: "pointer", borderRadius: 8,
    background: tab === t ? "#6366f1" : "transparent",
    color: tab === t ? "#fff" : "#a6adc8",
    border: "none", fontWeight: 600, fontSize: 13
  })

  return (
    <div style={{ minHeight: "100vh", background: "#11111b", color: "#cdd6f4", fontFamily: "Inter, system-ui, sans-serif" }}>
      {/* Header */}
      <div style={{ background: "#1e1e2e", borderBottom: "1px solid #313244", padding: "16px 32px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <span style={{ fontSize: 20, fontWeight: 800, color: "#cba6f7" }}>SHRRI</span>
          <span style={{ fontSize: 13, color: "#6c7086", marginLeft: 10 }}>AI OS v2 Dashboard</span>
        </div>
        <div style={{ display: "flex", gap: 4 }}>
          {status && (
            <span style={{ fontSize: 12, color: "#a6e3a1", background: "#1e3a2e", padding: "4px 10px", borderRadius: 6 }}>
              🟢 {status.system?.hostname?.split("-")[0]} · {status.battery?.percentage} {status.battery?.state}
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ padding: "16px 32px 0", display: "flex", gap: 4, borderBottom: "1px solid #313244", background: "#181825" }}>
        {TABS.map(t => <button key={t} style={tabStyle(t)} onClick={() => setTab(t)}>{t}</button>)}
      </div>

      <div style={{ padding: 32, maxWidth: 1200, margin: "0 auto" }}>

        {/* OVERVIEW */}
        {tab === "Overview" && status && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
            <Card title="System" icon={Cpu} color="#89b4fa">
              <Stat label="Host" value={status.system?.hostname?.split("-")[0]} />
              <Stat label="OS" value={`${status.system?.os} ${status.system?.machine}`} />
              <Stat label="Python" value={status.system?.python} />
              <Stat label="Uptime" value={status.system?.uptime} />
            </Card>
            <Card title="Hardware" icon={Battery} color="#a6e3a1">
              <Stat label="Battery" value={status.battery?.percentage} sub={status.battery?.state} />
              <Stat label="RAM used" value={status.memory?.used} sub={`/ ${status.memory?.total}`} />
              <Stat label="RAM free" value={status.memory?.free} />
              <Stat label="Disk" value={`${status.disk?.used}/${status.disk?.total}`} sub={status.disk?.use_pct} />
            </Card>
            <Card title="Network & CPU" icon={Wifi} color="#f9e2af">
              <Stat label="WiFi" value={status.wifi?.ssid} />
              <Stat label="IP" value={status.wifi?.ip} />
              <Stat label="CPU" value={status.cpu?.model?.split(" with")[0]} />
              <Stat label="Cores" value={status.cpu?.cores} sub={`load ${status.cpu?.load_avg}`} />
            </Card>

            {/* Provider summary */}
            {metrics?.providers && (
              <Card title="Provider Performance" icon={Activity} color="#cba6f7" style={{ gridColumn: "span 3" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {Object.values(metrics.providers).slice(0, 5).map((p, i) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: "1px solid #313244" }}>
                      <span style={{ fontSize: 13 }}>{p.provider}/{p.model}</span>
                      <div style={{ display: "flex", gap: 16, fontSize: 12 }}>
                        <span style={{ color: "#a6adc8" }}>{p.total_calls} calls</span>
                        <span style={{ color: parseInt(p.success_rate) > 80 ? "#a6e3a1" : "#f38ba8" }}>{p.success_rate}</span>
                        <span style={{ color: "#89b4fa" }}>{p.avg_latency_s}s</span>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Benchmark */}
            {metrics?.benchmarks?.recent_runs && (
              <Card title="Benchmark History" icon={Layers} color="#89dceb">
                {metrics.benchmarks.recent_runs.map((r, i) => (
                  <div key={i} style={{ fontSize: 12, marginBottom: 4, display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "#6c7086" }}>{r.timestamp?.slice(0, 16)}</span>
                    <span style={{ color: r.score === "100%" ? "#a6e3a1" : "#f9e2af", fontWeight: 700 }}>{r.passed}/{r.total} {r.score}</span>
                  </div>
                ))}
              </Card>
            )}
          </div>
        )}

        {/* METRICS */}
        {tab === "Metrics" && metrics && (
          <div>
            <Card title="Provider Call Volume" icon={BarChart} color="#cba6f7">
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={Object.values(metrics.providers || {})}>
                  <XAxis dataKey="model" tick={{ fontSize: 10, fill: "#a6adc8" }} />
                  <YAxis tick={{ fontSize: 10, fill: "#a6adc8" }} />
                  <Tooltip contentStyle={{ background: "#1e1e2e", border: "1px solid #313244" }} />
                  <Bar dataKey="total_calls" fill="#6366f1" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
            <Card title="Tool Usage" icon={Terminal} color="#f9e2af">
              {Object.entries(metrics.tools || {}).map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: 13, padding: "4px 0", borderBottom: "1px solid #313244" }}>
                  <span>{k}</span><span style={{ color: "#89b4fa" }}>{v}×</span>
                </div>
              ))}
            </Card>
          </div>
        )}

        {/* TRACES */}
        {tab === "Traces" && (
          <Card title="Recent LLM Traces" icon={Activity} color="#89b4fa">
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ color: "#6c7086", textAlign: "left" }}>
                  {["Time", "Provider", "Model", "Capability", "Latency", "Status"].map(h => (
                    <th key={h} style={{ padding: "6px 8px", borderBottom: "1px solid #313244" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(traces || []).map((r, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid #1e1e2e" }}>
                    <td style={{ padding: "6px 8px", color: "#6c7086" }}>{r.timestamp?.slice(11)}</td>
                    <td style={{ padding: "6px 8px" }}>{r.provider}</td>
                    <td style={{ padding: "6px 8px", color: "#89b4fa" }}>{r.model}</td>
                    <td style={{ padding: "6px 8px" }}>{r.capability}</td>
                    <td style={{ padding: "6px 8px", color: "#f9e2af" }}>{r.latency_ms?.toFixed(0)}ms</td>
                    <td style={{ padding: "6px 8px" }}><Badge ok={r.success} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}

        {/* LOGS */}
        {tab === "Logs" && (
          <Card title="Structured Logs" icon={Terminal} color="#a6e3a1">
            <div style={{ fontFamily: "monospace", fontSize: 12, lineHeight: 1.8 }}>
              {(logs || []).slice().reverse().map((l, i) => {
                const col = { DEBUG: "#6c7086", INFO: "#89b4fa", WARN: "#f9e2af", ERROR: "#f38ba8" }[l.level] || "#cdd6f4"
                const icon = { DEBUG: "🔍", INFO: "ℹ️", WARN: "⚠️", ERROR: "❌" }[l.level] || ""
                return (
                  <div key={i} style={{ padding: "2px 0", borderBottom: "1px solid #181825" }}>
                    <span style={{ color: "#6c7086" }}>{l.ts?.slice(11)} </span>
                    <span style={{ color: col }}>[{l.level}] </span>
                    <span style={{ color: "#a6adc8" }}>{l.component}: </span>
                    <span>{l.msg}</span>
                  </div>
                )
              })}
            </div>
          </Card>
        )}

        {/* AUDIT */}
        {tab === "Audit" && (
          <Card title="Audit Trail" icon={Shield} color="#f38ba8">
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ color: "#6c7086", textAlign: "left" }}>
                  {["Time", "Actor", "Action", "Resource", "Result"].map(h => (
                    <th key={h} style={{ padding: "6px 8px", borderBottom: "1px solid #313244" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(audit || []).map((r, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid #1e1e2e" }}>
                    <td style={{ padding: "6px 8px", color: "#6c7086" }}>{r.timestamp?.slice(11)}</td>
                    <td style={{ padding: "6px 8px", color: "#cba6f7" }}>{r.actor}</td>
                    <td style={{ padding: "6px 8px" }}>{r.action}</td>
                    <td style={{ padding: "6px 8px", color: "#89b4fa" }}>{r.resource}</td>
                    <td style={{ padding: "6px 8px" }}><Badge ok={r.result === "ok"} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}

        {/* MEMORY */}
        {tab === "Memory" && memory && (
          <Card title={`Memory Browser (${memory.count} facts)`} icon={Database} color="#89dceb">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {Object.entries(memory.facts || {}).slice(0, 40).map(([k, v]) => (
                <div key={k} style={{ background: "#181825", borderRadius: 6, padding: "8px 12px", fontSize: 12 }}>
                  <div style={{ color: "#6c7086", marginBottom: 2 }}>{k}</div>
                  <div style={{ color: "#cdd6f4" }}>{String(v).slice(0, 80)}</div>
                </div>
              ))}
            </div>
          </Card>
        )}

      </div>
    </div>
  )
}
