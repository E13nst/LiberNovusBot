import Link from "next/link";

import type { PolicyTrace } from "@/lib/api";
import {
  extractInputText,
  extractOutcomeFlags,
  formatTimestamp,
  routeLabel,
  shortId
} from "@/lib/format";

import { RawPayload } from "./RawPayload";
import { StatusBadge } from "./StatusBadge";

export function PolicyTraceCard({ trace }: { trace: PolicyTrace }) {
  const inputText = extractInputText(trace);
  const outcome = extractOutcomeFlags(trace.outcome);

  return (
    <article className="policy-card">
      <div className="policy-card-header">
        <StatusBadge kind={trace.route} label={routeLabel(trace.route)} />
        <span className="muted">{formatTimestamp(trace.created_at)}</span>
      </div>

      <div className="policy-section">
        <h3>Input</h3>
        {inputText ? (
          <p className="policy-input">{inputText}</p>
        ) : (
          <p className="muted">No input text stored in this trace.</p>
        )}
      </div>

      <div className="policy-section">
        <h3>Policy</h3>
        <dl className="meta-list">
          <div>
            <dt>Route</dt>
            <dd>{trace.route}</dd>
          </div>
          <div>
            <dt>Rule</dt>
            <dd>{trace.reason_code}</dd>
          </div>
          <div>
            <dt>Confidence</dt>
            <dd>1.0</dd>
          </div>
        </dl>
      </div>

      <div className="policy-section">
        <h3>Execution</h3>
        <ul className="execution-list">
          <li>Dream created: {formatFlag(outcome.dreamCreated)}</li>
          <li>Job enqueued: {formatFlag(outcome.jobEnqueued)}</li>
          <li>Reflection generated: {formatFlag(outcome.reflectionGenerated)}</li>
        </ul>
        <div className="policy-links">
          {trace.dream_id ? (
            <Link href={`/dream/${trace.dream_id}`}>Open dream #{trace.dream_id}</Link>
          ) : null}
          {trace.job_id ? <span className="muted">Job {shortId(trace.job_id)}</span> : null}
        </div>
      </div>

      <RawPayload
        title="Raw policy payload"
        value={{ input: trace.input, decision: trace.decision, outcome: trace.outcome }}
      />
    </article>
  );
}

function formatFlag(value: boolean | null): string {
  if (value === null) {
    return "unknown";
  }
  return value ? "yes" : "no";
}
