/** Typed access to the FastAPI control plane. One place that knows about HTTP. */

export type Json = Record<string, any>;

async function request<T>(path: string, params: Json = {}, method = "GET"): Promise<T> {
  const url = new URL(path, window.location.origin);
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
  }
  const res = await fetch(url.toString(), { method });
  if (!res.ok) {
    // FastAPI puts the reason in `detail`. Surfacing the status alone turns
    // "actor is required" into "422", which tells the operator nothing.
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string"
        ? body.detail
        : JSON.stringify(body.detail);
    } catch { /* body was not JSON; the status line is all we have */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T,>(path: string, params?: Json) => request<T>(path, params, "GET"),
  post: <T,>(path: string, params?: Json) => request<T>(path, params, "POST"),
};

export interface Project { name: string; is_rollup: boolean; has_graph: boolean; counts: Json }
export interface Group { name: string; classes: string[]; projects: Project[] }
export interface Tree { root: string; groups: Group[] }

export interface SemanticRow {
  name: string; table: string; schema: string; columns: number;
  roles: string[]; primary_key: string;
  status: "moved" | "held" | "uncovered" | "unreviewed";
  checks: number; check_types: string[];
  row_count: { base: number; curr: number; delta: number } | null;
  rows_added: number; rows_removed: number; categories_drifted: string[];
}

export interface SemanticDiff {
  group: string; project: string;
  wren_enabled: boolean; recce_enabled: boolean;
  reviewed: boolean; has_baseline: boolean;
  catalog: string; schema: string;
  models: SemanticRow[];
  unpublished: Json[];
  counts: Record<string, number>;
}

export interface RecceCheck {
  name: string; description: string; type: string; model: string;
  verdict: "changed" | "clean" | "not_run" | "errored";
  detail: string; run_at: string; is_preset: boolean;
}

export interface GovEdit {
  id: string; ts: string; actor: string; surface: string; scope: string;
  key_path: string; before: string; after: string; reason: string;
  applied: boolean; error: string;
}

export interface GovSurface {
  name: string; title: string; rel: string; scoped: boolean; description: string;
}
