import { PanelRightOpen, PanelRightClose } from "lucide-react"

export default function TopBar({ drawerOpen, setDrawerOpen }) {
  return (
    <div style={{ background: "#1e1e2e", borderBottom: "1px solid #313244", padding: "12px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div>
        <span style={{ fontSize: 18, fontWeight: 800, color: "#cba6f7" }}>SHRRI</span>
        <span style={{ fontSize: 12, color: "#6c7086", marginLeft: 8 }}>AI OS v2</span>
      </div>
      <div onClick={() => setDrawerOpen(o => !o)} style={{ cursor: "pointer", color: "#a6adc8" }}>
        {drawerOpen ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}
      </div>
    </div>
  )
}
