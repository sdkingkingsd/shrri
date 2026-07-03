import { Cpu, Smartphone, GitBranch, Calendar, Mail, DollarSign, Radio, Terminal, ChevronDown, ChevronRight } from "lucide-react"
import { useState } from "react"

const GROUPS = [
  { name: "System", icon: Cpu, agents: ["Linux", "Filesystem", "Process"] },
  { name: "Comms", icon: Mail, agents: ["Email", "Calendar", "Telegram"] },
  { name: "Dev", icon: GitBranch, agents: ["GitHub", "Browser"] },
  { name: "Mobile & IoT", icon: Smartphone, agents: ["Android/adb", "MQTT/IoT"] },
  { name: "Finance", icon: DollarSign, agents: ["Finance"] },
]

export default function Sidebar({ pinnedAgent, onPin }) {
  const [open, setOpen] = useState(() => Object.fromEntries(GROUPS.map(g => [g.name, true])))
  const toggle = (name) => setOpen(o => ({ ...o, [name]: !o[name] }))

  return (
    <div style={{ width: 220, background: "#181825", borderRight: "1px solid #313244", padding: "16px 10px", overflowY: "auto" }}>
      <div style={{ fontSize: 11, color: "#6c7086", fontWeight: 700, letterSpacing: 1, padding: "0 8px 10px" }}>AGENTS</div>
      {GROUPS.map(g => (
        <div key={g.name} style={{ marginBottom: 6 }}>
          <div
            onClick={() => toggle(g.name)}
            style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 8px", cursor: "pointer", color: "#a6adc8", fontSize: 12, fontWeight: 600 }}
          >
            {open[g.name] ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            <g.icon size={14} />
            {g.name}
          </div>
          {open[g.name] && g.agents.map(a => (
            <div
              key={a}
              onClick={() => onPin(a)}
              style={{
                padding: "6px 10px 6px 28px", fontSize: 13, cursor: "pointer", borderRadius: 6,
                background: pinnedAgent === a ? "#6366f1" : "transparent",
                color: pinnedAgent === a ? "#fff" : "#cdd6f4",
                marginBottom: 2
              }}
            >
              {a}
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
