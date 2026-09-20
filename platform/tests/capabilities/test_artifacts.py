"""Which object store `pf artifacts` is actually talking to.

Every failure this file guards is a *silent* one. A store resolved against the
wrong backend does not raise at construction; it raises three network calls
later, in a message written by somebody else's SDK, about a credential that is
fine. The specific ones that have cost time:

  - `region=auto` is an R2-ism. Real S3 signs it into SigV4 and answers
    `AuthorizationHeaderMalformed`, which reads as a bad key and is not one.
  - A 403 treated as "absent" turns a revoked token into a calm "nothing has
    been published yet", and CI then reviews against an empty baseline.
  - `Store` carries a secret. `repr` is what Rich prints in a traceback, and
    typer renders exceptions with Rich.

So these assert the handful of values that decide those three things, not the
shape of the dataclass.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pf import artifacts as A

AZURE = "https://pfacct.blob.core.windows.net"
CREDS = {
    "PF_ARTIFACTS_ACCESS_KEY_ID": "AKIAEXAMPLEKEY",
    "PF_ARTIFACTS_SECRET_ACCESS_KEY": "not-a-real-secret",
    # main moved the endpoint to the environment (it carries an account id), so a
    # configured store is the pair *and* an endpoint; this one is R2's shape.
    "PF_ARTIFACTS_ENDPOINT": "https://0123456789abcdef.r2.cloudflarestorage.com",
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """No PF_ARTIFACTS_* leaking in from the developer's shell or from CI.

    Without this the suite passes or fails depending on whose laptop it runs
    on, which is worse than not having it.
    """
    for key in list(os.environ):
        if key.startswith(("PF_ARTIFACTS", "R2_", "AZURE_STORAGE")):
            monkeypatch.delenv(key, raising=False)
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(key, raising=False)


def store(monkeypatch: pytest.MonkeyPatch, **env: str) -> A.Store:
    for k, v in {**CREDS, **env}.items():
        monkeypatch.setenv(k, v)
    s = A.Store.from_env()
    assert s is not None
    return s


# ----------------------------------------------------------- resolution --
def test_no_credentials_is_none_rather_than_an_exception() -> None:
    """Every recce entry point calls this on laptops with no bucket."""
    assert A.Store.from_env() is None


def test_azure_is_recognised_from_the_endpoint_alone(
        monkeypatch: pytest.MonkeyPatch) -> None:
    assert store(monkeypatch, PF_ARTIFACTS_ENDPOINT=AZURE).backend == "azure"


@pytest.mark.parametrize("endpoint", [
    "https://s3.eu-west-1.amazonaws.com",     # real AWS
    "https://storage.googleapis.com",         # GCS over the XML API
    "http://localhost:4566",                  # floci
    "https://minio.internal:9000",            # anything self-hosted
])
def test_everything_that_is_not_azure_is_s3(
        monkeypatch: pytest.MonkeyPatch, endpoint: str) -> None:
    """The four S3-speaking stores differ by endpoint and by nothing else here."""
    assert store(monkeypatch, PF_ARTIFACTS_ENDPOINT=endpoint).backend == "s3"


def test_the_backend_can_be_forced_past_the_endpoint(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A private endpoint hides the host that would have named the backend."""
    s = store(monkeypatch, PF_ARTIFACTS_ENDPOINT="https://blob.internal",
              PF_ARTIFACTS_BACKEND="azure")
    assert s.backend == "azure"


def test_an_unknown_backend_is_refused_at_construction(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Named now, or three calls later inside somebody else's SDK."""
    for k, v in {**CREDS, "PF_ARTIFACTS_BACKEND": "gcs"}.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(A.ArtifactStoreError, match="gcs"):
        A.Store.from_env()


# --------------------------------------------------------------- region --
def test_r2_keeps_auto_because_r2_rejects_a_real_region(
        monkeypatch: pytest.MonkeyPatch) -> None:
    assert store(monkeypatch).region == "auto"


def test_a_real_region_survives_to_the_signer(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """The whole point: `auto` against real S3 is AuthorizationHeaderMalformed."""
    s = store(monkeypatch, PF_ARTIFACTS_ENDPOINT="https://s3.eu-west-1.amazonaws.com",
              PF_ARTIFACTS_REGION="eu-west-1")
    assert s.region == "eu-west-1"


def test_status_shows_the_region_so_the_signing_error_is_diagnosable(
        monkeypatch: pytest.MonkeyPatch) -> None:
    d = store(monkeypatch, PF_ARTIFACTS_ENDPOINT="https://s3.us-east-1.amazonaws.com",
              PF_ARTIFACTS_REGION="us-east-1").describe()
    assert d["region"] == "us-east-1"
    assert d["backend"] == "s3"


def test_azure_reports_no_region_rather_than_a_meaningless_one(
        monkeypatch: pytest.MonkeyPatch) -> None:
    assert store(monkeypatch, PF_ARTIFACTS_ENDPOINT=AZURE).describe()["region"] == "—"


# ------------------------------------------------------------ rendering --
def test_an_azure_url_names_the_protocol_it_will_actually_use(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """An az:// key pasted into an `aws s3` command should look wrong on sight."""
    assert store(monkeypatch, PF_ARTIFACTS_ENDPOINT=AZURE).url("k.json") == \
        "az://data-platform/k.json"


def test_an_s3_url_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    assert store(monkeypatch).url("k.json") == "s3://data-platform/k.json"


def test_the_secret_is_in_no_rendering_of_the_store(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Rich prints locals in tracebacks; typer renders exceptions with Rich."""
    s = store(monkeypatch, PF_ARTIFACTS_ENDPOINT=AZURE)
    assert CREDS["PF_ARTIFACTS_SECRET_ACCESS_KEY"] not in repr(s)
    assert CREDS["PF_ARTIFACTS_SECRET_ACCESS_KEY"] not in str(s.describe())
    assert s.describe()["key_id"].endswith("…")


# -------------------------------------------------------------- absence --
class _Err(Exception):
    """Stands in for an SDK error carrying a status the way Azure's does."""

    def __init__(self, status: int | None = None, code: str = "",
                 response: dict | None = None) -> None:
        self.status_code = status
        self.error_code = code
        if response is not None:
            self.response = response


def test_an_azure_404_is_absence() -> None:
    assert A._is_missing(_Err(status=404, code="BlobNotFound")) is True


def test_a_missing_container_is_not_absence() -> None:
    """Otherwise `pull` prints a calm 'absent' per artefact against no container."""
    assert A._is_missing(_Err(status=404, code="ContainerNotFound")) is False


def test_a_403_is_never_absence() -> None:
    """A revoked token must not read as 'nothing published yet'."""
    assert A._is_missing(_Err(status=403, code="AuthenticationFailed")) is False
    assert A._is_missing(_Err(response={"Error": {"Code": "403"}})) is False


def test_the_s3_codes_still_mean_what_they_did() -> None:
    for code in ("404", "NoSuchKey", "NotFound"):
        assert A._is_missing(_Err(response={"Error": {"Code": code}})) is True
    assert A._is_missing(_Err(response={"Error": {"Code": "NoSuchBucket"}})) is False


def test_an_unrecognisable_exception_is_a_fault_not_an_absence() -> None:
    assert A._is_missing(RuntimeError("connection reset")) is False


# ------------------------------------------------------------ transfers --
def test_push_skips_a_file_that_was_never_built(tmp_path: Path) -> None:
    """catalog.json only exists after `dbt docs generate`; that is degraded, not broken."""
    moved: list[str] = []

    class FakeStore:
        def put(self, key: str, path: Path) -> int:
            moved.append(key)
            return Path(path).stat().st_size

    present = tmp_path / "manifest.json"
    present.write_text("{}")
    out = A.push_files(FakeStore(), [                     # type: ignore[arg-type]
        ("k/manifest.json", present),
        ("k/catalog.json", tmp_path / "catalog.json"),
    ])
    assert moved == ["k/manifest.json"]
    assert [t.key for t in out] == ["k/manifest.json"]
    assert all(t.ok for t in out)


def test_an_absent_key_is_reported_not_raised() -> None:
    assert A.Transfer("k", Path("p"), -1).ok is False
    assert A.human(-1) == "absent"


# ------------------------------------------------------------- deletion --
#: Two sisters in one group. The one that leaves and the one that must still be
#: there afterwards — offboarding is the only operation in this module whose
#: blast radius reaches a tenant that did not ask for anything.
IND = A.project_prefix("commodity", "commodity-india")
BRA = A.project_prefix("commodity", "commodity-brazil")


class _FakeS3:
    """Enough of botocore's client for the three calls deletion makes.

    A fake and not a bucket: every test below is about what happens *before*
    the network, and a suite that needed credentials would be a suite nobody
    runs. Paginated two keys to a page, because "stopped at the first page" is
    the failure `delete_prefix` has to not have and a fake that returns
    everything in one go cannot catch it.
    """

    PAGE = 2

    def __init__(self, keys: list[str]) -> None:
        self.keys = list(keys)
        self.deleted: list[str] = []

    def get_paginator(self, name: str) -> _FakeS3:
        assert name == "list_objects_v2"
        return self

    def paginate(self, *, Bucket: str, Prefix: str = "") -> list[dict]:
        hits = sorted(k for k in self.keys if k.startswith(Prefix))
        return [{"Contents": [{"Key": k, "Size": 1} for k in hits[i:i + self.PAGE]]}
                for i in range(0, len(hits), self.PAGE)]

    def head_object(self, *, Bucket: str, Key: str) -> dict:
        if Key not in self.keys:
            raise _Err(response={"Error": {"Code": "404"}})
        return {}

    def delete_object(self, *, Bucket: str, Key: str) -> dict:
        # Idempotent, exactly like the real one: a key that was never there
        # deletes fine and answers 204, which is why `delete` buys the HEAD.
        self.deleted.append(Key)
        self.keys = [k for k in self.keys if k != Key]
        return {}


def s3(monkeypatch: pytest.MonkeyPatch, keys: list[str]) -> tuple[A.Store, _FakeS3]:
    fake = _FakeS3(keys)
    s = store(monkeypatch)
    monkeypatch.setattr(A.Store, "client", lambda self: fake)
    return s, fake


def test_delete_reports_that_the_key_was_there(
        monkeypatch: pytest.MonkeyPatch) -> None:
    s, fake = s3(monkeypatch, [f"{IND}/transform/reviews/main/recce_state.json"])
    assert s.delete(f"{IND}/transform/reviews/main/recce_state.json") is True
    assert fake.keys == []


def test_deleting_a_key_that_was_never_published_is_not_an_error(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Offboarding walks keys that *might* exist — a project reviewed once has no catalog."""
    s, fake = s3(monkeypatch, [f"{IND}/transform/target-base/main/manifest.json"])
    assert s.delete(f"{IND}/transform/target-base/main/catalog.json") is False
    assert fake.deleted == []


def test_a_403_on_delete_is_a_fault_not_an_absence(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A revoked token must not read as 'that was already gone'."""
    s, fake = s3(monkeypatch, [f"{IND}/manifest.json"])

    def refuse(**_kw: str) -> dict:
        raise _Err(response={"Error": {"Code": "403"}})

    monkeypatch.setattr(fake, "delete_object", refuse)
    with pytest.raises(A.ArtifactStoreError, match="delete failed"):
        s.delete(f"{IND}/manifest.json")


def test_delete_prefix_is_a_dry_run_unless_told_otherwise(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """The default is the feature: a mistyped sister must not be unrecoverable."""
    keys = [f"{IND}/a.json", f"{IND}/b.json"]
    s, fake = s3(monkeypatch, keys)
    assert s.delete_prefix(IND) == keys
    assert fake.deleted == []
    assert fake.keys == keys


def test_delete_prefix_removes_when_it_is_not_a_dry_run(
        monkeypatch: pytest.MonkeyPatch) -> None:
    s, fake = s3(monkeypatch, [f"{IND}/a.json", f"{IND}/b.json", f"{BRA}/a.json"])
    assert s.delete_prefix(IND, dry_run=False) == [f"{IND}/a.json", f"{IND}/b.json"]
    assert fake.keys == [f"{BRA}/a.json"]


def test_delete_prefix_walks_every_page_not_just_the_first(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Truncating at a page boundary reports a clean offboarding and leaves the tail."""
    keys = [f"{IND}/r{i:02d}.json" for i in range(7)]      # four pages of two
    s, fake = s3(monkeypatch, [*keys, f"{BRA}/keep.json"])
    assert s.delete_prefix(IND, dry_run=False) == keys
    assert fake.keys == [f"{BRA}/keep.json"]


@pytest.mark.parametrize("prefix", ["", "   ", "/", "///"])
def test_an_empty_prefix_is_refused_even_when_it_is_not_a_dry_run(
        monkeypatch: pytest.MonkeyPatch, prefix: str) -> None:
    """It matches every key every sister ever published, and nothing says so."""
    s, fake = s3(monkeypatch, [f"{IND}/a.json", f"{BRA}/a.json"])
    with pytest.raises(A.ArtifactStoreError, match="every key"):
        s.delete_prefix(prefix, dry_run=False)
    assert fake.deleted == []


@pytest.mark.parametrize("prefix", ["groups", "groups/", "transform/reviews"])
def test_a_prefix_that_names_no_tenant_is_refused(
        monkeypatch: pytest.MonkeyPatch, prefix: str) -> None:
    """`groups/` is every tenant in the bucket; anything outside it is not a key we wrote."""
    s, fake = s3(monkeypatch, [f"{IND}/a.json", f"{BRA}/a.json"])
    with pytest.raises(A.ArtifactStoreError, match="not scoped to one tenant"):
        s.delete_prefix(prefix, dry_run=False)
    assert fake.deleted == []


def test_a_whole_group_is_a_tenant_and_is_allowed(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """The shallowest thing that is still one tenant's — a group offboarding is real."""
    s, _ = s3(monkeypatch, [f"{IND}/a.json", f"{BRA}/a.json"])
    assert s.delete_prefix("groups/commodity") == [f"{BRA}/a.json", f"{IND}/a.json"]
