import React from "react";
import {
  Badge, Banner, Button, HStack, Input, Modal, Select, Spinner, Text, VStack,
} from "wss3-forge";
import {
  api, type CreatedGroup, type GroupPlan, type ProvisionOptions,
} from "../api";

/**
 * Create a group: a family of sister companies, with its own ontology instance.
 *
 * Two things make this more than a name field.
 *
 * The **archetype** decides which ontology classes the family starts with, and
 * that decision is expensive to revisit once projects are modelled against it.
 * So the classes are shown as they are chosen, not described — an operator
 * picking `fintech` can see they are getting Contract and Currency before the
 * directory exists.
 *
 * The **owner** is optional and is nagged about anyway. `group.yaml` is
 * templated with an empty owner because a template cannot know one, and every
 * group in this repository still has it empty — which is how `pf offboard` came
 * to have nobody to notify. The one moment it is cheap to record is now.
 */
export default function NewGroupDialog({ open, onClose, onCreated, options }: {
  open: boolean;
  onClose: () => void;
  onCreated: (result: CreatedGroup) => void;
  options: ProvisionOptions | null;
}) {
  const [group, setGroup] = React.useState("");
  const [domain, setDomain] = React.useState("b2b_saas");
  const [displayName, setDisplayName] = React.useState("");
  const [ownerTeam, setOwnerTeam] = React.useState("");
  const [ownerContact, setOwnerContact] = React.useState("");
  const [tier, setTier] = React.useState("standard");
  const [actor, setActor] = React.useState(() => localStorage.getItem("pf-actor") ?? "");
  const [reason, setReason] = React.useState("");

  const [plan, setPlan] = React.useState<GroupPlan | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    if (!open) return;
    setPlan(null);
    setError("");
  }, [open]);

  // The plan is re-resolved as the form is typed, debounced. The server owns
  // every rule — name shape, collision, archetype — so the button cannot come
  // to disagree with what the scaffolder would actually do.
  React.useEffect(() => {
    if (!open) return;
    if (!group) { setPlan(null); return; }
    const id = setTimeout(() => {
      api.send<GroupPlan>("/api/provision/group/plan",
                          { group, domain, owner_team: ownerTeam, owner_contact: ownerContact })
        .then(setPlan)
        .catch(e => setError(e.message));
    }, 250);
    return () => clearTimeout(id);
  }, [open, group, domain, ownerTeam, ownerContact]);

  const classes = plan?.classes
    ?? options?.domains.find(d => d.name === domain)?.classes
    ?? [];
  const ready = Boolean(plan?.ok && actor.trim() && !busy);

  async function submit() {
    setBusy(true);
    setError("");
    try {
      localStorage.setItem("pf-actor", actor.trim());
      const created = await api.send<CreatedGroup>("/api/provision/group", {
        group, domain, display_name: displayName, owner_team: ownerTeam,
        owner_contact: ownerContact, tier, actor: actor.trim(), reason,
      });
      onCreated(created);
      setGroup(""); setDisplayName(""); setOwnerTeam("");
      setOwnerContact(""); setReason("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New group"
      subtitle="A family of sister companies: one shared ontology instance, conformed dimensions, group metrics."
      size="lg"
    >
      <Modal.Content>
        <VStack gap="md">
          <HStack gap="md" align="start">
            <Input
              label="Group name"
              value={group}
              onChange={setGroup}
              placeholder="northwind"
              hint="Lowercase, hyphens. Becomes a directory, a Python module and a dbt profile key."
              style={{ flex: 1 }}
              autoFocus
            />
            <Input
              label="Display name"
              value={displayName}
              onChange={setDisplayName}
              placeholder="Northwind Traders"
              hint="Optional — how a human writes it."
              style={{ flex: 1 }}
            />
          </HStack>

          <HStack gap="md" align="start">
            <Select
              label="Archetype"
              value={domain}
              onChange={setDomain}
              options={(options?.domains ?? []).map(d => ({ value: d.name, label: d.name }))}
              hint="Decides the ontology classes this family starts with."
              style={{ flex: 1 }}
            />
            <Select
              label="Tier"
              value={tier}
              onChange={setTier}
              options={(options?.tiers ?? ["standard"]).map(t => ({ value: t, label: t }))}
              hint="critical raises the loop budget and the gate severity."
              style={{ flex: 1 }}
            />
          </HStack>

          {classes.length > 0 && (
            <VStack gap="xs">
              <Text size="sm" color="secondary">
                Ontology classes seeded by <span className="pf-mono">{domain}</span>
              </Text>
              <HStack gap="xs" wrap>
                {classes.map(c => <Badge key={c} variant="info">{c}</Badge>)}
              </HStack>
            </VStack>
          )}

          <HStack gap="md" align="start">
            <Input
              label="Owner team"
              value={ownerTeam}
              onChange={setOwnerTeam}
              placeholder="data-engineering"
              style={{ flex: 1 }}
            />
            <Input
              label="Owner contact"
              value={ownerContact}
              onChange={setOwnerContact}
              placeholder="data-eng@northwind.example"
              style={{ flex: 1 }}
            />
          </HStack>

          <HStack gap="md" align="start">
            <Input
              label="Your name or email"
              value={actor}
              onChange={setActor}
              placeholder="you@example.com"
              hint="Recorded against this action. Required."
              error={!actor.trim() && plan?.ok ? "Required" : undefined}
              style={{ flex: 1 }}
            />
            <Input
              label="Reason"
              value={reason}
              onChange={setReason}
              placeholder="new tenant — signed 2026-09"
              hint="Optional, goes into the provenance record."
              style={{ flex: 1 }}
            />
          </HStack>

          {/* Blockers and warnings are kept apart on purpose: one stops the
              scaffold, the other is a thing to look at before proceeding, and
              collapsing them into one list makes the second read as the first. */}
          {plan?.blockers.map(b => (
            <Banner key={b} variant="error" title="Cannot create">{b}</Banner>
          ))}
          {plan?.warnings.map(w => (
            <Banner key={w} variant="warning">{w}</Banner>
          ))}
          {error && <Banner variant="error" title="Failed">{error}</Banner>}
        </VStack>
      </Modal.Content>

      <Modal.Footer>
        <HStack justify="between" align="center" style={{ width: "100%" }}>
          <Text size="xs" color="secondary" className="pf-mono">
            {plan?.path ?? (group ? `groups/${group}` : "")}
          </Text>
          <HStack gap="sm">
            <Button variant="ghost" onClick={onClose} disabled={busy}>Cancel</Button>
            <Button onClick={submit} disabled={!ready}>
              {busy ? <Spinner size="sm" /> : "Create group"}
            </Button>
          </HStack>
        </HStack>
      </Modal.Footer>
    </Modal>
  );
}
