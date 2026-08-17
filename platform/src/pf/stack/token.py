"""The catalogue's own credential, resolved rather than carried.

`pf.tools.openmetadata` reads `OPENMETADATA_JWT_TOKEN` from the environment and
nothing else, deliberately: it runs in CI and on laptops that have no business
holding a key to the catalogue database. That contract is right, and it is why
`catalog_sync` failed inside the stack with

    RuntimeError: 75 failed — classification/PlatformRole:
    OPENMETADATA_JWT_TOKEN is not set

— eight Dagster code locations publishing to a catalogue eighty milliseconds
away, blocked on a token whose documented provenance is "open the UI, go to
Settings, Bots, ingestion-bot, copy, paste into .env".

Inside the stack that hand-carry is unnecessary, and this module is the reason
why. The publisher and the server are now the same container, on the same
database, with the same `FERNET_KEY`; the bot's JWT is a row in
`user_entity`, encrypted with that key:

    {"authenticationMechanism": {"authType": "JWT",
      "config": {"JWTToken": "fernet:gAAAA…", "JWTTokenExpiry": "Unlimited"}}}

So the entrypoint decrypts it once at start and exports it, and every supervised
process inherits a credential nobody typed. Nothing is stored, nothing is
written to a file, and outside the stack the environment variable remains the
only source — which is what keeps a CI runner from needing database access to
publish a glossary.

## Why this is not a widening of trust

Reading it requires the admin role on the catalogue database *and* the Fernet
key. Anything holding both can already read every stored service connection
directly; deriving one bot token changes nothing about who can do what. What it
changes is that the token stops being copied by hand into a `.env`, where it
outlives the deployment that issued it and survives in shell history.
"""

from __future__ import annotations

from pf.stack.storage import Settings

#: OpenMetadata creates it on first start and it never expires
#: (`JWTTokenExpiry: Unlimited`). Overridable because a deployment may publish
#: under a bot of its own.
DEFAULT_BOT = "ingestion-bot"

ENV_TOKEN = "OPENMETADATA_JWT_TOKEN"
ENV_FERNET = "FERNET_KEY"

#: The prefix OpenMetadata puts on a value it encrypted. Absent on deployments
#: configured without a secrets manager, so its absence is a plaintext token
#: rather than an error.
FERNET_PREFIX = "fernet:"

# The bot flag is read out of the JSON, not off the `isbot` column beside it.
# That column is generated, and in OpenMetadata 1.13.3's Postgres DDL it is
# generated from the wrong field:
#
#   isbot boolean not null generated always as ((json ->> 'deleted')::boolean)
#
# So `where isBot = true` selects deleted users, matches nothing here, and
# reports "no JWT on bot 'ingestion-bot'" for a bot that is plainly there.
_QUERY = ("select json::jsonb #>> %s from user_entity "
          "where name = %s and json::jsonb ->> 'isBot' = 'true'")
_PATH = "{authenticationMechanism,config,JWTToken}"


class TokenUnavailable(RuntimeError):
    """Raised with what to do about it, not just what went wrong."""


def ingestion_jwt(admin: Settings, fernet_key: str, *,
                  bot: str = DEFAULT_BOT) -> str:
    """The bot's JWT, decrypted. Never logged, never written to disk.

    `admin` because the row lives in OpenMetadata's `public` schema and the
    `dagster` role deliberately has no rights there — the same separation that
    keeps Dagster's migrations out of the catalogue's tables also means Dagster's
    credentials cannot read this.
    """
    try:
        import psycopg2
    except ImportError as exc:  # pragma: no cover - environment, not logic
        raise TokenUnavailable(
            "psycopg2 is not installed — uv sync --extra stack") from exc

    conn = psycopg2.connect(admin.dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(_QUERY, (_PATH, bot))
            row = cur.fetchone()
    finally:
        conn.close()

    if not row or not row[0]:
        raise TokenUnavailable(
            f"no JWT on bot {bot!r} in {admin.db}. OpenMetadata creates it on "
            f"first start, so this usually means the server has not completed "
            f"a migration yet — check `podman logs pf_stack`.")

    return decrypt_stored(str(row[0]), fernet_key)


def decrypt_stored(stored: str, fernet_key: str) -> str:
    """A stored `JWTToken` value, decrypted if it needs to be."""
    if not stored.startswith(FERNET_PREFIX):
        # Configured without a secrets manager. Unusual, and not a failure.
        return stored

    if not fernet_key:
        raise TokenUnavailable(
            f"the token is encrypted but {ENV_FERNET} is empty. It must be the "
            f"key the row was written with; a different one does not error, it "
            f"fails to decrypt.")

    try:
        from cryptography.fernet import Fernet, InvalidToken
    except ImportError as exc:  # pragma: no cover - environment, not logic
        raise TokenUnavailable(
            "cryptography is not installed — uv sync --extra stack") from exc

    try:
        raw = Fernet(fernet_key).decrypt(stored[len(FERNET_PREFIX):].encode())
    except InvalidToken as exc:
        raise TokenUnavailable(
            f"{ENV_FERNET} does not decrypt this token. The catalogue was "
            f"written with a different key; changing it orphans every stored "
            f"credential, so restore the original rather than re-encrypting.",
        ) from exc
    except ValueError as exc:
        raise TokenUnavailable(f"{ENV_FERNET} is not a valid Fernet key: "
                               f"{exc}") from exc
    return raw.decode()


def resolve(env: dict[str, str], admin: Settings | None, *,
            bot: str = DEFAULT_BOT) -> tuple[str, str]:
    """`(token, where_it_came_from)`, preferring what was explicitly provided.

    An operator who sets `OPENMETADATA_JWT_TOKEN` means it — a bot with narrower
    rights, a remote catalogue — and silently replacing it with whatever this
    database happens to hold would be the kind of helpfulness that publishes to
    the wrong server.
    """
    given = (env.get(ENV_TOKEN) or "").strip()
    if given:
        return given, "environment"
    if admin is None:
        raise TokenUnavailable(
            f"{ENV_TOKEN} is not set and there is no catalogue database "
            f"configured to read it from — set it, or run inside the stack.")
    return ingestion_jwt(admin, env.get(ENV_FERNET, ""), bot=bot), "database"
