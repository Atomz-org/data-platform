import React from "react";
import {
  Badge, Banner, Button, Card, Checkbox, Divider, HStack, Input, Modal, Select,
  Spinner, Switch, Text, VStack,
} from "wss3-forge";
import {
  api, type CapabilityOption, type CreatedProject, type Fleet, type ProjectPlan,
  type ProvisionOptions,
} from "../api";

/**
 * Create a project: one legal entity, with its own warehouse, pipelines and dbt
 * project.
 *
 * Three steps, because the three decisions have different costs. The name and
 * the group are cheap to change now and impossible later. The capability set is
 * the expensive one — `pf bootstrap` backfills what is missing but never removes
 * what should not have been added — so it is chosen explicitly and seeded from
 * the registry defaults rather than from an empty list. The plan is the last
 * thing before the write, and it is the server's plan, not a summary of the form.
 *
 * The step order is fixed and forward-only past the plan: re-resolving after the
 * files exist would show a blocker for the project that was just created.
 */
const STEPS = ["Identity", "Capabilities", "Review"] as const;

export default function NewProjectDialog({ open, onClose, onCreated, options, fleet, initialGroup }: {
  open: boolean;
  onClose: () => void;
  onCreated: (result: CreatedProject) => void;
  options: ProvisionOptions | null;
  fleet: Fleet | null;
  initialGroup?: string;
}) {
  const [step, setStep] = React.useState(0);
  const [group, setGroup] = React.useState(initialGroup ?? "");
  const [project, setProject] = React.useState("");
  const [rollup, setRollup] = React.useState(false);
  const [sisters, setSisters] = React.useState<string[]>([]);
  const [warehouse, setWarehouse] = React.useState("");
  const [extras, setExtras] = React.useState<string[]>([]);
  const [dropped, setDropped] = React.useState<string[]>([]);
  const [actor, setActor] = React.useState(() => localStorage.getItem("pf-actor") ?? "");
  const [reason, setReason] = React.useState("");

  const [plan, setPlan] = React.useState<ProjectPlan | null>(null);
  const [result, setResult] = React.useState<CreatedProject | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    if (!open) return;
    setStep(0); setPlan(null); setResult(null); setError("");
    setGroup(initialGroup ?? "");
  }, [open, initialGroup]);

  const caps = options?.capabilities ?? [];
  const warehouses = caps.filter(c => c.is_warehouse);
  const optional = caps.filter(c => !c.is_warehouse && !c.default);
  const defaults = caps.filter(c => c.default);

  // The default warehouse is already a default capability. Naming a different
  // one adds it rather than replacing it, which is what `--with` does, so the
  // one being replaced has to be dropped explicitly or the project gets two.
  const defaultWarehouse = defaults.find(c => c.is_warehouse)?.name ?? "";
  const withNames = [...extras, ...(warehouse && warehouse !== defaultWarehouse ? [warehouse] : [])];
  const withoutNames = [
    ...dropped,
    ...(warehouse && warehouse !== defaultWarehouse && defaultWarehouse ? [defaultWarehouse] : []),
  ];

  const sisterOptions = (fleet?.groups.find(g => g.name === group)?.projects ?? [])
    .filter(p => !p.is_rollup)
    .map(p => p.name);

  const identityDone = Boolean(group && project);

  // Resolved only when the review step is reached. A plan recomputed on every
  // keystroke of a nine-field form is a lot of scaffolder work for an answer
  // nobody is reading yet.
  React.useEffect(() => {
    if (!open || step !== 2 || result) return;
    setBusy(true);
    api.send<ProjectPlan>("/api/provision/project/plan", {
      group, project, rollup, sisters,
      with: withNames, without: withoutNames,
    })
      .then(setPlan)
      .catch(e => setError(e.message))
      .finally(() => setBusy(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, step, result]);

  async function submit() {
    setBusy(true);
    setError("");
    try {
      localStorage.setItem("pf-actor", actor.trim());
      const created = await api.send<CreatedProject>("/api/provision/project", {
        group, project, rollup, sisters,
        with: withNames, without: withoutNames,
        actor: actor.trim(), reason,
      });
      setResult(created);
      onCreated(created);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function toggle(list: string[], set: (v: string[]) => void, name: string, on: boolean) {
    set(on ? [...list, name] : list.filter(n => n !== name));
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={result ? `${result.group}/${result.project}` : "New project"}
      subtitle={result
        ? "Created. Every bootstrap step is listed below."
        : "One legal entity: its own warehouse, its own pipelines, its own dbt project."}
      size="lg"
      closable={!busy}
    >
      <Modal.Content>
        {!result && (
          <VStack gap="md">
            <HStack gap="xs" align="center">
              {STEPS.map((label, i) => (
                <React.Fragment key={label}>
                  {i > 0 && <Text color="secondary">›</Text>}
                  <Badge variant={i === step ? "primary" : i < step ? "success" : "default"}>
                    {i + 1}. {label}
                  </Badge>
                </React.Fragment>
              ))}
            </HStack>
            <Divider />

            {step === 0 && (
              <VStack gap="md">
                <HStack gap="md" align="start">
                  <Select
                    label="Group"
                    value={group}
                    onChange={g => { setGroup(g); setSisters([]); }}
                    options={(options?.groups ?? []).map(g => ({ value: g, label: g }))}
                    placeholder="Select a group"
                    hint="A project must live in a group. Create one first if it is not listed."
                    searchable
                    style={{ flex: 1 }}
                  />
                  <Input
                    label="Project name"
                    value={project}
                    onChange={setProject}
                    placeholder={group ? `${group}-us` : "acme-us"}
                    hint="One legal entity. Conventionally the group name and a region."
                    style={{ flex: 1 }}
                  />
                </HStack>

                <Switch
                  checked={rollup}
                  onChange={v => { setRollup(v); if (!v) setSisters([]); }}
                  label="Cross-entity roll-up"
                  hint="Reads its sisters rather than a source of its own. A roll-up over no sisters unions nothing."
                />

                {rollup && (
                  <Card variant="raised" title="Sisters to union"
                        subtitle="Every non-roll-up project in this group">
                    {sisterOptions.length === 0
                      ? <Text color="secondary" size="sm">
                          This group has no sister projects yet, so the roll-up will union
                          nothing until one is created.
                        </Text>
                      : <VStack gap="xs">
                          {sisterOptions.map(s => (
                            <Checkbox
                              key={s}
                              checked={sisters.includes(s)}
                              onChange={on => toggle(sisters, setSisters, s, on)}
                              label={s}
                            />
                          ))}
                        </VStack>}
                  </Card>
                )}
              </VStack>
            )}

            {step === 1 && (
              <VStack gap="md">
                <Select
                  label="Production warehouse"
                  value={warehouse || defaultWarehouse}
                  onChange={setWarehouse}
                  options={warehouses.map(w => ({ value: w.name, label: w.name }))}
                  hint="What the dbt prod target ships onto. Credentials are reported, not required, at this point."
                  searchable
                />

                <Card variant="raised" title="Included by default"
                      subtitle="Every project gets these. Unticking one is deliberate and is recorded in the plan.">
                  <VStack gap="xs">
                    {defaults.filter(c => !c.is_warehouse).map(c => (
                      <Checkbox
                        key={c.name}
                        checked={!dropped.includes(c.name)}
                        onChange={on => toggle(dropped, setDropped, c.name, !on)}
                        label={c.name}
                        hint={c.description}
                      />
                    ))}
                  </VStack>
                </Card>

                {optional.length > 0 && (
                  <Card variant="raised" title="Optional"
                        subtitle="Added on top. A capability is far cheaper to add now than to remove later.">
                    <VStack gap="xs">
                      {optional.map((c: CapabilityOption) => (
                        <Checkbox
                          key={c.name}
                          checked={extras.includes(c.name)}
                          onChange={on => toggle(extras, setExtras, c.name, on)}
                          label={c.name}
                          hint={c.description}
                        />
                      ))}
                    </VStack>
                  </Card>
                )}
              </VStack>
            )}

            {step === 2 && (
              <VStack gap="md">
                {busy && !plan && <Spinner />}

                {plan && (
                  <>
                    <Card variant="raised" title="What this will write">
                      <VStack gap="sm">
                        <HStack justify="between">
                          <Text size="sm" color="secondary">Path</Text>
                          <Text size="sm" className="pf-mono">{plan.path}</Text>
                        </HStack>
                        <HStack justify="between">
                          <Text size="sm" color="secondary">Capabilities</Text>
                          <Text size="sm">{plan.capabilities.length}</Text>
                        </HStack>
                        <HStack justify="between">
                          <Text size="sm" color="secondary">Gate rules added</Text>
                          <Text size="sm">{plan.gate_rules_added}</Text>
                        </HStack>
                        <HStack gap="xs" wrap>
                          {plan.capabilities.map(c => (
                            <Badge key={c.name}>{c.name}</Badge>
                          ))}
                        </HStack>
                      </VStack>
                    </Card>

                    <HStack gap="md" align="start">
                      <Input
                        label="Your name or email"
                        value={actor}
                        onChange={setActor}
                        placeholder="you@example.com"
                        hint="Recorded against this action. Required."
                        style={{ flex: 1 }}
                      />
                      <Input
                        label="Reason"
                        value={reason}
                        onChange={setReason}
                        placeholder="EU entity go-live"
                        hint="Optional, goes into the provenance record."
                        style={{ flex: 1 }}
                      />
                    </HStack>

                    {plan.blockers.map(b => (
                      <Banner key={b} variant="error" title="Cannot create">{b}</Banner>
                    ))}
                    {plan.warnings.map(w => (
                      <Banner key={w} variant="warning">{w}</Banner>
                    ))}
                    {/* Missing credentials do not block. The scaffold is inert
                        without them and `pf doctor` reports them later; the
                        cheapest moment to pick a different warehouse is before
                        the files exist, which is why they are shown here. */}
                    {Object.keys(plan.missing_env).length > 0 && (
                      <Banner variant="info" title="Credentials not set yet">
                        {Object.entries(plan.missing_env)
                          .map(([cap, names]) => `${cap}: ${names.join(", ")}`)
                          .join(" · ")}
                      </Banner>
                    )}
                  </>
                )}

                {error && <Banner variant="error" title="Failed">{error}</Banner>}
              </VStack>
            )}
          </VStack>
        )}

        {result && (
          <VStack gap="md">
            <Banner variant={result.ok ? "success" : "warning"}
                    title={result.ok ? "Created" : "Created, with failed steps"}>
              {result.file_count} files, {result.capabilities.length} capabilities,
              {" "}{result.gate_rules_added} gate rule(s).
              {!result.ok && " The project exists but its bootstrap did not finish — the failed steps are listed below."}
            </Banner>

            {/* Every step, not a single tick. A project whose ladder half-ran
                exists on disk and is not finished, and a green tick over a
                failed graph build is the report that costs someone an afternoon. */}
            <Card variant="raised" title="Bootstrap" subtitle="The same ladder `pf bootstrap` runs">
              <VStack gap="none" style={{ maxHeight: 280, overflowY: "auto" }}>
                {result.steps.map(s => (
                  <HStack key={s.name} gap="sm" align="center"
                          style={{ padding: "4px 0" }}>
                    <span className={`pf-dot pf-${s.status === "failed" ? "changed"
                      : s.status === "skipped" ? "unknown" : "clean"}`} aria-hidden="true" />
                    <Text size="sm" style={{ minWidth: 150 }}>{s.name}</Text>
                    <Text size="xs" color="secondary">{s.status}</Text>
                    <Text size="xs" color="secondary" style={{ flex: 1 }}>{s.detail}</Text>
                  </HStack>
                ))}
              </VStack>
            </Card>

            <Text size="sm" color="secondary">
              Next: <span className="pf-mono">pf seed {result.group} {result.project}</span> to
              load data and refresh the graph, then <span className="pf-mono">pf check</span> before
              the first commit.
            </Text>
          </VStack>
        )}
      </Modal.Content>

      <Modal.Footer>
        <HStack justify="between" align="center" style={{ width: "100%" }}>
          <Text size="xs" color="secondary" className="pf-mono">
            {group && project ? `groups/${group}/projects/${project}` : ""}
          </Text>
          <HStack gap="sm">
            {result ? (
              <Button onClick={onClose}>Done</Button>
            ) : (
              <>
                <Button variant="ghost" onClick={onClose} disabled={busy}>Cancel</Button>
                {step > 0 && (
                  <Button variant="secondary" onClick={() => setStep(step - 1)} disabled={busy}>
                    Back
                  </Button>
                )}
                {step < 2 && (
                  <Button onClick={() => setStep(step + 1)}
                          disabled={step === 0 && !identityDone}>
                    Next
                  </Button>
                )}
                {step === 2 && (
                  <Button onClick={submit}
                          disabled={!plan?.ok || !actor.trim() || busy}>
                    {busy ? <Spinner size="sm" /> : "Create project"}
                  </Button>
                )}
              </>
            )}
          </HStack>
        </HStack>
      </Modal.Footer>
    </Modal>
  );
}
