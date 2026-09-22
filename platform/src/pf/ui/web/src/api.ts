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

/**
 * POST with a JSON body, for the provisioning routes.
 *
 * The older write routes take query parameters and are right to: they edit one
 * scalar at a time. A project is created with a list of capabilities and a list
 * of sisters, and encoding lists into a query string is the detail that
 * eventually disagrees between the two ends.
 */
async function send<T>(path: string, body: Json): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const parsed = await res.json();
      if (parsed?.detail) detail = typeof parsed.detail === "string"
        ? parsed.detail
        : JSON.stringify(parsed.detail);
    } catch { /* body was not JSON; the status line is all we have */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T,>(path: string, params?: Json) => request<T>(path, params, "GET"),
  post: <T,>(path: string, params?: Json) => request<T>(path, params, "POST"),
  send: <T,>(path: string, body: Json) => send<T>(path, body),
};

// ------------------------------------------------------------------ fleet --
export interface FleetProject {
  group: string; name: string; path: string;
  is_rollup: boolean; has_graph: boolean;
  counts: Record<string, number>;
  /** `null`, not `0`, when nothing has graphed this project. A green nought
   *  over an unmeasured project is a clean bill of health nobody issued. */
  models: number | null; sources: number | null;
  metrics: number | null; tests: number | null;
  warehouse: string; has_dbt: boolean; has_pipelines: boolean;
}

export interface FleetGroup {
  name: string; classes: string[]; projects: FleetProject[]; project_count: number;
  error: string; template_version_current: number;
  display_name?: string; domain?: string; lifecycle?: string; tier?: string;
  owner_team?: string; owner_contact?: string; residency?: string;
  template_version?: number; behind_template?: boolean;
  runs_loops?: boolean; strict?: boolean;
}

export interface Fleet {
  root: string; groups: FleetGroup[]; unmanaged: string[];
  counts: { groups: number; projects: number; active: number; behind_template: number };
}

// ------------------------------------------------------------ provisioning --
export interface CapabilityOption {
  name: string; description: string; default: boolean;
  is_warehouse: boolean; files: number; env: string[]; requires: string[];
}

export interface ProvisionOptions {
  domains: { name: string; classes: string[] }[];
  capabilities: CapabilityOption[];
  defaults: string[];
  warehouses: string[];
  lifecycles: string[];
  tiers: string[];
  groups: string[];
  name_rule: string;
  name_max: number;
}

export interface GroupPlan {
  group: string; domain: string; classes: string[]; path: string;
  blockers: string[]; warnings: string[]; ok: boolean;
}

export interface ProjectPlan {
  group: string; project: string; path: string; is_rollup: boolean;
  capabilities: { name: string; files: number; ci: string[] }[];
  gate_rules_added: number;
  missing_env: Record<string, string[]>;
  blockers: string[]; warnings: string[]; ok: boolean;
}

export interface BootstrapStep {
  name: string; status: "ok" | "created" | "skipped" | "failed"; detail: string;
}

export interface CreatedProject {
  group: string; project: string; path: string;
  files: string[]; file_count: number;
  capabilities: string[]; capability_files: Record<string, number>;
  gate_rules: string[]; gate_rules_added: number;
  steps: BootstrapStep[];
  missing_env: Record<string, string[]>;
  ok: boolean; actor: string;
}

export interface CreatedGroup {
  group: string; domain: string; classes: string[];
  files: string[]; file_count: number; actor: string; next: string;
}

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
