import { useEffect, useMemo, useState } from "react";

const API_BASE = "http://localhost:8000";

const statusProgress = {
  queued: 20,
  processing: 70,
  completed: 100,
  failed: 100,
};

function formatDate(dateString) {
  if (!dateString) return "-";
  return new Date(dateString).toLocaleString();
}

function StatCard({ title, value, subtitle }) {
  return (
    <div className="card stat-card">
      <div className="stat-title">{title}</div>
      <div className="stat-value">{value}</div>
      {subtitle ? <div className="stat-subtitle">{subtitle}</div> : null}
    </div>
  );
}

function ProgressBar({ value, label }) {
  return (
    <div>
      <div className="progress-row">
        <span>{label}</span>
        <strong>{value}%</strong>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

function CacheBadge({ cacheHit }) {
  return <span className={`badge ${cacheHit ? "badge-cache-hit" : "badge-cache-miss"}`}>{cacheHit ? "Cache hit" : "Fresh call"}</span>;
}

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [activeJobId, setActiveJobId] = useState(null);
  const [activeJob, setActiveJob] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");

  async function fetchMetrics() {
    const response = await fetch(`${API_BASE}/dashboard/metrics`);
    if (!response.ok) throw new Error("Failed to fetch dashboard metrics");
    const data = await response.json();
    setMetrics(data);
  }

  async function fetchHistory() {
    const response = await fetch(`${API_BASE}/jobs?limit=20`);
    if (!response.ok) throw new Error("Failed to fetch request history");
    const data = await response.json();
    setHistory(data);
  }

  async function fetchJob(jobId) {
    const response = await fetch(`${API_BASE}/jobs/${jobId}`);
    if (!response.ok) throw new Error("Failed to fetch current job");
    const data = await response.json();
    setActiveJob(data);
    return data;
  }

  async function refreshDashboard() {
    await Promise.all([fetchMetrics(), fetchHistory()]);
  }

  useEffect(() => {
    refreshDashboard().catch((err) => setError(err.message));
    const interval = setInterval(() => {
      refreshDashboard().catch((err) => setError(err.message));
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!activeJobId) return;
    let interval = null;

    const poll = async () => {
      try {
        const job = await fetchJob(activeJobId);
        await refreshDashboard();
        if (["completed", "failed"].includes(job.status)) {
          clearInterval(interval);
        }
      } catch (err) {
        setError(err.message);
        clearInterval(interval);
      }
    };

    poll();
    interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, [activeJobId]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (!prompt.trim()) {
      setError("Please enter a prompt.");
      return;
    }

    try {
      setSubmitting(true);
      setActiveJob(null);
      const response = await fetch(`${API_BASE}/prompts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, metadata: { source: "react-dashboard" } }),
      });
      if (!response.ok) throw new Error("Failed to submit prompt");
      const data = await response.json();
      setActiveJobId(data.job_id);
      setPrompt("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  const activeProgress = activeJob?.progress ?? (activeJob?.status ? statusProgress[activeJob.status] : 0);

  const derivedSummary = useMemo(() => {
    const completed = history.filter((item) => item.status === "completed").length;
    const cacheHits = history.filter((item) => item.cache_hit).length;
    return {
      completed,
      cacheHits,
      cacheRate: completed ? Math.round((cacheHits / completed) * 100) : 0,
    };
  }, [history]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>Prompt Processing Dashboard</h1>
        <p className="muted">
          Monitor prompt execution, request history, cache efficiency, and current provider rate limit usage.
        </p>

        <div className="card side-card">
          <div className="panel-title">Quick summary</div>
          <div className="summary-grid">
            <div>
              <span className="summary-label">Completed</span>
              <strong>{derivedSummary.completed}</strong>
            </div>
            <div>
              <span className="summary-label">Cache hits</span>
              <strong>{derivedSummary.cacheHits}</strong>
            </div>
            <div>
              <span className="summary-label">Cache rate</span>
              <strong>{derivedSummary.cacheRate}%</strong>
            </div>
          </div>
        </div>
      </aside>

      <main className="content">
        <section className="hero-grid">
          <StatCard title="Total jobs" value={metrics?.total_jobs ?? "-"} subtitle="All requests received" />
          <StatCard title="Queued" value={metrics?.queued_jobs ?? "-"} subtitle="Waiting for workers" />
          <StatCard title="Processing" value={metrics?.processing_jobs ?? "-"} subtitle="Currently running" />
          <StatCard title="Cache hit rate" value={metrics ? `${metrics.cache_hit_rate_percent}%` : "-"} subtitle="Completed jobs served from cache" />
        </section>

        <section className="grid-two">
          <div className="card">
            <div className="panel-title">Submit a prompt</div>
            <form onSubmit={handleSubmit} className="stack-gap">
              <textarea
                className="prompt-input"
                rows="7"
                placeholder="Ask the system to summarize a design doc, explain a concept, or generate an answer..."
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
              />
              <button className="primary-button" disabled={submitting}>
                {submitting ? "Submitting..." : "Submit request"}
              </button>
            </form>
            {error ? <div className="error-banner">{error}</div> : null}
          </div>

          <div className="card">
            <div className="panel-title">Rate limit visualization</div>
            <ProgressBar value={Math.round(metrics?.rate_limit?.usage_percent ?? 0)} label="Current minute usage" />
            <div className="rate-limit-meta">
              <div><strong>Used:</strong> {metrics?.rate_limit?.used_in_current_window ?? 0}</div>
              <div><strong>Remaining:</strong> {metrics?.rate_limit?.remaining_in_current_window ?? 0}</div>
              <div><strong>Limit:</strong> {metrics?.rate_limit?.limit_per_minute ?? 300}/min</div>
              <div><strong>Resets in:</strong> {metrics?.rate_limit?.seconds_until_reset ?? 0}s</div>
            </div>
          </div>
        </section>

        <section className="grid-two">
          <div className="card">
            <div className="panel-title">Live request status</div>
            {!activeJob ? (
              <div className="empty-state">Submit a prompt to see live progress here.</div>
            ) : (
              <div className="stack-gap">
                <div className="job-header-row">
                  <div>
                    <div className="job-id">Job ID: {activeJob.id}</div>
                    <div className="muted">{activeJob.current_stage || "Processing"}</div>
                  </div>
                  <div className="badge-stack">
                    <StatusBadge status={activeJob.status} />
                    {activeJob.status === "completed" ? <CacheBadge cacheHit={activeJob.cache_hit} /> : null}
                  </div>
                </div>
                <ProgressBar value={activeProgress} label="Execution progress" />
                <div>
                  <div className="section-label">Prompt</div>
                  <div className="code-block">{activeJob.prompt}</div>
                </div>
                {activeJob.response_text ? (
                  <div>
                    <div className="section-label">Result</div>
                    <div className="result-block">{activeJob.response_text}</div>
                  </div>
                ) : null}
                {activeJob.error_message ? (
                  <div className="error-banner">{activeJob.error_message}</div>
                ) : null}
              </div>
            )}
          </div>

          <div className="card">
            <div className="panel-title">Cache efficiency</div>
            <div className="cache-overview">
              <div className="cache-pill success">Cache hits: {metrics?.cache_hits ?? 0}</div>
              <div className="cache-pill">Avg similarity: {metrics?.average_similarity_score ?? "-"}</div>
            </div>
            <p className="muted">
              Repeating or semantically similar prompts can return faster from the cache instead of calling the LLM provider.
            </p>
          </div>
        </section>

        <section className="card">
          <div className="panel-title">Request history</div>
          <div className="history-table-wrapper">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Created</th>
                  <th>Prompt</th>
                  <th>Status</th>
                  <th>Progress</th>
                  <th>Cache</th>
                  <th>Provider</th>
                </tr>
              </thead>
              <tbody>
                {history.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="empty-row">No requests yet.</td>
                  </tr>
                ) : (
                  history.map((job) => (
                    <tr key={job.id} onClick={() => { setActiveJobId(job.id); setActiveJob(job); }}>
                      <td>{formatDate(job.created_at)}</td>
                      <td className="prompt-cell" title={job.prompt}>{job.prompt}</td>
                      <td><StatusBadge status={job.status} /></td>
                      <td>
                        <div className="table-progress">
                          <div className="table-progress-track">
                            <div className="table-progress-fill" style={{ width: `${job.progress ?? statusProgress[job.status] ?? 0}%` }} />
                          </div>
                          <span>{job.progress ?? statusProgress[job.status] ?? 0}%</span>
                        </div>
                      </td>
                      <td>{job.status === "completed" ? <CacheBadge cacheHit={job.cache_hit} /> : "-"}</td>
                      <td>{job.provider_name || "-"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
