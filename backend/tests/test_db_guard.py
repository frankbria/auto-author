"""Tests for the test-DB teardown safety guard (#211).

The guard is pure string logic (no Mongo connection), so these run without a live
database. The headline pin is the Atlas-wipe scenario from the issue.
"""

import pytest

from tests.db_guard import assert_safe_test_db, _hosts_all_local


class TestAssertSafeTestDb:
    def test_accidental_atlas_uri_raises(self):
        # The exact scenario from #211: remote srv host + a real, non-test DB name.
        with pytest.raises(RuntimeError, match="Refusing to run destructive"):
            assert_safe_test_db(
                "mongodb+srv://user:pw@cluster0.abcde.mongodb.net/auto-author",
                "auto-author",
            )

    def test_remote_plain_host_real_db_raises(self):
        with pytest.raises(RuntimeError):
            assert_safe_test_db("mongodb://db.prod.internal:27017/auto-author", "auto-author")

    def test_empty_db_name_on_remote_raises(self):
        with pytest.raises(RuntimeError):
            assert_safe_test_db("mongodb+srv://cluster0.mongodb.net/", "")

    def test_local_host_real_db_name_ok(self):
        # Local host allowed even without a test-named DB (dev's own machine).
        assert_safe_test_db("mongodb://localhost:27017/auto-author", "auto-author")

    def test_default_test_uri_ok(self):
        assert_safe_test_db(
            "mongodb://localhost:27017/auto-author-test", "auto-author-test"
        )

    def test_remote_host_with_test_name_ok(self):
        # Shared CI test cluster: remote but explicitly test-named.
        assert_safe_test_db("mongodb+srv://cluster0.mongodb.net/ci-test-db", "ci-test-db")

    def test_test_name_case_insensitive(self):
        assert_safe_test_db("mongodb+srv://cluster0.mongodb.net/MyTESTdb", "MyTESTdb")

    def test_loopback_ipv4_ok(self):
        assert_safe_test_db("mongodb://127.0.0.1:27017/auto-author", "auto-author")

    def test_bracketed_ipv6_loopback_ok(self):
        assert_safe_test_db("mongodb://[::1]:27017/auto-author", "auto-author")


class TestHostsAllLocal:
    def test_srv_is_never_local(self):
        assert _hosts_all_local("mongodb+srv://localhost/db") is False

    def test_credentials_stripped(self):
        assert _hosts_all_local("mongodb://user:pw@localhost:27017/db") is True

    def test_replica_set_all_local(self):
        assert _hosts_all_local("mongodb://localhost:27017,127.0.0.1:27018/db") is True

    def test_replica_set_one_remote_fails(self):
        assert _hosts_all_local("mongodb://localhost:27017,remote.host:27018/db") is False
