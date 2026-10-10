"""Storage delete helpers only delete the caller's own objects (#797).

The stored URL is not proof of ownership: it used to be client-writable, and old
documents may still carry a value a client chose. Every helper is handed the
owner's prefix and must refuse anything outside it.

The SDK clients are stand-ins (there is no local S3 or Cloudinary); the URL
parsing and the refusal are the real code. Local storage uses real files.
"""

from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

import app.services.file_upload_service as fus
from app.services.cloud_storage_service import (
    CloudinaryStorageService,
    S3StorageService,
)

pytestmark = pytest.mark.asyncio

BOOK_A = "64b000000000000000000001"
BOOK_B = "64b000000000000000000002"
HEX = "0123456789abcdef0123456789abcdef"
S3_HOST = "https://bkt.s3.us-east-1.amazonaws.com"
CLD = "https://res.cloudinary.com/demo/image/upload/v1712345678"


@pytest.fixture
def s3():
    service = S3StorageService.__new__(S3StorageService)
    service.bucket_name = "bkt"
    service.region = "us-east-1"
    service.ClientError = ClientError
    service.s3_client = Mock()
    return service


@pytest.fixture
def cloudinary():
    service = CloudinaryStorageService.__new__(CloudinaryStorageService)
    service.cloudinary_uploader = Mock()
    service.cloudinary_uploader.destroy.return_value = {"result": "ok"}
    return service


# --- S3 ----------------------------------------------------------------------


async def test_s3_deletes_a_key_under_the_owners_prefix(s3):
    url = f"{S3_HOST}/cover_images/{BOOK_A}/{HEX}.png"

    assert await s3.delete_image(url, f"cover_images/{BOOK_A}/") is True

    s3.s3_client.delete_object.assert_called_once_with(
        Bucket="bkt", Key=f"cover_images/{BOOK_A}/{HEX}.png"
    )


@pytest.mark.parametrize(
    "url",
    [
        # another book's cover and thumbnail
        f"{S3_HOST}/cover_images/{BOOK_B}/{HEX}.png",
        f"{S3_HOST}/cover_images/{BOOK_B}/thumbnails/{HEX}.png",
        # another kind of object entirely
        f"{S3_HOST}/profile_pictures/someone/{HEX}.png",
        # a prefix that only looks like the owner's
        f"{S3_HOST}/cover_images/{BOOK_A}0/{HEX}.png",
        f"{S3_HOST}/cover_images/{BOOK_A}",
        # the owner's prefix in the query or fragment, not in the key
        f"{S3_HOST}/cover_images/{BOOK_B}/{HEX}.png?x=/cover_images/{BOOK_A}/",
        f"{S3_HOST}/cover_images/{BOOK_B}/{HEX}.png#cover_images/{BOOK_A}/",
        # traversal out of the owner's prefix
        f"{S3_HOST}/cover_images/{BOOK_A}/../{BOOK_B}/{HEX}.png",
        # the bucket host as a substring of another host, or in the path
        f"https://bkt.s3.us-east-1.amazonaws.com.evil.test/cover_images/{BOOK_A}/x.png",
        f"https://evil.test/bkt.s3.us-east-1.amazonaws.com/cover_images/{BOOK_A}/x.png",
        f"https://evil.test/?u=bkt.s3.us-east-1.amazonaws.com/cover_images/{BOOK_A}/x.png",
        # the bucket host as userinfo: the real host is evil.test
        f"https://bkt.s3.us-east-1.amazonaws.com@evil.test/cover_images/{BOOK_A}/x.png",
        f"https://bkt.s3.us-east-1.amazonaws.com\\@evil.test/cover_images/{BOOK_A}/x.png",
        # urlparse raises on this one; a stored value must never raise out of a delete
        "http://[bad",
        "not a url",
        "",
    ],
)
async def test_s3_refuses_a_key_outside_the_owners_prefix(s3, url):
    assert await s3.delete_image(url, f"cover_images/{BOOK_A}/") is False

    s3.s3_client.delete_object.assert_not_called()


async def test_s3_refuses_everything_for_an_empty_prefix(s3):
    url = f"{S3_HOST}/cover_images/{BOOK_A}/{HEX}.png"

    assert await s3.delete_image(url, "") is False

    s3.s3_client.delete_object.assert_not_called()


async def test_s3_deletes_what_its_own_upload_wrote(s3):
    """The prefix the service passes must match the key upload_image builds,
    or every real delete would be refused without a test noticing."""
    for folder in (f"cover_images/{BOOK_A}", f"cover_images/{BOOK_A}/thumbnails"):
        s3.s3_client.reset_mock()
        url = await s3.upload_image(b"x", "c.png", "image/png", folder=folder)

        assert await s3.delete_image(url, f"cover_images/{BOOK_A}/") is True

        written = s3.s3_client.put_object.call_args.kwargs["Key"]
        s3.s3_client.delete_object.assert_called_once_with(Bucket="bkt", Key=written)


# --- Cloudinary --------------------------------------------------------------


async def test_cloudinary_destroys_a_public_id_under_the_owners_prefix(cloudinary):
    url = f"{CLD}/profile_pictures/user-a/{HEX}.png"

    assert await cloudinary.delete_image(url, "profile_pictures/user-a/") is True

    cloudinary.cloudinary_uploader.destroy.assert_called_once_with(
        f"profile_pictures/user-a/{HEX}"
    )


@pytest.mark.parametrize(
    "url",
    [
        f"{CLD}/profile_pictures/user-b/{HEX}.png",
        f"{CLD}/cover_images/{BOOK_A}/{HEX}.png",
        f"{CLD}/profile_pictures/user-a-2/{HEX}.png",
        f"{CLD}/profile_pictures/user-a/../user-b/{HEX}.png",
        # the right path on a host that is not Cloudinary's
        f"https://res.cloudinary.com.evil.test/demo/image/upload/v1/profile_pictures/user-a/{HEX}.png",
        f"https://evil.test/cloudinary.com/image/upload/v1/profile_pictures/user-a/{HEX}.png",
        f"https://res.cloudinary.com@evil.test/demo/image/upload/v1/profile_pictures/user-a/{HEX}.png",
        "http://[bad",
        "",
    ],
)
async def test_cloudinary_refuses_a_public_id_outside_the_owners_prefix(
    cloudinary, url
):
    assert await cloudinary.delete_image(url, "profile_pictures/user-a/") is False

    cloudinary.cloudinary_uploader.destroy.assert_not_called()


# --- local files -------------------------------------------------------------


@pytest.fixture
def local(tmp_path, monkeypatch):
    covers = tmp_path / "cover_images"
    avatars = tmp_path / "profile_pictures"
    covers.mkdir()
    avatars.mkdir()
    monkeypatch.setattr(fus, "COVER_IMAGES_DIR", covers)
    monkeypatch.setattr(fus, "PROFILE_PICTURES_DIR", avatars)
    monkeypatch.setattr(fus, "get_cloud_storage_service", lambda: None)
    return covers, avatars


def _file(directory, name):
    path = directory / name
    path.write_bytes(b"x")
    return path


async def test_local_cover_delete_removes_only_the_books_own_files(local):
    covers, _ = local
    mine = _file(covers, f"{BOOK_A}_{HEX}.png")
    my_thumb = _file(covers, f"{BOOK_A}_{HEX}_thumb.png")
    theirs = _file(covers, f"{BOOK_B}_{HEX}.png")

    service = fus.FileUploadService()
    await service.delete_cover_image(
        BOOK_A,
        f"/uploads/cover_images/{theirs.name}",
        f"/uploads/cover_images/{my_thumb.name}",
    )
    assert theirs.exists()
    assert not my_thumb.exists()

    await service.delete_cover_image(BOOK_A, f"/uploads/cover_images/{mine.name}")
    assert not mine.exists()


@pytest.mark.parametrize(
    "name",
    [
        f"{BOOK_B}_{HEX}.png",
        # the owner's id as a prefix of a longer id
        f"{BOOK_A}0_{HEX}.png",
        f"{BOOK_A}_not-a-server-name.png",
        f"x{BOOK_A}_{HEX}.png",
    ],
)
async def test_local_cover_delete_refuses_names_the_server_did_not_write(local, name):
    covers, _ = local
    target = _file(covers, name)

    await fus.FileUploadService().delete_cover_image(
        BOOK_A, f"/uploads/cover_images/{name}"
    )

    assert target.exists()


async def test_local_avatar_delete_removes_only_the_users_own_file(local):
    _, avatars = local
    mine = _file(avatars, f"user-a_{HEX}.png")
    theirs = _file(avatars, f"user-b_{HEX}.png")
    # "user-a" is a prefix of this other user's id
    lookalike = _file(avatars, f"user-a_b_{HEX}.png")

    service = fus.FileUploadService()
    for target in (theirs, lookalike, mine):
        await service.delete_profile_picture(
            "user-a", f"/uploads/profile_pictures/{target.name}"
        )

    assert theirs.exists()
    assert lookalike.exists()
    assert not mine.exists()


async def test_local_delete_refuses_everything_for_an_empty_owner(local):
    covers, avatars = local
    cover = _file(covers, f"_{HEX}.png")
    avatar = _file(avatars, f"_{HEX}.png")

    service = fus.FileUploadService()
    await service.delete_cover_image("", f"/uploads/cover_images/{cover.name}")
    await service.delete_profile_picture("", f"/uploads/profile_pictures/{avatar.name}")

    assert cover.exists()
    assert avatar.exists()


# --- the service hands the provider the owner's prefix -----------------------


class _RecordingCloud:
    def __init__(self):
        self.calls = []

    async def delete_image(self, url: str, key_prefix: str) -> bool:
        self.calls.append((url, key_prefix))
        return True


async def test_service_passes_the_owner_prefix_to_the_provider(monkeypatch):
    cloud = _RecordingCloud()
    monkeypatch.setattr(fus, "get_cloud_storage_service", lambda: cloud)
    service = fus.FileUploadService()

    await service.delete_cover_image(BOOK_A, "https://cdn/c.png", "https://cdn/t.png")
    await service.delete_profile_picture("user-a", "https://cdn/a.png")

    assert cloud.calls == [
        ("https://cdn/c.png", f"cover_images/{BOOK_A}/"),
        ("https://cdn/t.png", f"cover_images/{BOOK_A}/"),
        ("https://cdn/a.png", "profile_pictures/user-a/"),
    ]
