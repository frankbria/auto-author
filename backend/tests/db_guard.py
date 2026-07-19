"""Guard the destructive test-DB teardown against a non-test / remote database.

conftest drops its database (``drop_database`` / ``collection.drop()``) in fixture
setup/teardown, with the target derived purely from ``TEST_MONGO_URI``. The project's
real Mongo is Atlas, and this repo has a history of stray env vars — so an accidental
Atlas URI would silently wipe real users/books/audit_logs.

conftest calls :func:`assert_safe_test_db` at import time, before any fixture can run,
so a misconfigured URI aborts collection instead of destroying data (#211).
"""

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}


def _hosts_all_local(uri: str) -> bool:
    """True only when every host in the URI is loopback.

    ``mongodb+srv://`` is a DNS-seedlist scheme (Atlas / remote by definition), so it
    is never treated as local. IPv6 hosts must be bracketed (``[::1]``), per the Mongo
    connection-string spec, so a bare ``::1`` is not expected here.
    """
    if uri.startswith("mongodb+srv://"):
        return False
    rest = uri.split("://", 1)[-1]        # drop scheme
    rest = rest.rsplit("@", 1)[-1]        # drop user:pass@
    hostpart = rest.split("/", 1)[0].split("?", 1)[0]  # keep only host:port list
    hosts = [h.strip() for h in hostpart.split(",") if h.strip()]
    if not hosts:
        return False
    for h in hosts:
        if h.startswith("["):             # bracketed IPv6, e.g. [::1]:27017
            host = h.split("]", 1)[0] + "]"
        else:
            host = h.rsplit(":", 1)[0] if ":" in h else h
        host = host.lower()
        if host not in _LOCAL_HOSTS and not host.startswith("127."):
            return False
    return True


def assert_safe_test_db(uri: str, db_name: str) -> None:
    """Raise unless it's safe to drop this database in test teardown.

    Safe when the DB name contains ``test`` (case-insensitive) OR every host is
    loopback. The dangerous case the guard blocks — a remote Atlas URI with a
    real, non-test database name — satisfies neither and raises.
    """
    name_is_test = bool(db_name) and "test" in db_name.lower()
    if name_is_test or _hosts_all_local(uri):
        return
    scheme = uri.split("://", 1)[0] if "://" in uri else uri
    raise RuntimeError(
        f"Refusing to run destructive test teardown against database {db_name!r} "
        f"at a non-local host (URI scheme {scheme!r}). conftest DROPS this database. "
        f"Point TEST_MONGO_URI at a local Mongo or a database whose name contains "
        f"'test'. (#211)"
    )
