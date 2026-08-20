"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ProviderInfo, WorkflowMode, WorkflowRun } from "@/types/ai";
import { ResultPanel } from "./ResultPanel";

interface ProvidersPayload {
  providers: ProviderInfo[];
  limits: {
    maxOutputTokens: number;
    requestTimeoutMs: number;
    maxRetries: number;
    maxTaskLength: number;
    maxProviderCallsPerRun: number;
  };
  mockEnabled: boolean;
}

const MODES: Array<{ value: WorkflowMode; label: string; hint: string }> = [
  { value: "single", label: "Single", hint: "One selected model answers." },
  { value: "parallel", label: "Parallel", hint: "All selected models answer simultaneously." },
  {
    value: "review",
    label: "Review",
    hint: "First provider drafts, second critiques, first revises.",
  },
  {
    value: "consensus",
    label: "Consensus",
    hint: "All selected models answer, then the judge produces one final answer.",
  },
];

export default function Dashboard() {
  const [meta, setMeta] = useState<ProvidersPayload | null>(null);
  const [task, setTask] = useState("");
  const [mode, setMode] = useState<WorkflowMode>("parallel");
  const [selected, setSelected] = useState<string[]>([]);
  const [judge, setJudge] = useState<string>("");
  const [maxTokens, setMaxTokens] = useState<number | "">("");
  const [running, setRunning] = useState(false);
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [history, setHistory] = useState<WorkflowRun[]>([]);

  const loadHistory = useCallback(async () => {
    try {
      const res = await fetch("/api/runs?limit=15");
      const data = await res.json();
      if (data.ok) setHistory(data.runs as WorkflowRun[]);
    } catch {
      /* history is non-critical */
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/providers");
        const data = await res.json();
        if (!data.ok) return;
        const payload = data as ProvidersPayload;
        setMeta(payload);
        const ready = payload.providers.filter((p) => p.enabled).map((p) => p.id);
        setSelected(ready);
        setJudge(ready[0] ?? "");
      } catch {
        setErrors(["Could not reach the server. Is it running?"]);
      }
    })();
    void loadHistory();
  }, [loadHistory]);

  const providers = meta?.providers ?? [];
  const ready = useMemo(() => providers.filter((p) => p.enabled), [providers]);
  const activeMode = MODES.find((m) => m.value === mode)!;

  /** Local mirror of the server-side rules, so the UI explains itself before you click RUN. */
  const blocker = useMemo(() => {
    if (!task.trim()) return "Enter a task.";
    if (selected.length === 0) return "Select at least one provider.";
    if (mode === "single" && selected.length !== 1) return "Single mode takes exactly one provider.";
    if (mode === "review" && selected.length !== 2)
      return "Review mode needs exactly two providers (first drafts, second reviews).";
    if (mode === "consensus" && selected.length < 2)
      return "Consensus mode needs at least two providers.";
    if (mode === "consensus" && !judge) return "Choose a judge model.";
    if (meta && task.length > meta.limits.maxTaskLength)
      return `Task exceeds the ${meta.limits.maxTaskLength} character limit.`;
    return null;
  }, [task, selected, mode, judge, meta]);

  function toggleProvider(id: string) {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id],
    );
  }

  async function runWorkflow() {
    setRunning(true);
    setErrors([]);
    setRun(null);
    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          task,
          mode,
          providers: selected,
          ...(mode === "consensus" ? { judge } : {}),
          ...(maxTokens === "" ? {} : { maxOutputTokens: maxTokens }),
        }),
      });
      const data = await res.json();
      if (!data.ok) {
        setErrors([data.error, ...((data.issues as string[] | undefined) ?? [])]);
        return;
      }
      setRun(data.run as WorkflowRun);
      void loadHistory();
    } catch (err) {
      setErrors([err instanceof Error ? err.message : "Request failed"]);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="wrap">
      <header className="masthead">
        <h1>Pizarro Multi-AI Orchestrator</h1>
        <p>
          One task → many models → one answer. All provider calls run server-side; API keys
          never reach this page.
        </p>
      </header>

      {meta?.mockEnabled && (
        <div className="notice mock">
          <strong>Mock provider enabled.</strong> A development-only fake provider is
          available and its output is <em>not</em> from any AI model. Unset
          <code>ENABLE_MOCK_PROVIDER</code> to hide it.
        </div>
      )}

      <div className="grid">
        <main>
          <section className="card">
            <h2>Task</h2>
            <label className="field">
              <span>What should the AI systems work on?</span>
              <textarea
                value={task}
                onChange={(e) => setTask(e.target.value)}
                placeholder="Describe the task for the models…"
              />
            </label>
            <p className="muted">
              {task.length.toLocaleString()}
              {meta ? ` / ${meta.limits.maxTaskLength.toLocaleString()}` : ""} characters
            </p>
          </section>

          {errors.length > 0 && (
            <div className="notice error">
              <strong>{errors[0]}</strong>
              {errors.length > 1 && (
                <ul>
                  {errors.slice(1).map((e) => (
                    <li key={e}>{e}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {run && (
            <section>
              <h2 style={{ fontSize: 13, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--muted)" }}>
                Results — {run.mode} · {run.status} · {run.durationMs} ms
              </h2>

              {run.steps.map((step, i) => (
                <ResultPanel key={`${step.stage}-${step.provider}-${i}`} step={step} />
              ))}

              <div className="result final">
                <div className="head">
                  <span className="title">Final synthesis</span>
                  <span className="stats">
                    {run.judge ? `judge: ${run.judge} · ` : ""}run {run.runId.slice(0, 8)}
                  </span>
                </div>
                <div className="body">
                  {run.finalResponse ??
                    (run.mode === "parallel"
                      ? "Parallel mode returns each model's answer separately — there is no single synthesized answer. Use Consensus mode to have a judge model combine them."
                      : "No final answer was produced. See the failures above.")}
                </div>
              </div>
            </section>
          )}
        </main>

        <aside>
          <section className="card">
            <h2>Providers</h2>
            {providers.length === 0 && <p className="muted">Loading…</p>}
            {providers.map((p) => (
              <label key={p.id} className={`provider-row ${p.enabled ? "" : "disabled"}`}>
                <input
                  type="checkbox"
                  checked={selected.includes(p.id)}
                  disabled={!p.enabled}
                  onChange={() => toggleProvider(p.id)}
                />
                <span>
                  <span className="pname">
                    {p.name}
                    {p.mock && <span className="badge mock">mock</span>}
                    {!p.configured && <span className="badge err">not configured</span>}
                  </span>
                  <br />
                  <span className="meta">
                    {p.model} · {p.status}
                  </span>
                </span>
              </label>
            ))}
            {providers.some((p) => !p.configured) && (
              <p className="muted">
                Unconfigured providers stay disabled — nothing is faked in their place.
              </p>
            )}
          </section>

          <section className="card">
            <h2>Mode</h2>
            <label className="field">
              <select value={mode} onChange={(e) => setMode(e.target.value as WorkflowMode)}>
                {MODES.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
            <p className="muted">{activeMode.hint}</p>

            {mode === "consensus" && (
              <label className="field">
                <span>Judge model</span>
                <select value={judge} onChange={(e) => setJudge(e.target.value)}>
                  <option value="">Select a judge…</option>
                  {ready.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <label className="field">
              <span>Max output tokens {meta ? `(cap ${meta.limits.maxOutputTokens})` : ""}</span>
              <input
                type="number"
                min={1}
                max={meta?.limits.maxOutputTokens}
                value={maxTokens}
                placeholder={String(meta?.limits.maxOutputTokens ?? "")}
                onChange={(e) => setMaxTokens(e.target.value === "" ? "" : Number(e.target.value))}
              />
            </label>

            {blocker && <p className="muted">{blocker}</p>}

            <button className="run" onClick={runWorkflow} disabled={running || Boolean(blocker)}>
              {running ? "RUNNING…" : "RUN WORKFLOW"}
            </button>
          </section>

          <section className="card">
            <h2>History</h2>
            {history.length === 0 && <p className="muted">No runs yet.</p>}
            {history.map((h) => (
              <button key={h.runId} className="history-item" onClick={() => setRun(h)}>
                <span className="when">
                  {new Date(h.createdAt).toLocaleString()} · {h.mode} ·{" "}
                  <span className={`badge ${h.status === "success" ? "ok" : h.status === "partial" ? "warn" : "err"}`}>
                    {h.status}
                  </span>
                </span>
                <span className="task">
                  {h.task.length > 90 ? `${h.task.slice(0, 90)}…` : h.task}
                </span>
              </button>
            ))}
          </section>
        </aside>
      </div>
    </div>
  );
}
