"""MongoDB connection settings shared by the operator scripts in this package."""

import certifi


class ConnectionConfigError(Exception):
    """No usable connection string or database name was given."""


def client_kwargs(uri):
    """TLS options for an Atlas URI, matching how the app itself connects.

    `app/db/base.py` branches on the same `mongodb+srv://` prefix and passes an
    explicit CA bundle. That is the configuration known to reach this cluster; a
    one-shot operator run is the wrong place to find out that a bare client would
    also have worked.
    """
    if not uri.startswith("mongodb+srv://"):
        return {}
    return {
        "tls": True,
        "tlsCAFile": certifi.where(),
        "tlsAllowInvalidCertificates": False,
    }


def resolve_connection(uri, database, env):
    """Take the connection from the flags, else from the process environment.

    The scripts run inside a backend container, where compose has already put
    `MONGODB_URI` and `DATABASE_NAME`. Requiring the operator to pass them as
    `--mongodb-uri "$MONGODB_URI"` under `docker compose exec` would expand them
    on the *host*, where they are unset, so the run would target an empty URI.

    `DATABASE_URL` is the same connection string under the name the frontend
    container sees; the backend's settings prefer `MONGODB_URI` over it, so match
    that order rather than inventing a new one.
    """
    uri = uri or env.get("MONGODB_URI") or env.get("DATABASE_URL")
    database = database or env.get("DATABASE_NAME")
    if not uri:
        raise ConnectionConfigError(
            "no MongoDB connection string: pass --mongodb-uri, or run where "
            "MONGODB_URI (or DATABASE_URL) is set. If you are using `docker compose "
            "exec`, note that $MONGODB_URI in that command line is expanded by your "
            "shell, not the container's."
        )
    if not database:
        raise ConnectionConfigError(
            "no database name: pass --database, or run where DATABASE_NAME is set."
        )
    return uri, database
