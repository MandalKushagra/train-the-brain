import { useState } from "react";

const API = "http://localhost:8000";

interface AdminFormProps {
  onGenerated: (data: any) => void;
  onBack: () => void;
}

export default function AdminForm({ onGenerated, onBack }: AdminFormProps) {
  const [workflowName, setWorkflowName] = useState("");
  const [githubUrls, setGithubUrls] = useState([""]);
  const [filePatterns, setFilePatterns] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!files || files.length === 0) {
      setError("Please upload at least one screenshot");
      return;
    }
    if (!workflowName.trim()) {
      setError("Please enter a workflow name");
      return;
    }

    setLoading(true);
    setError("");

    const formData = new FormData();
    formData.append("workflow_name", workflowName);
    formData.append("github_repo_urls", JSON.stringify(githubUrls.filter(u => u.trim())));
    formData.append("file_patterns", filePatterns);
    for (let i = 0; i < files.length; i++) {
      formData.append("screenshots", files[i]);
    }

    try {
      const res = await fetch(`${API}/sim/generate`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || `API error ${res.status}`);
      }
      const data = await res.json();
      onGenerated(data);
    } catch (err: any) {
      setError(err.message + " — is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🧠</div>
          <p style={{ color: "white", fontSize: 18 }}>AI generating simulation...</p>
          <p style={{ color: "#9CA3AF", fontSize: 14, marginTop: 8 }}>
            Vision AI is analyzing your screenshots
          </p>
          <p style={{ color: "#6B7280", fontSize: 12, marginTop: 4 }}>~30 seconds per screenshot</p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <button onClick={onBack} style={styles.backBtn}>← Back</button>
        <h2 style={styles.title}>🧠 Create Simulation</h2>
        <p style={styles.subtitle}>Upload screenshots and provide context for the AI pipeline</p>

        <form onSubmit={handleSubmit}>
          <label style={styles.label}>Workflow Name *</label>
          <input
            type="text"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            placeholder="e.g. FTG Dimension Capture"
            style={styles.input}
          />

          <label style={styles.label}>Screenshots * (PNG/JPG)</label>
          <input
            type="file"
            multiple
            accept="image/png,image/jpeg"
            onChange={(e) => setFiles(e.target.files)}
            style={styles.fileInput}
          />
          {files && (
            <p style={styles.fileCount}>{files.length} file(s) selected</p>
          )}

          <label style={styles.label}>GitHub Repository URLs (optional)</label>
          {githubUrls.map((url, i) => (
            <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
              <input
                type="text"
                value={url}
                onChange={(e) => {
                  const updated = [...githubUrls];
                  updated[i] = e.target.value;
                  setGithubUrls(updated);
                }}
                placeholder="https://github.com/org/repo"
                style={{ ...styles.input, flex: 1 }}
              />
              {githubUrls.length > 1 && (
                <button
                  type="button"
                  onClick={() => setGithubUrls(githubUrls.filter((_, j) => j !== i))}
                  style={{ background: "#7F1D1D", color: "#FCA5A5", border: "none", borderRadius: 8, padding: "0 12px", cursor: "pointer", fontSize: 16 }}
                >
                  ×
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={() => setGithubUrls([...githubUrls, ""])}
            style={{ background: "none", border: "1px dashed #4B5563", color: "#9CA3AF", borderRadius: 8, padding: "6px 12px", cursor: "pointer", fontSize: 12, marginTop: 4 }}
          >
            + Add another repo
          </button>

          <label style={styles.label}>File Patterns (optional)</label>
          <input
            type="text"
            value={filePatterns}
            onChange={(e) => setFilePatterns(e.target.value)}
            placeholder="src/components/**, src/screens/**"
            style={styles.input}
          />
          <p style={styles.hint}>Comma-separated glob patterns to scope code analysis</p>

          <button type="submit" style={styles.submitBtn}>
            🚀 Generate Simulation
          </button>
        </form>

        {error && <div style={styles.error}>{error}</div>}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: "#111827",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
  },
  card: {
    maxWidth: 480,
    width: "100%",
    background: "#1F2937",
    borderRadius: 16,
    padding: 32,
  },
  backBtn: {
    background: "none",
    border: "none",
    color: "#9CA3AF",
    cursor: "pointer",
    fontSize: 14,
    marginBottom: 16,
    padding: 0,
  },
  title: {
    color: "white",
    fontSize: 24,
    fontWeight: "bold",
    margin: "0 0 4px",
  },
  subtitle: {
    color: "#9CA3AF",
    fontSize: 14,
    margin: "0 0 24px",
  },
  label: {
    display: "block",
    color: "#D1D5DB",
    fontSize: 13,
    fontWeight: 600,
    marginBottom: 6,
    marginTop: 16,
  },
  input: {
    width: "100%",
    padding: "10px 12px",
    background: "#374151",
    border: "1px solid #4B5563",
    borderRadius: 8,
    color: "white",
    fontSize: 14,
    boxSizing: "border-box" as const,
  },
  fileInput: {
    width: "100%",
    padding: "10px 0",
    color: "#D1D5DB",
    fontSize: 14,
  },
  fileCount: {
    color: "#6EE7B7",
    fontSize: 12,
    margin: "4px 0 0",
  },
  hint: {
    color: "#6B7280",
    fontSize: 11,
    margin: "4px 0 0",
  },
  submitBtn: {
    width: "100%",
    padding: "14px 0",
    marginTop: 28,
    background: "#2563EB",
    color: "white",
    fontSize: 16,
    fontWeight: "bold",
    border: "none",
    borderRadius: 12,
    cursor: "pointer",
  },
  error: {
    marginTop: 16,
    padding: 12,
    background: "#7F1D1D",
    color: "#FCA5A5",
    borderRadius: 8,
    fontSize: 14,
  },
};
