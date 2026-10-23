"""Tests for the connection settings the operator scripts share (`app/scripts/_connection.py`)."""

import pytest

from app.scripts._connection import (
    ConnectionConfigError,
    client_kwargs,
    resolve_connection,
)


class TestConnectionResolution:
    """Where the URI and database name come from.

    A runbook once told the operator to pass `--mongodb-uri "$MONGODB_URI"`. Those
    variables live in the container, not the operator's shell, so `docker compose
    exec` would expand them to empty strings on the host. Read the container's own
    environment instead, and keep the flags as overrides.
    """

    def test_reads_the_backend_container_environment(self):
        uri, database = resolve_connection(
            None,
            None,
            {"MONGODB_URI": "mongodb://in-container", "DATABASE_NAME": "auto_author"},
        )
        assert (uri, database) == ("mongodb://in-container", "auto_author")

    def test_falls_back_to_database_url(self):
        # The frontend container gets the same connection string under
        # DATABASE_URL; the backend's own settings prefer MONGODB_URI over it, so
        # accept either and in that order.
        uri, _ = resolve_connection(
            None, "db", {"DATABASE_URL": "mongodb://from-database-url"}
        )
        assert uri == "mongodb://from-database-url"

    def test_mongodb_uri_wins_over_database_url(self):
        uri, _ = resolve_connection(
            None,
            "db",
            {"MONGODB_URI": "mongodb://wins", "DATABASE_URL": "mongodb://loses"},
        )
        assert uri == "mongodb://wins"

    def test_explicit_flags_override_the_environment(self):
        uri, database = resolve_connection(
            "mongodb://explicit",
            "explicit_db",
            {"MONGODB_URI": "mongodb://env", "DATABASE_NAME": "env_db"},
        )
        assert (uri, database) == ("mongodb://explicit", "explicit_db")

    def test_says_which_variable_is_missing_rather_than_connecting_to_nothing(self):
        # An empty string is what host-side expansion of an unset variable
        # produces, and it is the failure this whole class exists to prevent.
        with pytest.raises(ConnectionConfigError, match="MONGODB_URI"):
            resolve_connection("", "db", {})
        with pytest.raises(ConnectionConfigError, match="DATABASE_NAME"):
            resolve_connection("mongodb://x", None, {})


class TestAtlasConnection:
    """Connect the way the app already connects.

    CI's MongoDB is a local `mongodb://`, where the TLS branch never runs, so
    nothing else would notice a difference. `app/db/base.py` already establishes
    what works against the Atlas cluster; match it.
    """

    def test_atlas_uris_get_explicit_tls_with_a_ca_bundle(self):
        # `.invalid` (RFC 2606), not a `*.mongodb.net` placeholder: the #544 guard
        # rejects any managed-cluster hostname in a tracked file of a public repo.
        # Only the scheme prefix matters here; nothing connects.
        kwargs = client_kwargs("mongodb+srv://cluster.invalid/")
        assert kwargs["tls"] is True
        assert kwargs["tlsAllowInvalidCertificates"] is False
        assert kwargs["tlsCAFile"].endswith(".pem")

    def test_plain_uris_get_no_tls_options(self):
        # A local mongodb:// has no certificate to verify, and forcing tls on
        # would break the very fixture the tests run against.
        assert client_kwargs("mongodb://127.0.0.1:27017") == {}
