import { useState, useEffect } from "react";

const API = "http://localhost:8000";

interface Workflow {
  workflow_id: string;
  workflow_name: string;
  status: string;
  steps?: number;
  configs?: number;
  created_at?: string;
  error?: string;
}

interface SimDashboardProps {
  onOpenSimulation: (workflowId: string) => void;
  onCreateNew: () => void;
  onBack: () => void;
}

export default function SimDashboard({ onOpenSimulation, onCreateNew, onBack }: SimDashboardProps) {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);

  async function fetchWorkflows() {
    try {
      const res = await fetch(`${API}/sim/workflows`);
      const data = await res.json();
      setWorkflows(data.workflows || []);
    } catch {
      setWorkflows([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchWorkflows();
    const interval = setInterval(fetchWorkflows, 3000);
    return () => clearInterval(interval);
  }, []);

  const statusBadge = (status: string) => {
    const colors: Record<string, { bg: string; text: string }> = {
      processing: { bg: "#FEF3C7", text: "#92400E" },
      done: { bg: "#D1FAE5", text: "#065F46" },
      failed: { bg: "#FEE2E2", text: "#991B1B" },
    };
    const c = colors[status] || { bg: "#E5E7EB", text: "#374151" };
    return (
      <span style={{
        padding: "2px 10px", borderRadius: 12, fontSize: 11, fontWeight: 600,
        backgroundColor: c.bg, color: c.text,
      }}>
        {status === "processing" ? "⏳ Processing" : status === "done" ? "✅ Done" : "❌ Failed"}
      </span>
    );
  };

  return (
    <div style={styles.container}>
      <div style={styles.panel}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <div>
            <button onClick={onBack} style={styles.backBtn}>← Back</button>
            <h2 style={styles.title}>🧠 Simulations</h2>
          </div>
          <button onClick={onCreateNew} style={styles.createBtn}>+ Create New</button>
        </div>

        {loading ? (
          <p style={{ color: "#9CA3AF", textAlign: "center" }}>Loading...</p>
        ) : workflows.length === 0 ? (
          <div style={{ textAlign: "center", padding: 40 }}>
            <p style={{ color: "#6B7280", fontSize: 16 }}>No simulations yet</p>
            <p style={{ color: "#9CA3AF", fontSize: 13, marginTop: 4 }}>Click "Create New" to get started</p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {workflows.map((wf) => (
              <div key={wf.workflow_id} style={styles.card}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <p style={styles.wfName}>{wf.workflow_name}</p>
                    <p style={styles.wfId}>{wf.workflow_id}</p>
                  </div>
                  {statusBadge(wf.status)}
                </div>
                <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
                  {wf.configs != null && <span style={styles.stat}>📱 {wf.configs} screens</span>}
                  {wf.steps != null && <span style={styles.stat}>📋 {wf.steps} steps</span>}
                </div>
                {wf.error && <p style={styles.error}>Error: {wf.error}</p>}
                {wf.status === "done" && (
                  <button onClick={() => onOpenSimulation(wf.workflow_id)} style={styles.openBtn}>
                    ▶ Open Simulation
                  </button>
                )}
                {wf.status === "processing" && (
                  <p style={{ color: "#92400E", fontSize: 12, marginTop: 8 }}>⏳ AI is generating screens... refresh in a moment</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh", background: "#111827",
    display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "32px 16px",
  },
  panel: { maxWidth: 600, width: "100%", background: "#1F2937", borderRadius: 16, padding: 24 },
  backBtn: { background: "none", border: "none", color: "#9CA3AF", cursor: "pointer", fontSize: 14, padding: 0, marginBottom: 8, display: "block" },
  title: { color: "white", fontSize: 22, fontWeight: "bold", margin: 0 },
  createBtn: {
    background: "#7C3AED", color: "white", border: "none", borderRadius: 10,
    padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer",
  },
  card: {
    background: "#374151", borderRadius: 12, padding: 16,
  },
  wfName: { color: "white", fontSize: 16, fontWeight: 600, margin: 0 },
  wfId: { color: "#6B7280", fontSize: 11, margin: "2px 0 0", fontFamily: "monospace" },
  stat: { color: "#9CA3AF", fontSize: 12 },
  error: { color: "#FCA5A5", fontSize: 12, marginTop: 6 },
  openBtn: {
    marginTop: 10, background: "#2563EB", color: "white", border: "none",
    borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer",
  },
};
