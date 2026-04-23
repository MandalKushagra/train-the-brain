import { useState, useEffect } from "react";
import Simulator from "./Simulator";
import AdminPanel from "./AdminPanel";
import DynamicSimulator from "./DynamicSimulator";
import AdminForm from "./AdminForm";
import SimDashboard from "./SimDashboard";
import { manifest as hardcodedManifest } from "./manifest";

const API = "http://localhost:8000";

type AppMode = "menu" | "loading" | "demo" | "live" | "admin-login" | "admin" | "training-link" | "training-complete" | "dashboard" | "create-sim" | "dynamic";

export default function App() {
  const [mode, setMode] = useState<AppMode>("menu");
  const [liveData, setLiveData] = useState<any>(null);
  const [dynamicData, setDynamicData] = useState<any>(null);
  const [err, setErr] = useState("");
  const [adminKey, setAdminKey] = useState("");
  const [adminKeyInput, setAdminKeyInput] = useState("");
  const [trainingData, setTrainingData] = useState<any>(null);
  const [linkToken, setLinkToken] = useState("");
  const [completionData, setCompletionData] = useState<any>(null);

  useEffect(() => {
    const path = window.location.pathname;
    if (path.startsWith("/t/")) {
      const token = path.slice(3);
      setLinkToken(token);
      loadTrainingLink(token);
    }
  }, []);

  async function loadTrainingLink(token: string) {
    setMode("loading");
    try {
      const r = await fetch(API + `/t/${token}`);
      if (!r.ok) throw new Error("Invalid or expired training link");
      const data = await r.json();
      if (data.status === "completed") {
        setCompletionData(data);
        setMode("training-complete");
      } else {
        setTrainingData(data);
        await fetch(API + `/t/${token}/start`, { method: "POST" });
        setMode("training-link");
      }
    } catch (e: any) {
      setErr(e.message);
      setMode("menu");
    }
  }

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

  function handleAdminLogin() {
    if (adminKeyInput.trim()) {
      setAdminKey(adminKeyInput.trim());
      setMode("admin");
    }
  }

  async function handleOpenSimulation(workflowId: string) {
    try {
      const res = await fetch(`${API}/sim/manifest/${workflowId}`);
      if (!res.ok) throw new Error("Failed to load manifest");
      const manifest = await res.json();
      setDynamicData(manifest);
      setMode("dynamic");
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function handleTrainingComplete(completionPayload: any) {
    if (linkToken) {
      try {
        await fetch(API + `/t/${linkToken}/complete`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(completionPayload),
        });
      } catch (e) {
        console.error("Failed to submit completion:", e);
      }
    }
    setCompletionData(completionPayload);
    setMode("training-complete");
  }

  if (mode === "loading") return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      <div className="text-center">
        <div className="text-5xl mb-4 animate-spin">🧠</div>
        <p className="text-white text-lg">Loading training...</p>
      </div>
    </div>
  );

  if (mode === "admin-login") return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-sm w-full text-center">
        <div className="text-5xl mb-3">🔐</div>
        <h1 className="text-white text-2xl font-bold mb-6">Admin Access</h1>
        <input type="password" value={adminKeyInput}
          onChange={(e) => setAdminKeyInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdminLogin()}
          placeholder="Enter admin key"
          className="w-full bg-gray-800 text-white rounded-xl px-4 py-3 border border-gray-700 mb-3" />
        <button onClick={handleAdminLogin}
          className="w-full bg-blue-600 text-white px-6 py-3 rounded-xl font-semibold text-lg mb-3">
          Enter Admin Panel
        </button>
        <button onClick={() => setMode("menu")}
          className="w-full bg-gray-700 text-gray-300 px-6 py-3 rounded-xl font-semibold">Back</button>
      </div>
    </div>
  );

  if (mode === "admin") return <AdminPanel adminKey={adminKey} onBack={() => setMode("menu")} />;

  if (mode === "dashboard") return (
    <SimDashboard
      onOpenSimulation={handleOpenSimulation}
      onCreateNew={() => setMode("create-sim")}
      onBack={() => setMode("menu")}
    />
  );

  if (mode === "create-sim") return (
    <AdminForm onSubmitted={() => setMode("dashboard")} onBack={() => setMode("dashboard")} />
  );

  if (mode === "dynamic" && dynamicData) return (
    <DynamicSimulator manifest={dynamicData} onBack={() => setMode("dashboard")} />
  );

  if (mode === "demo") return <Simulator manifest={hardcodedManifest} onBack={() => setMode("menu")} />;
  if (mode === "live" && liveData) return <Simulator manifest={liveData} onBack={() => setMode("menu")} />;

  if (mode === "training-link" && trainingData) return (
    <div>
      <div className="bg-gray-800 text-center py-2 text-sm text-gray-400">
        Training for: <span className="text-white font-medium">{trainingData.operator_name}</span>
        {" · "}{trainingData.simulation_name}
      </div>
      <Simulator manifest={trainingData.manifest} assessment={trainingData.assessment}
        onBack={() => setMode("menu")} onComplete={handleTrainingComplete} />
    </div>
  );

  if (mode === "training-complete") return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl p-8 max-w-sm w-full text-center">
        <div className="text-6xl mb-4">🎉</div>
        <h2 className="text-2xl font-bold mb-2">Training Complete!</h2>
        {completionData && completionData.quiz_score != null && (
          <div className="bg-green-50 rounded-xl p-6 mb-4">
            <p className="text-4xl font-bold text-green-600">{completionData.quiz_score}/{completionData.total_questions}</p>
            <p className="text-sm text-green-700 mt-1">Quiz Score</p>
          </div>
        )}
        <p className="text-gray-500 text-sm">You can close this window now.</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-sm w-full text-center">
        <div className="text-5xl mb-3">🧠</div>
        <h1 className="text-white text-2xl font-bold">Train the Brain</h1>
        <p className="text-gray-400 mt-1 mb-8">Interactive Training Simulator</p>
        <button onClick={() => setMode("dashboard")}
          className="w-full bg-purple-600 text-white px-6 py-4 rounded-xl font-semibold text-lg mb-3">
          ✨ Simulations Dashboard
        </button>
        <button onClick={() => setMode("demo")}
          className="w-full bg-blue-600 text-white px-6 py-4 rounded-xl font-semibold text-lg mb-3">
          ▶️ Demo Mode
        </button>
        <button onClick={goLive}
          className="w-full bg-green-600 text-white px-6 py-4 rounded-xl font-semibold text-lg mb-3">
          🤖 Generate Live
        </button>
        <button onClick={() => setMode("admin-login")}
          className="w-full bg-gray-700 text-white px-6 py-4 rounded-xl font-semibold text-lg mb-3">
          🔐 Admin Panel
        </button>
        <p className="text-gray-500 text-xs mt-4">Dashboard = create & manage simulations · Demo = pre-built · Live = legacy AI</p>
        {err && <div className="mt-4 bg-red-900/50 text-red-300 px-4 py-3 rounded-xl text-sm">{err}</div>}
      </div>
    </div>
  );
}
