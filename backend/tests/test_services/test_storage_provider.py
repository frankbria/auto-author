"""Where uploads go is decided in one place, from settings (#806).

It was decided three ways. The Settings fields were declared and unused. The
service read ``os.getenv`` and needed every key of a provider. The static mount
in ``main.py`` looked at one key of each. With half a Cloudinary configuration
the service wrote files to local disk and the mount, seeing "cloud", never
served them. And with no configuration in the container, startup died on a
``PermissionError`` for ``uploads``, which is how production was kept off local
disk: by accident, with a message that names nothing an operator can fix.
"""

import os
import stat

import pytest
from fastapi import FastAPI

from app.core.config import settings
from app.services import cloud_storage_service, file_upload_service
from app.services.cloud_storage_service import (
    CloudinaryStorageService,
    S3StorageService,
    get_cloud_storage_service,
)
from app.services.file_upload_service import FileUploadService

CLOUDINARY = {"CLOUDINARY_CLOUD_NAME": "demo", "CLOUDINARY_API_KEY": "key", "CLOUDINARY_API_SECRET": "x"}
S3 = {"AWS_ACCESS_KEY_ID": "id", "AWS_SECRET_ACCESS_KEY": "x", "AWS_S3_BUCKET": "bucket"}
EVERY_FIELD = {**dict.fromkeys(CLOUDINARY, ""), **dict.fromkeys(S3, "")}


@pytest.fixture
def configure(monkeypatch):
    """Set the storage settings to exactly the given fields; everything else empty.

    The process environment is cleared of them too, so a test that passes only
    because of ``os.getenv`` cannot pass.
    """

    def apply(**fields):
        for name, value in {**EVERY_FIELD, **fields}.items():
            monkeypatch.setattr(settings, name, value)
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setattr(cloud_storage_service, "_storage_service", None)

    return apply


def test_the_test_session_itself_stores_uploads_locally():
    """conftest empties the storage settings, so no test run reaches a real
    bucket because a developer's ``.env`` names one."""
    assert settings.storage_provider == "local"


class TestOneAnswerFromSettings:
    @pytest.mark.parametrize(
        "fields, provider",
        [
            ({}, "local"),
            (CLOUDINARY, "cloudinary"),
            (S3, "s3"),
            ({**CLOUDINARY, **S3}, "cloudinary"),
            ({"CLOUDINARY_CLOUD_NAME": "demo"}, "local"),
            ({"AWS_S3_BUCKET": "bucket", "AWS_ACCESS_KEY_ID": "id"}, "local"),
        ],
        ids=["nothing set", "cloudinary", "s3", "both: cloudinary", "half of cloudinary", "s3 without its secret"],
    )
    def test_the_provider(self, configure, fields, provider):
        configure(**fields)

        assert settings.storage_provider == provider

    def test_half_a_configuration_is_named(self, configure):
        configure(CLOUDINARY_CLOUD_NAME="demo", AWS_S3_BUCKET="bucket")

        assert settings.storage_fields_missing == [
            "CLOUDINARY_API_KEY",
            "CLOUDINARY_API_SECRET",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
        ]

    @pytest.mark.parametrize(
        "fields, kind",
        [
            (CLOUDINARY, CloudinaryStorageService),
            (S3, S3StorageService),
            ({}, type(None)),
            # The original defect: with half a provider the service must agree
            # with the mount that this is local disk.
            ({"CLOUDINARY_CLOUD_NAME": "demo"}, type(None)),
            ({"AWS_S3_BUCKET": "bucket"}, type(None)),
        ],
        ids=["cloudinary", "s3", "local", "half of cloudinary", "half of s3"],
    )
    def test_the_service_follows_the_settings_not_the_process_environment(
        self, configure, monkeypatch, fields, kind
    ):
        configure(**fields)
        # The opposite answer in the environment, which the old code would have believed.
        for name in CLOUDINARY if kind is not CloudinaryStorageService else S3:
            monkeypatch.setenv(name, "from-the-environment")
        if kind is CloudinaryStorageService:
            pytest.importorskip("cloudinary")
        if kind is S3StorageService:
            pytest.importorskip("boto3")

        assert isinstance(get_cloud_storage_service(), kind)


class TestTheMountAsksTheSameQuestion:
    def _mounted(self, app: FastAPI) -> bool:
        return any(getattr(route, "path", None) == "/uploads" for route in app.routes)

    def test_half_a_cloud_configuration_still_serves_the_local_files_it_writes(
        self, configure, tmp_path, monkeypatch
    ):
        from app.main import mount_local_uploads

        configure(CLOUDINARY_CLOUD_NAME="demo")
        monkeypatch.chdir(tmp_path)
        (tmp_path / "uploads").mkdir()
        app = FastAPI()

        mount_local_uploads(app)

        assert self._mounted(app)

    def test_a_file_uploaded_after_startup_is_served(self, configure, tmp_path, monkeypatch):
        """The directory is created by the first upload, which is after startup.
        The mount used to be skipped when it did not exist yet, so on a fresh
        checkout nothing uploaded was served until the next restart."""
        from fastapi.testclient import TestClient

        from app.main import mount_local_uploads

        configure()
        monkeypatch.chdir(tmp_path)
        app = FastAPI()
        mount_local_uploads(app)

        FileUploadService()  # creates uploads/, as the first upload does
        (tmp_path / file_upload_service.PROFILE_PICTURES_DIR / "a.txt").write_text("picture")

        response = TestClient(app).get("/uploads/profile_pictures/a.txt")
        assert (response.status_code, response.text) == (200, "picture")

    def test_cloud_storage_mounts_nothing(self, configure, tmp_path, monkeypatch):
        from app.main import mount_local_uploads

        configure(**CLOUDINARY)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "uploads").mkdir()
        app = FastAPI()

        mount_local_uploads(app)

        assert not self._mounted(app)


class TestLocalDiskIsForDevelopment:
    def test_production_refuses_to_start_on_local_disk_and_says_what_to_set(
        self, configure, monkeypatch
    ):
        from app.main import validate_production_security

        configure(CLOUDINARY_CLOUD_NAME="demo")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "BYPASS_AUTH", False)

        with pytest.raises(RuntimeError) as refused:
            validate_production_security()

        message = str(refused.value)
        assert message.startswith("Application startup blocked: no upload storage is configured")
        assert "local disk in production" in message
        assert "Not set: CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET." in message

    @pytest.mark.parametrize("fields", [CLOUDINARY, S3], ids=["cloudinary", "s3"])
    def test_production_with_a_complete_provider_starts(self, configure, monkeypatch, fields):
        from app.main import validate_production_security

        configure(**fields)
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "BYPASS_AUTH", False)

        validate_production_security()

    @pytest.mark.parametrize("environment", ["development", "test", "staging"])
    def test_other_environments_start_on_local_disk(self, configure, monkeypatch, environment):
        from app.main import validate_production_security

        configure()
        monkeypatch.setenv("ENVIRONMENT", environment)

        validate_production_security()

    def test_a_directory_it_cannot_write_is_reported_as_a_storage_problem(
        self, configure, monkeypatch, tmp_path
    ):
        """What the container does without a provider: its working directory
        belongs to root. The error used to be a bare PermissionError: 'uploads'."""
        if os.geteuid() == 0:
            pytest.skip("root can write anywhere")
        configure()
        locked = tmp_path / "app"
        locked.mkdir()
        locked.chmod(stat.S_IRUSR | stat.S_IXUSR)
        monkeypatch.chdir(locked)

        try:
            with pytest.raises(RuntimeError) as refused:
                FileUploadService()
        finally:
            locked.chmod(stat.S_IRWXU)

        message = str(refused.value)
        assert message.startswith("Uploads are not available: no cloud storage is configured")
        assert str(locked / "uploads") in message and "Permission denied" in message
        assert "CLOUDINARY_CLOUD_NAME" in message and "AWS_S3_BUCKET" in message

    def test_development_writes_to_local_disk(self, configure, monkeypatch, tmp_path):
        configure()
        monkeypatch.chdir(tmp_path)

        service = FileUploadService()

        assert service.cloud_storage is None
        assert (tmp_path / file_upload_service.COVER_IMAGES_DIR).is_dir()
