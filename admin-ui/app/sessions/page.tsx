import { SessionList } from "@/components/SessionList";
import { adminFetch, type AdminSession } from "@/lib/api";

export default async function SessionsPage() {
  const data = await adminFetch<{ sessions: AdminSession[] }>("/admin/api/sessions");

  return (
    <section>
      <h1>Sessions</h1>
      <p className="muted">
        Session-centric observability for user inputs, policy decisions, dream capture, jobs, and reflections.
      </p>
      {data.sessions.length > 0 ? (
        <SessionList sessions={data.sessions} />
      ) : (
        <div className="card">
          <p className="muted">No sessions recorded yet.</p>
        </div>
      )}
    </section>
  );
}
