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

  if (mode === "loading") return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      <div className="text-center">
        <div className="text-5xl mb-4 animate-spin">🧠</div>
        <p className="text-white text-lg">AI generating training...</p>
        <p className="text-gray-400 text-sm mt-2">~30 seconds</p>
      </div>
    </div>
  );

  if (mode === "demo") return (
    <Simulator manifest={hardcodedManifest} onBack={() => setMode("menu")} />
  );

  if (mode === "live" && liveData) return (
    <Simulator manifest={liveData} onBack={() => setMode("menu")} />
  );

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-sm w-full text-center">
        <div className="text-5xl mb-3">🧠</div>
        <h1 className="text-white text-2xl font-bold">Train the Brain</h1>
        <p className="text-gray-400 mt-1 mb-8">Interactive Training Simulator</p>
        <button onClick={() => setMode("demo")}
          className="w-full bg-blue-600 text-white px-6 py-4 rounded-xl font-semibold text-lg mb-3">
          ▶️ Demo Mode
        </button>
        <button onClick={goLive}
          className="w-full bg-green-600 text-white px-6 py-4 rounded-xl font-semibold text-lg mb-3">
          🤖 Generate Live
        </button>
        <p className="text-gray-500 text-xs mt-4">Demo = pre-built. Live = AI pipeline real-time.</p>
        {err && <div className="mt-4 bg-red-900/50 text-red-300 px-4 py-3 rounded-xl text-sm">{err}</div>}
      </div>
    </div>
  );
}
