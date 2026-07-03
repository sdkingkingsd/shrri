import { useState, useRef, useEffect } from "react"
import { Send, Terminal as TerminalIcon, Mic } from "lucide-react"

export default function ChatPanel({ pinnedAgent }) {
  const [messages, setMessages] = useState([
    { role: "shrri", text: "SHRRI online. Type a goal or use /goal <task>." }
  ])
  const [input, setInput] = useState("")
  const bottomRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages])

  const send = async () => {
    if (!input.trim()) return
    const text = pinnedAgent ? `[${pinnedAgent}] ${input}` : input
    setMessages(m => [...m, { role: "user", text }])
    setInput("")
    // Wire this fetch to your FastAPI /api/goal endpoint
    try {
      const r = await fetch("/api/goal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: text, agent: pinnedAgent || null })
      })
      const data = await r.json()
      setMessages(m => [...m, { role: "shrri", text: data.result ?? JSON.stringify(data) }])
    } catch (e) {
      setMessages(m => [...m, { role: "shrri", text: `⚠️ /api/goal not reachable yet: ${e.message}` }])
    }
  }

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", background: "#11111b" }}>
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
        {messages.map((m, i) => (
          <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start", marginBottom: 12 }}>
            <div style={{
              maxWidth: "70%", padding: "10px 14px", borderRadius: 10, fontSize: 14, lineHeight: 1.5,
              background: m.role === "user" ? "#6366f1" : "#1e1e2e",
              color: m.role === "user" ? "#fff" : "#cdd6f4",
              border: m.role === "user" ? "none" : "1px solid #313244"
            }}>
              {m.text}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div style={{ padding: "14px 24px", borderTop: "1px solid #313244", background: "#181825", display: "flex", gap: 8, alignItems: "center" }}>
        {pinnedAgent && (
          <span style={{ fontSize: 11, background: "#313244", color: "#cba6f7", padding: "4px 8px", borderRadius: 6 }}>{pinnedAgent}</span>
        )}
        <TerminalIcon size={16} color="#6c7086" />
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && send()}
          placeholder="/goal check my email and summarize unread"
          style={{ flex: 1, background: "#11111b", border: "1px solid #313244", borderRadius: 8, padding: "10px 12px", color: "#cdd6f4", fontSize: 14, outline: "none" }}
        />
        <Mic size={18} color="#6c7086" style={{ cursor: "pointer" }} />
        <button onClick={send} style={{ background: "#6366f1", border: "none", borderRadius: 8, padding: "10px 14px", cursor: "pointer" }}>
          <Send size={16} color="#fff" />
        </button>
      </div>
    </div>
  )
}
