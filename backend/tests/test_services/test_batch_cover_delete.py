"""Account deletion removes covers in batches, not one storage call per book (#941).

The SDK clients are stand-ins (there is no local S3 or Cloudinary); the key
parsing, the owner-prefix refusal and the chunking are the real code. Local
storage and MongoDB are real.
"""

from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError
from bson import ObjectId

import app.services.file_upload_service as fus
from app.db.base import get_collection
from app.db.book import delete_all_user_books
from app.services.cloud_storage_service import (
    CloudinaryStorageService,
    S3StorageService,
)

pytestmark = pytest.mark.asyncio

HEX = "0123456789abcdef0123456789abcdef"
S3_HOST = "https://bkt.s3.us-east-1.amazonaws.com"
CLD = "https://res.cloudinary.com/demo/image/upload/v1712345678"


def _book_ids(n):
    return [f"{i:024x}" for i in range(1, n + 1)]


@pytest.fixture
def s3():
    service = S3StorageService.__new__(S3StorageService)
    service.bucket_name = "bkt"
    service.region = "us-east-1"
    service.ClientError = ClientError
    service.s3_client = Mock()
    service.s3_client.delete_objects.return_value = {}
    return service


@pytest.fixture
def cloudinary():
    service = CloudinaryStorageService.__new__(CloudinaryStorageService)
    service.cloudinary_uploader = Mock()
    service.cloudinary_api = Mock()
    service.cloudinary_api.delete_resources.side_effect = lambda ids, **_: {
        "deleted": {i: "deleted" for i in ids}
    }
    return service


async def test_s3_deletes_in_chunks_of_1000_keys(s3):
    items = [
        (f"{S3_HOST}/cover_images/{book}/{HEX}.png", f"cover_images/{book}/")
        for book in _book_ids(2500)
    ]

    assert await s3.delete_images(items) == []

    calls = s3.s3_client.delete_objects.call_args_list
    assert [len(c.kwargs["Delete"]["Objects"]) for c in calls] == [1000, 1000, 500]
    assert calls[0].kwargs["Bucket"] == "bkt"
    assert calls[0].kwargs["Delete"]["Objects"][0] == {
        "Key": f"cover_images/{_book_ids(1)[0]}/{HEX}.png"
    }


async def test_s3_batch_refuses_foreign_keys_and_reports_errors(s3):
    mine = f"{S3_HOST}/cover_images/aa/{HEX}.png"
    failing = f"{S3_HOST}/cover_images/aa/{HEX}_thumb.png"
    foreign = f"{S3_HOST}/cover_images/bb/{HEX}.png"
    s3.s3_client.delete_objects.return_value = {
        "Errors": [{"Key": f"cover_images/aa/{HEX}_thumb.png", "Code": "AccessDenied"}]
    }

    failed = await s3.delete_images(
        [(mine, "cover_images/aa/"), (failing, "cover_images/aa/"), (foreign, "cover_images/aa/")]
    )

    assert sorted(failed) == sorted([failing, foreign])
    (call,) = s3.s3_client.delete_objects.call_args_list
    assert [o["Key"] for o in call.kwargs["Delete"]["Objects"]] == [
        f"cover_images/aa/{HEX}.png",
        f"cover_images/aa/{HEX}_thumb.png",
    ]


async def test_s3_batch_reports_a_whole_chunk_when_the_call_fails(s3):
    url = f"{S3_HOST}/cover_images/aa/{HEX}.png"
    s3.s3_client.delete_objects.side_effect = ClientError(
        {"Error": {"Code": "500", "Message": "down"}}, "DeleteObjects"
    )

    assert await s3.delete_images([(url, "cover_images/aa/")]) == [url]


async def test_cloudinary_deletes_in_chunks_of_100_public_ids(cloudinary):
    items = [
        (f"{CLD}/cover_images/{book}/{HEX}.png", f"cover_images/{book}/")
        for book in _book_ids(250)
    ]

    assert await cloudinary.delete_images(items) == []

    calls = cloudinary.cloudinary_api.delete_resources.call_args_list
    assert [len(c.args[0]) for c in calls] == [100, 100, 50]
    assert calls[0].args[0][0] == f"cover_images/{_book_ids(1)[0]}/{HEX}"


async def test_cloudinary_batch_reports_what_it_did_not_delete(cloudinary):
    mine = f"{CLD}/cover_images/aa/{HEX}.png"
    gone = f"{CLD}/cover_images/aa/{HEX}_thumb.png"
    foreign = f"{CLD}/cover_images/bb/{HEX}.png"
    cloudinary.cloudinary_api.delete_resources.side_effect = lambda ids, **_: {
        "deleted": {
            f"cover_images/aa/{HEX}": "deleted",
            f"cover_images/aa/{HEX}_thumb": "not_found",
        }
    }

    failed = await cloudinary.delete_images(
        [(mine, "cover_images/aa/"), (gone, "cover_images/aa/"), (foreign, "cover_images/aa/")]
    )

    assert sorted(failed) == sorted([gone, foreign])


# --- the service and the account cascade -------------------------------------


@pytest.fixture
def local(tmp_path, monkeypatch):
    covers = tmp_path / "cover_images"
    covers.mkdir()
    monkeypatch.setattr(fus, "COVER_IMAGES_DIR", covers)
    monkeypatch.setattr(fus, "PROFILE_PICTURES_DIR", tmp_path / "profile_pictures")
    monkeypatch.setattr(fus, "get_cloud_storage_service", lambda: None)
    return covers


async def test_local_batch_removes_only_each_books_own_files(local):
    a, b = _book_ids(2)
    for name in (f"{a}_{HEX}.png", f"{a}_{HEX}_thumb.png", f"{b}_{HEX}.png"):
        (local / name).write_bytes(b"x")

    await fus.FileUploadService().delete_cover_images(
        [
            (a, f"/uploads/cover_images/{a}_{HEX}.png"),
            (a, f"/uploads/cover_images/{a}_{HEX}_thumb.png"),
            # b's file named under a's id is refused
            (a, f"/uploads/cover_images/{b}_{HEX}.png"),
        ]
    )

    assert sorted(p.name for p in local.iterdir()) == [f"{b}_{HEX}.png"]


class _BatchCloud:
    """Records batch calls; the provider parsing is covered above."""

    def __init__(self):
        self.batches = []

    async def delete_images(self, items):
        self.batches.append(list(items))
        return [url for url, _ in items if "foreign" in url]

    async def delete_image(self, url, key_prefix):
        raise AssertionError("the account cascade must not delete one file at a time")


async def test_account_cascade_deletes_every_cover_in_one_batch(
    reinit_db, monkeypatch, caplog
):
    cloud = _BatchCloud()
    monkeypatch.setattr(fus, "get_cloud_storage_service", lambda: cloud)
    books = await get_collection("books")
    ids = []
    for i in range(3):
        result = await books.insert_one(
            {
                "title": f"B{i}",
                "owner_id": "victim",
                "cover_image_url": f"https://cdn.example.com/c{i}.jpg",
                "cover_thumbnail_url": f"https://cdn.example.com/{'foreign' if i == 2 else 't'}{i}.jpg",
            }
        )
        ids.append(str(result.inserted_id))
    await books.insert_one({"title": "no cover", "owner_id": "victim"})

    with caplog.at_level("WARNING", logger="app.services.file_upload_service"):
        assert await delete_all_user_books("victim") == 4

    (batch,) = cloud.batches
    assert sorted(batch) == sorted(
        [(f"https://cdn.example.com/c{i}.jpg", f"cover_images/{ids[i]}/") for i in range(3)]
        + [(f"https://cdn.example.com/t{i}.jpg", f"cover_images/{ids[i]}/") for i in range(2)]
        + [("https://cdn.example.com/foreign2.jpg", f"cover_images/{ids[2]}/")]
    )
    assert await books.count_documents({"_id": {"$in": [ObjectId(i) for i in ids]}}) == 0
    # A file left behind is not silent.
    assert any("foreign2.jpg" in r.getMessage() for r in caplog.records)
