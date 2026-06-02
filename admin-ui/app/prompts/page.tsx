import { revalidatePath } from "next/cache";

import { adminFetch, type PromptVersion } from "@/lib/api";

async function createPromptVersion(formData: FormData) {
  "use server";

  const id = String(formData.get("id") ?? "");
  const content = String(formData.get("content") ?? "");
  if (!id || !content.trim()) {
    return;
  }

  await adminFetch<PromptVersion>(`/admin/api/prompts/${id}`, {
    method: "POST",
    body: JSON.stringify({ content })
  });
  revalidatePath("/prompts");
}

export default async function PromptsPage() {
  const data = await adminFetch<{ prompts: PromptVersion[] }>("/admin/api/prompts");

  return (
    <section>
      <h1>Prompts</h1>
      <p className="muted">
        DB-backed prompt versions for admin review. Runtime prompt compiler integration is intentionally separate.
      </p>
      <div className="grid">
        {data.prompts.map((prompt) => (
          <article className="card" key={prompt.id}>
            <span className="pill">
              {prompt.prompt_type} v{prompt.version}
              {prompt.active_flag ? " active" : ""}
            </span>
            <p className="muted">{new Date(prompt.created_at).toLocaleString()}</p>
            <pre>{prompt.content}</pre>
            <form action={createPromptVersion}>
              <input name="id" type="hidden" value={prompt.id} />
              <label>
                New version content
                <textarea name="content" defaultValue={prompt.content} />
              </label>
              <button type="submit">Create active version</button>
            </form>
          </article>
        ))}
      </div>
      {data.prompts.length === 0 ? (
        <div className="card">
          <p className="muted">No DB-backed prompt versions yet. Seed one through the admin API first.</p>
        </div>
      ) : null}
    </section>
  );
}
