import { Text } from "wss3-forge";

/**
 * One verdict, rendered the same way everywhere it appears.
 *
 * Colour never carries the meaning on its own — the word travels with the dot.
 * A reviewer deciding whether to ship reads this in a screenshot, in greyscale,
 * or with a colour vision deficiency, and "the red one" has to survive all three.
 */
export type VerdictKind = "changed" | "clean" | "warning" | "unknown";

const LABELS: Record<VerdictKind, string> = {
  changed: "changed",
  clean: "clean",
  warning: "uncovered",
  unknown: "unreviewed",
};

export function Verdict({ verdict, label }: { verdict: VerdictKind; label?: string }) {
  return (
    <span className="pf-verdict">
      <span className={`pf-dot pf-${verdict}`} aria-hidden="true" />
      <Text size="sm">{label ?? LABELS[verdict]}</Text>
    </span>
  );
}
