# Plan 004: Local cover-image deletion cannot escape the uploads directory

> **Executor instructions**: Follow step by step. Run every verification
> command and confirm the expected result before moving on. STOP and report on
> any STOP condition. Update `plans/README.md` when done unless a reviewer
> maintains the index.
>
> **Drift check (run first)**: `git diff --stat e6980f3..HEAD -- backend/app/services/file_upload_service.py`
> Compare the "Current state" excerpt to live code; mismatch → STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `e6980f3`, 2026-06-21
- **Issue**: https://github.com/frankbria/auto-author/issues/88

## Why this matters

`delete_cover_image` builds a filesystem path by string-replacing a URL prefix
and joining the remainder to the uploads directory, with no containment check.
If the stored `cover_image_url` ever contains `../` sequences, the resulting
`unlink()` could delete files outside the intended directory. This path runs
only in **local-storage mode** (when neither Cloudinary nor S3 is configured),
so it is most relevant to local/self-hosted deployments — but it is a classic
path-traversal sink and the fix is small and self-contained. Add a containment
check that rejects any resolved path outside `COVER_IMAGES_DIR`.

## Current state

`backend/app/services/file_upload_service.py:186-211`:
```python
186   async def delete_cover_image(self, image_url: str, thumbnail_url: Optional[str] = None):
187       """Delete a cover image and its thumbnail."""
188       try:
189           if self.cloud_storage:
190               # Delete from cloud storage
191               if image_url:
192                   await self.cloud_storage.delete_image(image_url)
193               if thumbnail_url:
194                   await self.cloud_storage.delete_image(thumbnail_url)
195           else:
196               # Delete from local storage
197               if image_url and image_url.startswith("/uploads/cover_images/"):
198                   filename = image_url.replace("/uploads/cover_images/", "")
199                   image_path = COVER_IMAGES_DIR / filename
200                   if image_path.exists():
201                       image_path.unlink()
202
203               if thumbnail_url and thumbnail_url.startswith("/uploads/cover_images/"):
204                   thumb_filename = thumbnail_url.replace("/uploads/cover_images/", "")
205                   thumb_path = COVER_IMAGES_DIR / thumb_filename
206                   if thumb_path.exists():
207                       thumb_path.unlink()
208
209       except Exception as e:
210           # Log error but don't fail the operation
211           logger.error(f"Error deleting image files: {e}")
```
`COVER_IMAGES_DIR` is a `pathlib.Path` defined near the top of the same file
(it is the local cover-images directory). `image_url.replace(...)` strips only
the prefix; a value like `/uploads/cover_images/../../etc/x` leaves
`../../etc/x`, and `COVER_IMAGES_DIR / "../../etc/x"` resolves outside the
directory.

**Convention**: the file already uses `pathlib.Path` and a module `logger`.
Match that style.

## Commands you will need

| Purpose       | Command                                                        | Expected |
|---------------|---------------------------------------------------------------|----------|
| Backend deps  | `cd backend && uv sync`                                        | exit 0   |
| Lint          | `cd backend && uv run ruff check app/`                         | exit 0   |
| Targeted test | `cd backend && uv run pytest tests/test_services/test_file_upload_path_safety.py` | passes |

## Scope

**In scope**:
- `backend/app/services/file_upload_service.py` (the `delete_cover_image`
  method; you may add one small private helper in the same class/module)
- `backend/tests/test_services/test_file_upload_path_safety.py` (create)

**Out of scope**:
- The cloud-storage branch (lines 189–194) — delegated to the provider SDK.
- The upload/save methods — not part of this finding.
- Changing the public signature or return type of `delete_cover_image`.

## Git workflow

- Branch: `advisor/004-path-traversal-hardening`
- Conventional commits, e.g. `fix(security): prevent path traversal in local cover-image deletion`.
- Do NOT push or open a PR unless instructed.

## Steps

### Step 1: Add a safe-resolve helper

Add a module-level (or static) helper that maps a stored URL to a path and
guarantees containment. Target shape:
```python
def _resolve_local_cover_path(image_url: str) -> Optional[Path]:
    """Resolve a /uploads/cover_images/<name> URL to a path INSIDE
    COVER_IMAGES_DIR, or return None if it would escape the directory."""
    prefix = "/uploads/cover_images/"
    if not image_url or not image_url.startswith(prefix):
        return None
    filename = image_url[len(prefix):]
    base = COVER_IMAGES_DIR.resolve()
    candidate = (base / filename).resolve()
    # Containment check (Python 3.9+: is_relative_to)
    if not candidate.is_relative_to(base):
        return None
    return candidate
```
Place it near `COVER_IMAGES_DIR` / the class. (Project requires Python ≥3.13,
so `Path.is_relative_to` is available.)

### Step 2: Use the helper in delete_cover_image

Replace the two local-storage blocks (lines 197–207) so each deletes only via
the safe resolver, and logs a warning if a URL is rejected:
```python
        else:
            for url in (image_url, thumbnail_url):
                if not url:
                    continue
                path = _resolve_local_cover_path(url)
                if path is None:
                    logger.warning("Refusing to delete cover image outside uploads dir")
                    continue
                if path.exists():
                    path.unlink()
```
Keep the surrounding `try/except` (lines 188, 209–211) intact.

**Verify**: `grep -n "replace(\"/uploads/cover_images/\"" backend/app/services/file_upload_service.py` → no matches (the unsafe `.replace`-then-join is gone).

### Step 3: Lint

**Verify**: `cd backend && uv run ruff check app/` → exit 0.

## Test plan

Create `backend/tests/test_services/test_file_upload_path_safety.py` (model
imports/style after an existing `backend/tests/test_services/` test). Cover:
- **Happy path**: a normal URL `"/uploads/cover_images/abc.png"` resolves to a
  path inside `COVER_IMAGES_DIR` (assert `_resolve_local_cover_path` returns a
  path that `.is_relative_to(COVER_IMAGES_DIR.resolve())`).
- **Traversal rejected**: `"/uploads/cover_images/../../etc/passwd"` →
  `_resolve_local_cover_path` returns `None`.
- **Wrong prefix rejected**: `"/etc/passwd"` → returns `None`.
- **Deletion containment**: with `self.cloud_storage` falsy, call
  `delete_cover_image` with a traversal URL and assert no file outside a temp
  uploads dir is removed (use `tmp_path`/monkeypatch on `COVER_IMAGES_DIR` if
  feasible; otherwise assert the warning is logged and no unlink occurs).

**Verify**: `cd backend && uv run pytest tests/test_services/test_file_upload_path_safety.py` → all pass.

## Done criteria

ALL must hold:

- [ ] `_resolve_local_cover_path` (or equivalent) exists with a containment check
- [ ] `grep -n 'replace("/uploads/cover_images/"' backend/app/services/file_upload_service.py` → no matches
- [ ] New test file exists; traversal and wrong-prefix cases assert rejection; happy path passes
- [ ] `cd backend && uv run ruff check app/` exits 0
- [ ] `cd backend && uv run pytest tests/test_services/` → no NEW failures
- [ ] No files outside scope modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report if:
- `COVER_IMAGES_DIR` is not defined in this module as assumed (find its real
  definition and report).
- The excerpt at lines 186–211 differs materially (drift).
- The upload-save method stores URLs in a format the prefix check doesn't match
  (then the helper's prefix must be reconciled — report before guessing).

## Maintenance notes

- If cloud storage becomes the only supported backend, this local path could be
  removed entirely (and `delete_cover_image` simplified).
- Reviewer should check whether `cover_image_url` is ever set from
  client-supplied input anywhere (it shouldn't be — it's server-generated on
  upload); if it can be, this fix becomes higher severity.
