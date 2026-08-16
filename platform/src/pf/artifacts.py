"""Remote artefact store — where build artefacts live instead of in git.

`pf.tools.recce`'s own docstring names the gap this module closes:

    Fetching production artefacts — better, and unavailable here: the platform
    is local-first and there is no artefact registry to fetch from.

There is one now. It is an S3-compatible bucket (Cloudflare R2), and it exists
because the alternative was carrying build output in the repository. That was a
deliberate, documented trade — a reviewer on another machine can reproduce the
numbers in a summary only if the baseline travels with the branch — and it held
until jaffle-shop, whose 996 marts made the same three files 30 MB, larger than
the whole repository's history, rewritten in full on every review run.

Committing them and ignoring them are both wrong for the same reason: they are
**inputs on a machine that did not build them** and **output on the machine that
did**. Git models neither. A bucket does: the producer pushes, every consumer
pulls, and nothing about a 20 MB file has to pass through a diff.

## What this module is, and is not

It is a thin, explicit put/get over one bucket. No sync semantics, no manifest,
no caching layer, no lifecycle rules. Callers name a key and a path, in both
directions, and get told what moved. Everything clever belongs upstream of here,
in the tool that knows what its artefacts *mean* — `pf.tools.recce` decides that
a baseline is keyed by the base ref and a review by the head ref, because those
are recce's semantics and not the store's.

It is also **optional**. A store that is not configured is not an error: every
entry point degrades to local-only behaviour, which is exactly what a developer
with a warehouse on their laptop wants. `NotConfigured` is raised only by the
commands whose entire purpose is to talk to the bucket.

## Layout

Keys mirror the repository, so the bucket reads like a checkout:

    groups/<group>/projects/<project>/transform/target-base/<base-ref>/manifest.json
    groups/<group>/projects/<project>/transform/reviews/<head-ref>/recce_state.json

The trailing ref segment is the part git gave us for free and object storage
does not. Two branches reviewing the same project write two keys rather than
racing for one, which is the conflict that made the committed artefacts painful
in the first place — moving them to a single shared key would have moved the
problem rather than solved it.

## Credentials

Never in a file. Read from the environment, in this order, first match wins:

    PF_ARTIFACTS_ACCESS_KEY_ID   R2_ACCESS_KEY_ID   AWS_ACCESS_KEY_ID
    PF_ARTIFACTS_SECRET_ACCESS_KEY   R2_SECRET_ACCESS_KEY   AWS_SECRET_ACCESS_KEY

The `PF_`-prefixed pair is the one to set. The R2 and AWS fallbacks exist so a
shell or a CI job that already has S3 credentials for this bucket does not need
a second copy under a third name — but a machine that talks to *both* AWS and R2
must set the `PF_` pair, or the AWS fallback will point this at the wrong
endpoint's credentials and every call will 403.

The endpoint and bucket are **not** credentials — an R2 endpoint carries the
account id, which every client needs and no client can act on alone — so they
are committed as defaults below and overridable by env for a fork or a second
environment.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# The bucket this platform publishes to. Overridable, so a fork or a staging
# environment is two env vars rather than a patch.
DEFAULT_ENDPOINT = "https://3138e619a0287a5f6e9f343aa3d0b9a1.r2.cloudflarestorage.com"
DEFAULT_BUCKET = "data-platform"

# R2 accepts exactly this region and rejects a real AWS one. It is not a
# placeholder to be filled in later.
REGION = "auto"

#: Credential env vars, most specific first. See the module docstring for why
#: the AWS pair is last and why it is a trap on a machine that also uses AWS.
KEY_ID_VARS = ("PF_ARTIFACTS_ACCESS_KEY_ID", "R2_ACCESS_KEY_ID", "AWS_ACCESS_KEY_ID")
SECRET_VARS = ("PF_ARTIFACTS_SECRET_ACCESS_KEY", "R2_SECRET_ACCESS_KEY",
               "AWS_SECRET_ACCESS_KEY")

#: What to tell a caller that has no credentials. One string, so the CLI, the
#: recce integration and the UI all say the same thing.
SETUP_HINT = (
    "artefact store not configured — set PF_ARTIFACTS_ACCESS_KEY_ID and "
    "PF_ARTIFACTS_SECRET_ACCESS_KEY (an R2 API token with Object Read & Write "
    "on the bucket). See docs/ARTIFACTS.md."
)


class ArtifactStoreError(RuntimeError):
    """Anything that went wrong talking to the bucket."""


class NotConfigured(ArtifactStoreError):
    """No credentials in the environment. Raised only where a bucket is required."""


# ------------------------------------------------------------------ refs --
def _first_env(names: tuple[str, ...]) -> str:
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return ""


def sanitize_ref(ref: str) -> str:
    """A git ref as a key segment.

    Slashes survive: `feat/store` becomes a nested prefix, which is what makes
    the bucket browsable by feature. Everything else that would make a key
    awkward to type or to list is collapsed to a dash. An empty result is
    `unknown` rather than an empty segment, which would silently join two path
    components into one.
    """
    s = re.sub(r"\s+", "-", (ref or "").strip())
    s = re.sub(r"[^A-Za-z0-9._/-]", "-", s)
    s = re.sub(r"/{2,}", "/", s).strip("/")
    return s or "unknown"


def _git(*args: str, cwd: Path | None = None) -> str:
    try:
        p = subprocess.run(["git", *args], cwd=str(cwd) if cwd else None,
                           capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return p.stdout.strip() if p.returncode == 0 else ""


def head_ref(cwd: Path | None = None) -> str:
    """Which branch's *work* this is — the key segment a review is filed under.

    On GitHub Actions the checked-out ref for a pull request is a detached merge
    commit, so `git branch --show-current` is empty and `GITHUB_HEAD_REF` is the
    only thing that names the branch under review. Locally it is the other way
    round. Explicit override first, for a machine that is neither.
    """
    return sanitize_ref(
        os.environ.get("PF_ARTIFACTS_REF")
        or os.environ.get("GITHUB_HEAD_REF")
        or _git("branch", "--show-current", cwd=cwd)
        or "local"
    )


def base_ref(cwd: Path | None = None) -> str:
    """Which branch a diff is *against* — the key segment a baseline is filed under.

    A baseline is not per-developer state: it is one known-good build of a
    trunk, published once and pulled by everyone diffing against it. Keying it
    by `head_ref` would give every feature branch its own baseline, each
    captured from that branch's own code, and a diff against yourself is clean
    by construction — the exact false negative `capture_baseline` builds into
    the `base` target to avoid.
    """
    return sanitize_ref(
        os.environ.get("PF_ARTIFACTS_BASE_REF")
        or os.environ.get("GITHUB_BASE_REF")
        or "main"
    )


def project_prefix(group: str, project: str) -> str:
    """Repo-relative path of a project, which is also its key prefix."""
    return f"groups/{group}/projects/{project}"


# ----------------------------------------------------------------- store --
@dataclass(frozen=True)
class Store:
    """One bucket, and the credentials to reach it.

    Credential-carrying, so the credentials are kept out of `repr`. That is not
    tidiness: `repr` is what a traceback prints, Rich renders tracebacks with
    locals, and typer renders exceptions with Rich — so an unhandled error
    anywhere below `Store.required()` would have put the secret access key on
    screen and into whatever CI captured it. It did, until this was checked.

    `describe()` is the safe rendering and is what the CLI prints: endpoint,
    bucket, a four-character prefix of the key id, and which env var it came
    from. Never the secret, in any form.
    """

    endpoint: str
    bucket: str
    key_id: str = field(repr=False)
    secret: str = field(repr=False)

    # -- construction --
    @classmethod
    def from_env(cls) -> Store | None:
        """A configured store, or None. Never raises — the caller decides.

        Returning None rather than raising is what lets every recce entry point
        keep working on a laptop with no bucket. The commands that exist only to
        talk to the bucket call `required()` instead.
        """
        key_id, secret = _first_env(KEY_ID_VARS), _first_env(SECRET_VARS)
        if not (key_id and secret):
            return None
        return cls(
            endpoint=os.environ.get("PF_ARTIFACTS_ENDPOINT") or DEFAULT_ENDPOINT,
            bucket=os.environ.get("PF_ARTIFACTS_BUCKET") or DEFAULT_BUCKET,
            key_id=key_id, secret=secret,
        )

    @classmethod
    def required(cls) -> Store:
        s = cls.from_env()
        if s is None:
            raise NotConfigured(SETUP_HINT)
        return s

    def describe(self) -> dict[str, str]:
        """Everything about this store that is safe to print."""
        return {
            "endpoint": self.endpoint,
            "bucket": self.bucket,
            "key_id": self.key_id[:4] + "…" if len(self.key_id) > 4 else "set",
            "source": next((n for n in KEY_ID_VARS if os.environ.get(n)), ""),
        }

    def url(self, key: str) -> str:
        return f"s3://{self.bucket}/{key}"

    # -- client --
    def client(self):  # botocore's client type is dynamic; no annotation to give
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:  # pragma: no cover - depends on install extras
            raise ArtifactStoreError(
                "boto3 is not installed — `uv sync --extra artifacts`") from exc

        # R2 rejects the flexible checksum headers botocore ≥1.36 sends by
        # default on PutObject, with a signature error that reads like bad
        # credentials. `when_required` restores the pre-1.36 behaviour. The
        # kwarg does not exist on older botocore, hence the fallback rather
        # than a version pin — either version works, only one needs the flag.
        opts = {"signature_version": "s3v4",
                "retries": {"max_attempts": 3, "mode": "standard"}}
        try:
            cfg = Config(request_checksum_calculation="when_required", **opts)
        except TypeError:  # pragma: no cover - botocore < 1.36
            cfg = Config(**opts)

        return boto3.client(
            "s3", endpoint_url=self.endpoint, region_name=REGION, config=cfg,
            aws_access_key_id=self.key_id, aws_secret_access_key=self.secret,
        )

    # -- operations --
    def put(self, key: str, path: Path) -> int:
        """Upload one file. Returns its size in bytes."""
        p = Path(path)
        if not p.is_file():
            raise ArtifactStoreError(f"nothing to upload at {p}")
        try:
            self.client().upload_file(str(p), self.bucket, key)
        except Exception as exc:  # botocore raises a family, not a base we own
            raise ArtifactStoreError(f"upload failed for {self.url(key)}: {exc}") from exc
        return p.stat().st_size

    def get(self, key: str, path: Path) -> int:
        """Download one key. Returns bytes written, or -1 if the key is absent.

        Absent is a normal answer, not a failure: a project reviewed for the
        first time has no baseline in the bucket, and that is the state
        `pf tool recce ci` is written to handle.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        # Download beside the target and rename, so an interrupted transfer
        # cannot leave a half-written manifest that dbt will happily parse.
        tmp = p.with_suffix(p.suffix + ".part")
        try:
            self.client().download_file(self.bucket, key, str(tmp))
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            if _is_missing(exc):
                return -1
            raise ArtifactStoreError(f"download failed for {self.url(key)}: {exc}") from exc
        tmp.replace(p)
        return p.stat().st_size

    def exists(self, key: str) -> bool:
        try:
            self.client().head_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            if _is_missing(exc):
                return False
            raise ArtifactStoreError(f"head failed for {self.url(key)}: {exc}") from exc
        return True

    def ls(self, prefix: str = "") -> list[dict[str, object]]:
        """Every key under a prefix, with size and last-modified."""
        out: list[dict[str, object]] = []
        try:
            pages = self.client().get_paginator("list_objects_v2").paginate(
                Bucket=self.bucket, Prefix=prefix)
            for page in pages:
                for obj in page.get("Contents", []):
                    out.append({
                        "key": obj["Key"], "size": obj.get("Size", 0),
                        "modified": str(obj.get("LastModified", "")),
                    })
        except Exception as exc:
            raise ArtifactStoreError(f"list failed for {prefix}: {exc}") from exc
        return out

    def check(self) -> str:
        """Can we actually reach the bucket? Returns '' on success, else why not."""
        try:
            self.client().list_objects_v2(Bucket=self.bucket, MaxKeys=1)
        except Exception as exc:  # noqa: BLE001 — "why not" is the return value
            return str(exc)
        return ""

    def preflight(self) -> None:
        """`check`, as an exception. Call before a download that treats absence as normal.

        A download cannot distinguish "no such key" from "no such bucket" and
        never will: `download_file` issues a HEAD first, HEAD replies have no
        body, so botocore has nothing but the status line and reports a bare
        `404` either way. Pointed at a bucket that does not exist, `pull` then
        prints a calm list of "absent" for every artefact — which is what it did
        the first time it was run against this store, and reads exactly like
        "nothing has been published yet".

        One ListObjectsV2 turns that into "you are pointed at nothing". It costs
        a round trip on a path that is already doing network I/O.
        """
        why = self.check()
        if why:
            raise ArtifactStoreError(f"cannot reach {self.url('')}: {why}")


def _is_missing(exc: Exception) -> bool:
    """Is this exception 'the key/bucket is not there' rather than a real fault?

    botocore reports a missing key differently depending on the call —
    `head_object` and `download_file` raise `ClientError` carrying `404`,
    `get_object` carries `NoSuchKey`. Treating a genuine permission error as
    'absent' would turn a broken token into a silent 'nothing published yet',
    so the match is on those documented codes only: 403 stays an error, and so
    does `NoSuchBucket`, which was in this set until a test against a bucket
    that had not been created yet reported four cheerful lines of "absent"
    instead of "you are pointed at nothing".
    """
    resp = getattr(exc, "response", None)
    if not isinstance(resp, dict):
        return False
    err = resp.get("Error")
    code = str(err.get("Code", "")) if isinstance(err, dict) else ""
    return code in {"404", "NoSuchKey", "NotFound"}


# ------------------------------------------------------------- transfers --
@dataclass(frozen=True)
class Transfer:
    """One file that moved, or did not. `size` is -1 when the key was absent."""

    key: str
    path: Path
    size: int

    @property
    def ok(self) -> bool:
        return self.size >= 0


def push_files(store: Store, pairs: list[tuple[str, Path]]) -> list[Transfer]:
    """Upload each (key, path) whose path exists. Missing files are skipped.

    Skipped rather than fatal: `catalog.json` only exists after
    `dbt docs generate`, and a baseline without it is a degraded diff, not a
    broken one — the same rule `capture_baseline` already applies locally.
    """
    out = []
    for key, path in pairs:
        if not Path(path).is_file():
            continue
        out.append(Transfer(key, Path(path), store.put(key, Path(path))))
    return out


def pull_files(store: Store, pairs: list[tuple[str, Path]]) -> list[Transfer]:
    """Download each (key, path). A key that is not in the bucket yields size -1.

    Preflights the bucket first — see `Store.preflight` for why absence alone
    is not a trustworthy answer here.
    """
    if pairs:
        store.preflight()
    return [Transfer(key, Path(path), store.get(key, Path(path))) for key, path in pairs]


def human(size: int) -> str:
    if size < 0:
        return "absent"
    if size < 1024:
        return f"{size} B"
    n = size / 1024
    for unit in ("KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"  # pragma: no cover - unreachable, kept for the type
