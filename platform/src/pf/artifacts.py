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

## Which stores this reaches

Five, through two code paths. R2 is the default and the only one configured out
of the box; the rest are three environment variables each.

    store          PF_ARTIFACTS_ENDPOINT                        REGION
    R2 (default)   (built in)                                   auto
    AWS S3         https://s3.<region>.amazonaws.com            the real region
    GCS            https://storage.googleapis.com               the real region
    floci          http://localhost:4566                        us-east-1
    Azure Blob     https://<account>.blob.core.windows.net      n/a

`PF_ARTIFACTS_REGION` is not optional anywhere but R2. SigV4 signs the region
into every request, so `auto` against real S3 returns
`AuthorizationHeaderMalformed` — which reads exactly like a bad key and is not
one. That cost an afternoon before it was written down here.

GCS needs its **XML API** and an HMAC key pair (Cloud Storage → Settings →
Interoperability), not a service-account JSON. The JSON key is what every other
GCP integration wants and it does not work here; the HMAC pair is what makes
GCS an S3-speaking store.

Azure Blob speaks none of that, which is why `backend` exists. floci is an
emulator and needs no real credentials at all — any non-empty pair signs, which
is what makes `pf artifacts` testable in CI without a cloud account.
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

# R2 accepts exactly this region and rejects a real AWS one, so it stays the
# default. It is **not** a value that works everywhere: SigV4 signs the region
# into the request, and real S3 rejects `auto` with `AuthorizationHeaderMalformed`
# — an error that reads like a credential fault and is not one. Any backend that
# is not R2 must set `PF_ARTIFACTS_REGION`; `Store.from_env` refuses to guess.
DEFAULT_REGION = "auto"

#: Which object store this is talking to. Inferred from the endpoint host, which
#: is unambiguous for all four, and overridable when a private endpoint or an
#: emulator hides the host that would have given it away.
#:
#: `s3` covers R2, real AWS S3, GCS-over-XML and floci, because all four speak
#: SigV4 over the same verbs. Azure Blob does not, and is the reason this is a
#: field rather than an assumption.
BACKENDS = ("s3", "azure")

#: Host suffixes that name a backend on sight.
_AZURE_HOSTS = (".blob.core.windows.net",)

#: Credential env vars, most specific first. See the module docstring for why
#: the AWS pair is last and why it is a trap on a machine that also uses AWS.
#: The Azure pair is last for the same reason the AWS pair is: it is a fallback
#: for a shell that already has it, not the name to set. On Azure `key_id` is
#: the storage account name and `secret` is one of its two account keys.
KEY_ID_VARS = ("PF_ARTIFACTS_ACCESS_KEY_ID", "R2_ACCESS_KEY_ID", "AWS_ACCESS_KEY_ID",
               "AZURE_STORAGE_ACCOUNT")
SECRET_VARS = ("PF_ARTIFACTS_SECRET_ACCESS_KEY", "R2_SECRET_ACCESS_KEY",
               "AWS_SECRET_ACCESS_KEY", "AZURE_STORAGE_KEY")

#: What to tell a caller that has no credentials. One string, so the CLI, the
#: recce integration and the UI all say the same thing.
SETUP_HINT = (
    "artefact store not configured — set PF_ARTIFACTS_ACCESS_KEY_ID and "
    "PF_ARTIFACTS_SECRET_ACCESS_KEY (an R2 API token with Object Read & Write "
    "on the bucket). For a store that is not R2, also set PF_ARTIFACTS_ENDPOINT "
    "and PF_ARTIFACTS_REGION — 'auto' is an R2-ism and real S3 rejects it. "
    "See docs/ARTIFACTS.md."
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


def infer_backend(endpoint: str) -> str:
    """Which protocol this endpoint speaks, from its host alone.

    Only Azure is detectable and only Azure needs detecting: R2, S3, GCS and
    floci all speak SigV4 and are handled by the same code, so guessing wrong
    between *them* is impossible. Anything unrecognised is `s3`, which is the
    right default for a private endpoint or a self-hosted MinIO.
    """
    host = endpoint.lower()
    return "azure" if any(h in host for h in _AZURE_HOSTS) else "s3"


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

    ## Why one type and not one class per cloud

    The four S3-speaking stores — R2, AWS S3, GCS over its XML API, and floci —
    differ by endpoint and signing region and by nothing else this module cares
    about. Azure Blob differs by protocol. That is one real split, so `backend`
    is one field and the five operations dispatch on it; a class hierarchy would
    have put four identical subclasses around the one that is different.

    The field names stay S3's because they are the ones every caller already
    uses. On Azure they mean: `endpoint` is the account URL, `bucket` is the
    container, `key_id` is the storage account name, `secret` is an account key.
    """

    endpoint: str
    bucket: str
    key_id: str = field(repr=False)
    secret: str = field(repr=False)
    #: One of `BACKENDS`. Inferred from the endpoint unless overridden.
    backend: str = "s3"
    #: SigV4 signing region. Ignored by the Azure backend.
    region: str = DEFAULT_REGION

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
        endpoint = os.environ.get("PF_ARTIFACTS_ENDPOINT") or DEFAULT_ENDPOINT
        backend = os.environ.get("PF_ARTIFACTS_BACKEND") or infer_backend(endpoint)
        if backend not in BACKENDS:
            raise ArtifactStoreError(
                f"PF_ARTIFACTS_BACKEND={backend!r} is not one of {BACKENDS}")
        return cls(
            endpoint=endpoint,
            bucket=os.environ.get("PF_ARTIFACTS_BUCKET") or DEFAULT_BUCKET,
            key_id=key_id, secret=secret,
            backend=backend,
            region=os.environ.get("PF_ARTIFACTS_REGION") or DEFAULT_REGION,
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
            "backend": self.backend,
            # Printed because `auto` against real S3 is a signing failure that
            # reads as a credential failure. Seeing the region is what turns
            # that twenty-minute confusion into a one-line fix.
            "region": self.region if self.backend == "s3" else "—",
            "key_id": self.key_id[:4] + "…" if len(self.key_id) > 4 else "set",
            "source": next((n for n in KEY_ID_VARS if os.environ.get(n)), ""),
        }

    def url(self, key: str) -> str:
        scheme = "az" if self.backend == "azure" else "s3"
        return f"{scheme}://{self.bucket}/{key}"

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
            "s3", endpoint_url=self.endpoint, region_name=self.region, config=cfg,
            aws_access_key_id=self.key_id, aws_secret_access_key=self.secret,
        )

    def container(self):
        """The Azure container client. Mirrors `client()` for the other backend."""
        try:
            from azure.storage.blob import ContainerClient
        except ImportError as exc:  # pragma: no cover - depends on install extras
            raise ArtifactStoreError(
                "azure-storage-blob is not installed — "
                "`uv sync --extra artifacts-azure`") from exc

        return ContainerClient(
            account_url=self.endpoint, container_name=self.bucket,
            # The account key, not a connection string: a connection string
            # carries the endpoint too, and two sources for one value is how
            # they end up disagreeing.
            credential={"account_name": self.key_id, "account_key": self.secret},
        )

    # -- operations --
    def put(self, key: str, path: Path) -> int:
        """Upload one file. Returns its size in bytes."""
        p = Path(path)
        if not p.is_file():
            raise ArtifactStoreError(f"nothing to upload at {p}")
        try:
            if self.backend == "azure":
                with p.open("rb") as fh:
                    self.container().upload_blob(name=key, data=fh, overwrite=True)
            else:
                self.client().upload_file(str(p), self.bucket, key)
        except Exception as exc:  # each SDK raises a family, not a base we own
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
            if self.backend == "azure":
                with tmp.open("wb") as fh:
                    self.container().download_blob(key).readinto(fh)
            else:
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
            if self.backend == "azure":
                return bool(self.container().get_blob_client(key).exists())
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
            if self.backend == "azure":
                for b in self.container().list_blobs(name_starts_with=prefix):
                    out.append({
                        "key": b.name, "size": b.size or 0,
                        "modified": str(b.last_modified or ""),
                    })
                return out
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
            if self.backend == "azure":
                # get_container_properties, not list_blobs: listing an empty
                # container succeeds lazily and would report a container that
                # does not exist as reachable, which is the exact failure
                # `preflight` exists to prevent.
                self.container().get_container_properties()
            else:
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

    Azure's SDK raises `ResourceNotFoundError`, which carries `status_code` and
    no `response` dict. It is matched on the status rather than the class so
    this module never has to import `azure.core` — which is an extra, and would
    make an S3-only install fail at the point it handled an S3 error.
    `ContainerNotFound` is deliberately *not* here, for the same reason
    `NoSuchBucket` is not: it is "you are pointed at nothing".
    """
    if getattr(exc, "status_code", None) == 404:
        code = str(getattr(exc, "error_code", "") or "")
        return code != "ContainerNotFound"
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
