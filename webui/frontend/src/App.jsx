import { useState } from "react"
import TopBar from "./TopBar.jsx"
import Sidebar from "./Sidebar.jsx"
import ChatPanel from "./ChatPanel.jsx"
import Dashboard from "./Dashboard.jsx"

export default function App() {
  const [drawerOpen, setDrawerOpen] = useState(true)
  const [pinnedAgent, setPinnedAgent] = useState(null)

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", fontFamily: "Inter, system-ui, sans-serif" }}>
      <TopBar drawerOpen={drawerOpen} setDrawerOpen={setDrawerOpen} />
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <Sidebar pinnedAgent={pinnedAgent} onPin={setPinnedAgent} />
        <ChatPanel pinnedAgent={pinnedAgent} />
        {drawerOpen && (
          <div style={{ width: 420, overflowY: "auto", borderLeft: "1px solid #313244" }}>
            <Dashboard />
          </div>
        )}
      </div>
    </div>
  )
}
