import Link from "next/link";

import { StatusBadge } from "@/components/StatusBadge";
import type { AdminSession } from "@/lib/api";
import { computePipelineStatus, formatTimestamp, ownerLabel, pipelineSummary, shortId } from "@/lib/format";

export function SessionList({ sessions }: { sessions: AdminSession[] }) {
  return (
    <div className="session-list card">
      <table className="session-table">
        <thead>
          <tr>
            <th>Session</th>
            <th>Owner</th>
            <th>Status</th>
            <th>Pipeline</th>
            <th>Health</th>
            <th>Last activity</th>
            <th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {sessions.map((session) => {
            const health = computePipelineStatus(session);
            return (
              <tr key={session.id}>
                <td>
                  <Link className="session-link" href={`/sessions/${encodeURIComponent(session.id)}`}>
                    {shortId(session.id)}
                  </Link>
                  <span className="muted session-id-inline" title={session.id}>
                    {session.id}
                  </span>
                </td>
                <td>{ownerLabel(session.user_id)}</td>
                <td>
                  <StatusBadge kind={session.status} label={session.status} />
                </td>
                <td className="pipeline-cell">{pipelineSummary(session)}</td>
                <td>
                  <StatusBadge kind={health.kind} label={health.label} />
                  {health.hint ? (
                    <span className="muted health-hint" title={health.hint}>
                      ⓘ
                    </span>
                  ) : null}
                </td>
                <td className="muted">{formatTimestamp(session.last_activity_at)}</td>
                <td>
                  <Link className="table-action" href={`/sessions/${encodeURIComponent(session.id)}`}>
                    Open
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
