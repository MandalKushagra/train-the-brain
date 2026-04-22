import { useState, useEffect } from "react";

const API = "http://localhost:8000";

type Simulation = {
  id: string;
  workflow_id: string;
  workflow_name: string;
  status: string;
  created_at: string | null;
  published_at: string | null;
  assignment_count: number;
};

type Assignment = {
  assignment_id: string;
  operator_id: string;
  operator_name: string;
  simulation_name: string;
  status: string;
  training_link: string;
  assigned_at: string | null;
  completed_at: string | null;
  quiz_score?: number;
  total_questions?: number;
  passed?: boolean;
  time_taken_seconds?: number;
};

type OperatorResult = {
  operator_id: string;
  name: string;
  pending_trainings: Assignment[];
  completed_trainings: Assignment[];
  total_assigned: number;
  total_completed: number;
  total_pending: number;
};

type DashboardStats = {
  total_simulations: number;
  total_operators: number;
  total_assignments: number;
  total_completed: number;
  total_pending: number;
  completion_rate: number;
  average_quiz_score: number;
  failed_operators: number;
};

export default function AdminPanel({ adminKey, onBack }: { adminKey: string; onBack: () => void }) {
  const [tab, setTab] = useState<"dashboard" | "create" | "simulations" | "assign" | "search">("dashboard");

  const headers = { "x-admin-key": adminKey };

  const tabs = ["dashboard", "create", "simulations", "assign", "search"] as const;
  const tabLabels: Record<string, string> = {
    dashboard: "📊 Dashboard",
    create: "➕ Create",
    simulations: "📋 Simulations",
    assign: "🔗 Assign",
    search: "🔍 Search",
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Top nav */}
      <div className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center gap-4">
        <button onClick={onBack} className="text-gray-400 hover:text-white text-sm">← Back</button>
        <span className="text-lg font-bold">🧠 Admin Panel</span>
        <div className="flex-1" />
        {tabs.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              tab === t ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
            }`}>
            {tabLabels[t]}
          </button>
        ))}
      </div>

      <div className="max-w-5xl mx-auto p-6">
        {tab === "dashboard" && <DashboardTab headers={headers} />}
        {tab === "create" && <CreateTab headers={headers} onCreated={() => setTab("simulations")} />}
        {tab === "simulations" && <SimulationsTab headers={headers} />}
        {tab === "assign" && <AssignTab headers={headers} />}
        {tab === "search" && <SearchTab headers={headers} />}
      </div>
    </div>
  );
}

function CreateTab({ headers, onCreated }: { headers: Record<string, string>; onCreated: () => void }) {
  const [workflowName, setWorkflowName] = useState("");
  const [screenshots, setScreenshots] = useState<File[]>([]);
  const [prdFiles, setPrdFiles] = useState<File[]>([]);
  const [sopFiles, setSopFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<any>(null);

  function removeFile(list: File[], setList: (f: File[]) => void, idx: number) {
    setList(list.filter((_, i) => i !== idx));
  }

  async function handleSubmit() {
    if (!workflowName.trim()) { setError("Workflow name is required"); return; }
    if (prdFiles.length === 0) { setError("At least one PRD PDF is required"); return; }

    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("workflow_name", workflowName.trim());
    screenshots.forEach((f) => formData.append("screenshots", f));
    prdFiles.forEach((f) => formData.append("prd_files", f));
    sopFiles.forEach((f) => formData.append("sop_files", f));

    try {
      const r = await fetch(API + "/admin/generate-from-upload", {
        method: "POST",
        headers,
        body: formData,
      });
      if (!r.ok) {
        const err = await r.json();
        throw new Error(err.detail || "Upload failed");
      }
      setResult(await r.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  if (result) {
    return (
      <div>
        <h2 className="text-xl font-bold mb-4">Simulation Created</h2>
        <div className="bg-gray-800 rounded-xl p-6 border border-green-700 space-y-3">
          <div className="text-4xl text-center mb-2">✅</div>
          <p className="text-center text-lg font-semibold">{result.workflow_name}</p>
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div className="bg-gray-700 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold">{result.steps_generated}</div>
              <div className="text-gray-400 text-sm">Steps Generated</div>
            </div>
            <div className="bg-gray-700 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold">{result.questions_generated}</div>
              <div className="text-gray-400 text-sm">Quiz Questions</div>
            </div>
          </div>
          <p className="text-gray-400 text-sm text-center mt-2">Status: Draft — go to Simulations to publish it.</p>
          <button onClick={onCreated}
            className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold mt-4">
            Go to Simulations →
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Create New Simulation</h2>
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 space-y-5">
        {/* Workflow Name */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">Workflow Name *</label>
          <input type="text" value={workflowName} onChange={(e) => setWorkflowName(e.target.value)}
            placeholder="e.g. FTG Dimension Capture"
            className="w-full bg-gray-700 text-white rounded-lg px-4 py-2.5 border border-gray-600 focus:border-blue-500 focus:outline-none" />
        </div>

        {/* Screenshots */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">Screen Images (.png)</label>
          <p className="text-xs text-gray-500 mb-2">Upload screenshots of the app screens for this workflow</p>
          <label className="flex items-center justify-center w-full h-24 border-2 border-dashed border-gray-600 rounded-lg cursor-pointer hover:border-blue-500 transition-colors">
            <div className="text-center">
              <span className="text-2xl">🖼️</span>
              <p className="text-sm text-gray-400 mt-1">Click to select PNG files</p>
            </div>
            <input type="file" accept=".png" multiple className="hidden"
              onChange={(e) => setScreenshots((prev) => [...prev, ...Array.from(e.target.files || [])])} />
          </label>
          {screenshots.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {screenshots.map((f, i) => (
                <span key={i} className="bg-gray-700 text-sm px-3 py-1 rounded-full flex items-center gap-2">
                  🖼️ {f.name}
                  <button onClick={() => removeFile(screenshots, setScreenshots, i)} className="text-red-400 hover:text-red-300">×</button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* PRD Files */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">PRD Documents (.pdf) *</label>
          <p className="text-xs text-gray-500 mb-2">Product requirement documents describing the feature</p>
          <label className="flex items-center justify-center w-full h-24 border-2 border-dashed border-gray-600 rounded-lg cursor-pointer hover:border-blue-500 transition-colors">
            <div className="text-center">
              <span className="text-2xl">📄</span>
              <p className="text-sm text-gray-400 mt-1">Click to select PDF files</p>
            </div>
            <input type="file" accept=".pdf" multiple className="hidden"
              onChange={(e) => setPrdFiles((prev) => [...prev, ...Array.from(e.target.files || [])])} />
          </label>
          {prdFiles.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {prdFiles.map((f, i) => (
                <span key={i} className="bg-gray-700 text-sm px-3 py-1 rounded-full flex items-center gap-2">
                  📄 {f.name}
                  <button onClick={() => removeFile(prdFiles, setPrdFiles, i)} className="text-red-400 hover:text-red-300">×</button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* SOP Files */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">SOP Documents (.pdf)</label>
          <p className="text-xs text-gray-500 mb-2">Standard operating procedures (optional)</p>
          <label className="flex items-center justify-center w-full h-24 border-2 border-dashed border-gray-600 rounded-lg cursor-pointer hover:border-blue-500 transition-colors">
            <div className="text-center">
              <span className="text-2xl">📋</span>
              <p className="text-sm text-gray-400 mt-1">Click to select PDF files</p>
            </div>
            <input type="file" accept=".pdf" multiple className="hidden"
              onChange={(e) => setSopFiles((prev) => [...prev, ...Array.from(e.target.files || [])])} />
          </label>
          {sopFiles.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {sopFiles.map((f, i) => (
                <span key={i} className="bg-gray-700 text-sm px-3 py-1 rounded-full flex items-center gap-2">
                  📋 {f.name}
                  <button onClick={() => removeFile(sopFiles, setSopFiles, i)} className="text-red-400 hover:text-red-300">×</button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Submit */}
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <button onClick={handleSubmit} disabled={loading}
          className="w-full bg-green-600 text-white px-6 py-3 rounded-lg font-semibold text-lg disabled:opacity-50">
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin">🧠</span> Generating Training... (this may take a minute)
            </span>
          ) : "🚀 Generate Training Simulation"}
        </button>
      </div>
    </div>
  );
}

function DashboardTab({ headers }: { headers: Record<string, string> }) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(API + "/admin/dashboard/overview", { headers })
      .then((r) => r.json())
      .then(setStats)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-400">Loading...</p>;
  if (!stats) return <p className="text-red-400">Failed to load dashboard</p>;

  const cards = [
    { label: "Published Simulations", value: stats.total_simulations, icon: "📋" },
    { label: "Total Operators", value: stats.total_operators, icon: "👷" },
    { label: "Assignments", value: stats.total_assignments, icon: "🔗" },
    { label: "Completed", value: stats.total_completed, icon: "✅" },
    { label: "Pending", value: stats.total_pending, icon: "⏳" },
    { label: "Completion Rate", value: `${stats.completion_rate}%`, icon: "📈" },
    { label: "Avg Quiz Score", value: `${stats.average_quiz_score}%`, icon: "📝" },
    { label: "Failed (Need Review)", value: stats.failed_operators, icon: "🚩" },
  ];

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Dashboard Overview</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cards.map((c) => (
          <div key={c.label} className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-2xl mb-1">{c.icon}</div>
            <div className="text-2xl font-bold">{c.value}</div>
            <div className="text-gray-400 text-sm">{c.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SimulationsTab({ headers }: { headers: Record<string, string> }) {
  const [sims, setSims] = useState<Simulation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(API + "/admin/simulations", { headers })
      .then((r) => r.json())
      .then(setSims)
      .finally(() => setLoading(false));
  }, []);

  async function publishSim(id: string) {
    await fetch(API + `/admin/simulations/${id}/publish`, { method: "POST", headers });
    setSims((prev) => prev.map((s) => (s.id === id ? { ...s, status: "published" } : s)));
  }

  if (loading) return <p className="text-gray-400">Loading...</p>;

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Simulations</h2>
      {sims.length === 0 ? (
        <p className="text-gray-400">No simulations yet. Generate one via the AI pipeline.</p>
      ) : (
        <div className="space-y-3">
          {sims.map((s) => (
            <div key={s.id} className="bg-gray-800 rounded-xl p-4 border border-gray-700 flex items-center gap-4">
              <div className="flex-1">
                <div className="font-semibold">{s.workflow_name}</div>
                <div className="text-gray-400 text-sm">ID: {s.workflow_id} · {s.assignment_count} assigned</div>
              </div>
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                s.status === "published" ? "bg-green-900 text-green-300" : "bg-yellow-900 text-yellow-300"
              }`}>
                {s.status}
              </span>
              {s.status === "draft" && (
                <button onClick={() => publishSim(s.id)}
                  className="bg-green-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium">
                  Publish
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


function AssignTab({ headers }: { headers: Record<string, string> }) {
  const [sims, setSims] = useState<Simulation[]>([]);
  const [selectedSim, setSelectedSim] = useState("");
  const [operatorIds, setOperatorIds] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(API + "/admin/simulations", { headers })
      .then((r) => r.json())
      .then((data) => setSims(data.filter((s: Simulation) => s.status === "published")));
  }, []);

  async function handleAssign() {
    if (!selectedSim || !operatorIds.trim()) return;
    setLoading(true);
    setError("");
    setResults([]);

    const ids = operatorIds.split(/[,\n]/).map((s) => s.trim()).filter(Boolean);
    try {
      const r = await fetch(API + "/admin/assign", {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ simulation_id: selectedSim, operator_ids: ids }),
      });
      if (!r.ok) {
        const err = await r.json();
        throw new Error(err.detail || "Assignment failed");
      }
      const data = await r.json();
      setResults(data.assignments);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function copyLink(link: string) {
    navigator.clipboard.writeText(window.location.origin + link);
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Assign Training</h2>
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 space-y-4">
        <div>
          <label className="block text-sm text-gray-400 mb-1">Select Simulation</label>
          <select value={selectedSim} onChange={(e) => setSelectedSim(e.target.value)}
            className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 border border-gray-600">
            <option value="">-- Choose a published simulation --</option>
            {sims.map((s) => (
              <option key={s.id} value={s.id}>{s.workflow_name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">Operator IDs (comma or newline separated)</label>
          <textarea value={operatorIds} onChange={(e) => setOperatorIds(e.target.value)}
            placeholder="EMP001, EMP002, EMP003"
            className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 border border-gray-600 h-24 resize-none" />
        </div>
        <button onClick={handleAssign} disabled={loading || !selectedSim || !operatorIds.trim()}
          className="bg-blue-600 text-white px-6 py-2.5 rounded-lg font-semibold disabled:opacity-50">
          {loading ? "Assigning..." : "Assign Training"}
        </button>
        {error && <p className="text-red-400 text-sm">{error}</p>}
      </div>

      {results.length > 0 && (
        <div className="mt-6">
          <h3 className="text-lg font-semibold mb-3">Assignment Results</h3>
          <div className="space-y-2">
            {results.map((r, i) => (
              <div key={i} className="bg-gray-800 rounded-lg p-3 border border-gray-700 flex items-center gap-3">
                <span className={`text-lg ${r.status === "assigned" ? "" : "opacity-50"}`}>
                  {r.status === "assigned" ? "✅" : "⚠️"}
                </span>
                <div className="flex-1">
                  <span className="font-medium">{r.operator_id}</span>
                  <span className="text-gray-400 text-sm ml-2">— {r.status}</span>
                </div>
                <button onClick={() => copyLink(r.training_link)}
                  className="text-blue-400 hover:text-blue-300 text-sm">
                  📋 Copy Link
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SearchTab({ headers }: { headers: Record<string, string> }) {
  const [searchId, setSearchId] = useState("");
  const [result, setResult] = useState<OperatorResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch() {
    if (!searchId.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const r = await fetch(API + `/admin/operators/search?operator_id=${encodeURIComponent(searchId.trim())}`, { headers });
      if (!r.ok) {
        if (r.status === 404) throw new Error(`Operator '${searchId.trim()}' not found`);
        throw new Error("Search failed");
      }
      setResult(await r.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Search Operator</h2>
      <div className="flex gap-3 mb-6">
        <input value={searchId} onChange={(e) => setSearchId(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Enter operator ID (e.g. EMP001)"
          className="flex-1 bg-gray-800 text-white rounded-lg px-4 py-2.5 border border-gray-700" />
        <button onClick={handleSearch} disabled={loading || !searchId.trim()}
          className="bg-blue-600 text-white px-6 py-2.5 rounded-lg font-semibold disabled:opacity-50">
          {loading ? "..." : "Search"}
        </button>
      </div>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {result && (
        <div>
          {/* Operator header */}
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 mb-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center text-xl font-bold">
                {result.name.charAt(0).toUpperCase()}
              </div>
              <div>
                <div className="font-bold text-lg">{result.name}</div>
                <div className="text-gray-400 text-sm">ID: {result.operator_id}</div>
              </div>
              <div className="flex-1" />
              <div className="text-right">
                <div className="text-sm text-gray-400">
                  {result.total_completed}/{result.total_assigned} completed
                </div>
                <div className="text-sm text-gray-400">{result.total_pending} pending</div>
              </div>
            </div>
          </div>

          {/* Pending trainings */}
          <h3 className="text-lg font-semibold mb-2 text-yellow-400">⏳ Pending ({result.pending_trainings.length})</h3>
          {result.pending_trainings.length === 0 ? (
            <p className="text-gray-500 text-sm mb-4">No pending trainings</p>
          ) : (
            <div className="space-y-2 mb-6">
              {result.pending_trainings.map((a) => (
                <div key={a.assignment_id} className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                  <div className="flex items-center gap-3">
                    <span className="text-yellow-400">⏳</span>
                    <div className="flex-1">
                      <div className="font-medium">{a.simulation_name}</div>
                      <div className="text-gray-400 text-xs">
                        Assigned: {a.assigned_at ? new Date(a.assigned_at).toLocaleDateString() : "—"}
                        {" · "}Status: {a.status}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Completed trainings */}
          <h3 className="text-lg font-semibold mb-2 text-green-400">✅ Completed ({result.completed_trainings.length})</h3>
          {result.completed_trainings.length === 0 ? (
            <p className="text-gray-500 text-sm">No completed trainings</p>
          ) : (
            <div className="space-y-2">
              {result.completed_trainings.map((a) => (
                <div key={a.assignment_id} className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                  <div className="flex items-center gap-3">
                    <span className={a.passed ? "text-green-400" : "text-red-400"}>
                      {a.passed ? "✅" : "❌"}
                    </span>
                    <div className="flex-1">
                      <div className="font-medium">{a.simulation_name}</div>
                      <div className="text-gray-400 text-xs">
                        Completed: {a.completed_at ? new Date(a.completed_at).toLocaleDateString() : "—"}
                        {" · "}Score: {a.quiz_score}/{a.total_questions}
                        {a.time_taken_seconds != null && ` · ${Math.round(a.time_taken_seconds / 60)}min`}
                      </div>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      a.passed ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"
                    }`}>
                      {a.passed ? "PASSED" : "FAILED"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
