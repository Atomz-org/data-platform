"""The DORA workflow's independence, run rather than read.

`dora.yml` promises that its scans do not depend on one another and that only
the last step colours the run. Those promises live in two shell scripts inside
the YAML — the `switches` step that decides which scans are on, and the
`Outcome` step that decides red or green — so these tests pull exactly those
scripts out of the committed file and run them under bash with each scan's
outcome substituted for GitHub's `${{ steps.<id>.outcome }}` expressions.

What is pinned:

  a scan is on when its credential is present      and off otherwise
  a manual `scans=` input restricts the run         without touching the rest
  nothing configured is a warning, exit 0           never a failure
  a configured scan that failed is exit 1           and names itself
  another scan's failure does not turn one off      independence, the point
  a breached article is exit 1 even when every scan ran
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "dora.yml"
SCANS = ("aws", "gcp", "kubernetes", "cloudflare", "github")


def _steps() -> dict[str, dict]:
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job = doc["jobs"]["infrastructure"]
    return {(s.get("id") or s.get("name")): s for s in job["steps"]}


def _render(script: str, outcomes: dict[str, str], switches: dict[str, str]) -> str:
    """Substitute the GitHub expressions the way the runner would."""

    def sub(m: re.Match) -> str:
        expr = m.group(1).strip()
        if expr.startswith("steps.switches.outputs."):
            return switches.get(expr.rsplit(".", 1)[-1], "false")
        if expr.startswith("steps.") and expr.endswith(".outcome"):
            return outcomes.get(expr.split(".")[1], "skipped")
        if expr == "steps.audit.outputs.exit":
            return outcomes.get("audit_exit", "0")
        raise AssertionError(f"unexpected expression in the script: {expr}")

    return re.sub(r"\$\{\{\s*([^}]+?)\s*\}\}", sub, script)


def _bash(script: str, env: dict[str, str], tmp: Path) -> subprocess.CompletedProcess:
    out = tmp / "github_output"
    out.write_text("")
    full_env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp), "GITHUB_OUTPUT": str(out),
                "GITHUB_STEP_SUMMARY": str(tmp / "summary.md"), **env}
    return subprocess.run(["bash", "-e", "-c", script], env=full_env, cwd=str(tmp),
                          capture_output=True, text=True, check=False)


def _switch_outputs(tmp: Path) -> dict[str, str]:
    text = (tmp / "github_output").read_text()
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


# ---------------------------------------------------------------- switches --

def test_a_scan_is_on_exactly_when_its_credential_is_present(tmp_path: Path) -> None:
    script = _steps()["switches"]["run"]
    r = _bash(script, {"SCANS": "", "AWS_ROLE_ARN": "arn:aws:iam::1:role/x", "GITHUB_PERSONAL_ACCESS_TOKEN": "t"}, tmp_path)
    assert r.returncode == 0, r.stderr
    on = _switch_outputs(tmp_path)
    assert {k: on[k] for k in SCANS} == {"aws": "true", "gcp": "false", "kubernetes": "false",
                                          "cloudflare": "false", "github": "true"}


def test_gcp_is_on_with_either_credential_shape(tmp_path: Path) -> None:
    script = _steps()["switches"]["run"]
    _bash(script, {"SCANS": "", "GCP_WIF_PROVIDER": "projects/1/locations/global/workloadIdentityPools/p/providers/g"},
          tmp_path)
    assert _switch_outputs(tmp_path)["gcp"] == "true"
    _bash(script, {"SCANS": "", "GCP_CREDENTIALS_JSON": "{}"}, tmp_path)
    assert _switch_outputs(tmp_path)["gcp"] == "true"
    _bash(script, {"SCANS": ""}, tmp_path)
    assert _switch_outputs(tmp_path)["gcp"] == "false"


def test_manual_scans_input_restricts_without_enabling(tmp_path: Path) -> None:
    script = _steps()["switches"]["run"]
    env = {"SCANS": "cloudflare, github", "AWS_ROLE_ARN": "arn", "CLOUDFLARE_API_TOKEN": "t",
           "GITHUB_PERSONAL_ACCESS_TOKEN": "t"}
    _bash(script, env, tmp_path)
    on = _switch_outputs(tmp_path)
    assert on["aws"] == "false", "asked for cloudflare,github only"
    assert on["cloudflare"] == "true" and on["github"] == "true"
    _bash(script, {"SCANS": "gcp"}, tmp_path)
    assert _switch_outputs(tmp_path)["gcp"] == "false", "asking for a scan with no credential does not enable it"


# ----------------------------------------------------------------- outcome --

def _outcome(tmp_path: Path, switches: dict[str, str], outcomes: dict[str, str]) -> subprocess.CompletedProcess:
    script = _render(_steps()["Outcome"]["run"], outcomes, switches)
    return _bash(script, {}, tmp_path)


def test_nothing_configured_is_a_warning_not_a_failure(tmp_path: Path) -> None:
    r = _outcome(tmp_path, dict.fromkeys(SCANS, "false"), {"audit_exit": "0"})
    assert r.returncode == 0
    assert "::warning title=DORA infrastructure scan not configured" in r.stdout
    assert "::error" not in r.stdout


def test_a_configured_scan_that_did_not_run_is_red_and_named(tmp_path: Path) -> None:
    switches = {**dict.fromkeys(SCANS, "false"), "gcp": "true", "github": "true"}
    r = _outcome(tmp_path, switches, {"gcp_scan": "skipped", "github_scan": "success", "audit_exit": "0"})
    assert r.returncode == 1
    assert "::error title=Configured scan did not run:: gcp" in r.stdout
    assert "github" not in r.stdout.split("::error")[1], "the scan that ran is not blamed"


def test_scans_are_independent_of_each_other(tmp_path: Path) -> None:
    """Every scan configured, one of them broken: the others still count as
    ran, and only the broken one is named. Then the same with none broken."""
    switches = dict.fromkeys(SCANS, "true")
    ran = {"aws_scan": "success", "gcp_scan": "success", "kubernetes_scan": "success",
           "cloudflare_scan": "success", "r2_scan": "success", "github_scan": "success", "audit_exit": "0"}
    assert _outcome(tmp_path, switches, ran).returncode == 0
    for broken in ("aws_scan", "gcp_scan", "kubernetes_scan", "cloudflare_scan", "r2_scan", "github_scan"):
        r = _outcome(tmp_path, switches, {**ran, broken: "failure"})
        assert r.returncode == 1, broken
        named = r.stdout.split("Configured scan did not run::")[1].split()
        assert len(named) == 1, f"{broken} failing must name exactly one scan, got {named}"


def test_a_breached_article_is_red_even_when_every_scan_ran(tmp_path: Path) -> None:
    switches = {**dict.fromkeys(SCANS, "false"), "github": "true"}
    r = _outcome(tmp_path, switches, {"github_scan": "success", "audit_exit": "1"})
    assert r.returncode == 1 and "::error" not in r.stdout, "the audit's own log said which article"


# ------------------------------------------------------------- structure --

def test_no_credential_or_scan_step_can_abort_the_job() -> None:
    steps = _steps()
    for sid in ("aws_auth", "aws_scan", "gcp_wif", "gcp_key", "gcp_scan", "kubernetes_scan",
                "cloudflare_scan", "r2_scan", "github_scan"):
        assert steps[sid].get("continue-on-error") is True, f"{sid} could abort the job"
    for name in ("audit", "Step summary", "Archive evidence", "Outcome"):
        assert str(steps[name].get("if", "")).startswith("always()"), f"{name} must run whatever happened"
    assert list(steps)[-1] == "Outcome", "the colour of the run is decided last"


def test_each_scan_depends_only_on_its_own_switch_and_credential_step() -> None:
    steps = _steps()
    own = {"aws_scan": ({"aws_auth"}, "aws"), "gcp_scan": ({"gcp_wif", "gcp_key"}, "gcp"),
           "kubernetes_scan": (set(), "kubernetes"), "cloudflare_scan": (set(), "cloudflare"),
           "r2_scan": (set(), "cloudflare"), "github_scan": (set(), "github")}
    for sid, (allowed, switch) in own.items():
        cond = str(steps[sid].get("if", ""))
        referenced = set(re.findall(r"steps\.([a-z_0-9]+)\.outcome", cond))
        assert referenced <= allowed, f"{sid} depends on {referenced - allowed}"
        assert f"steps.switches.outputs.{switch} == 'true'" in cond


def test_no_provider_variable_remains() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "DORA_PROWLER_PROVIDER" not in text
    for scan in SCANS:
        assert f"prowler_{scan}" in text, f"the {scan} scan writes its own OCSF file"


@pytest.mark.parametrize("secret", ["DORA_AWS_ROLE_ARN", "DORA_GCP_CREDENTIALS_JSON", "DORA_KUBECONFIG_B64",
                                    "DORA_CLOUDFLARE_API_TOKEN", "DORA_GITHUB_TOKEN"])
def test_every_credential_is_a_secret_mapped_to_env(secret: str) -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert f"secrets.{secret}" in text
    assert f"vars.{secret}" not in text, "a credential is never a plain variable"
