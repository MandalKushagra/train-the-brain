import { useState } from "react";
import Simulator from "./Simulator";
import { manifest as hardcodedManifest } from "./manifest";

const API = "http://localhost:8000";

export default function App() {
  const [mode, setMode] = useState("menu");
  const [liveData, setLiveData] = useState(null as any);
  const [err, setErr] = useState("");

  async function goLive() {
    setMode("loading");
    setErr("");
    try {
      const r = await fetch(API + "/generate-with-defaults", { method: "POST" });
      if (!r.ok) throw new Error("API " + r.status);
      const d = await r.json();
      setLiveData(d.manifest);
      setMode("live");
    } catch (e: any) {
      setErr(e.message + " — is backend running?");
      setMode("menu");
    }
  }

  if (mode === "loading") {
    return (
      <div style={{ minHeight: "100vh", background: "#111827", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🧠</div>
          <p style={{ color: "white", fontSize: 18 }}>AI generating training...</p>
          <p style={{ color: "#9CA3AF", fontSize: 14, marginTop: 8 }}>~30 seconds</p>
        </div>
      </div>
    );
  }

  if (mode === "demo") {
    return <Simulator manifest={hardcodedManifest} onBack={() => setMode("menu")} />;
  }

  if (mode === "live" && liveData) {
    return <Simulator manifest={liveData} onBack={() => setMode("menu")} />;
  }

  return (
    <div style={{ minHeight: "100vh", background: "#111827", display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
      <div style={{ maxWidth: 384, width: "100%", textAlign: "center" }}>
        <div style={{ fontSize: 56, marginBottom: 12 }}>🧠</div>
        <h1 style={{ color: "white", fontSize: 24, fontWeight: "bold" }}>Train the Brain</h1>
        <p style={{ color: "#9CA3AF", marginTop: 4, marginBottom: 32 }}>Interactive Training Simulator</p>

        <button onClick={() => setMode("demo")} style={{ width: "100%", padding: "14px 0", marginBottom: 16, background: "#2563EB", color: "white", fontSize: 18, fontWeight: "bold", border: "none", borderRadius: 12, cursor: "pointer" }}>
          ▶ Demo Mode
        </button>

        <button onClick={goLive} style={{ width: "100%", padding: "14px 0", marginBottom: 16, background: "#16A34A", color: "white", fontSize: 18, fontWeight: "bold", border: "none", borderRadius: 12, cursor: "pointer" }}>
          🤖 Generate Live
        </button>

        <p style={{ color: "#6B7280", fontSize: 13 }}>Demo = pre-built. Live = AI pipeline real-time.</p>

        {err && <div style={{ marginTop: 16, padding: 12, background: "#7F1D1D", color: "#FCA5A5", borderRadius: 8, fontSize: 14 }}>{err}</div>}
      </div>
    </div>
  );
}
