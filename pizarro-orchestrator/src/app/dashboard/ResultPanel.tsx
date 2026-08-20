"use client";

import type { WorkflowStep } from "@/types/ai";
import { safeCitations } from "@/lib/citations";

const STAGE_LABEL: Record<string, string> = {
  answer: "answer",
  draft: "draft",
  critique: "critique",
  revision: "revised answer",
  synthesis: "synthesis",
};

/** One provider call: who ran, which model, how long it took, and what came back. */
export function ResultPanel({ step }: { step: WorkflowStep }) {
  const { result, stage } = step;
  const stageLabel = STAGE_LABEL[stage] ?? stage;
  const citations = safeCitations(result);

  return (
    <div className="result">
      <div className="head">
        <span className="title">
          {result.providerName}
          <span className={`badge ${result.ok ? "ok" : "err"}`}>
            {result.ok ? "success" : "failed"}
          </span>
          <span className="badge">{stageLabel}</span>
        </span>
        <span className="stats">
          {result.model} · {result.latencyMs} ms ·{" "}
          {new Date(result.timestamp).toLocaleTimeString()}
          {result.ok && result.usage?.outputTokens
            ? ` · ${result.usage.outputTokens} out tokens`
            : ""}
        </span>
      </div>

      {result.ok ? (
        <div className="body">{result.text}</div>
      ) : (
        <div className="body failed">
          {result.error.message}
          {"\n\n"}
          <span className="muted">
            code: {result.error.code} · attempts: {result.error.attempts} ·{" "}
            {result.error.retryable ? "transient" : "permanent"}
          </span>
        </div>
      )}

      {citations.length > 0 && (
        <div className="citations">
          Sources:
          {citations.slice(0, 8).map((url) => (
            <a key={url} href={url} target="_blank" rel="noreferrer noopener">
              {url}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
