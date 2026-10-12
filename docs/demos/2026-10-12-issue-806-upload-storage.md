# Where uploads go is decided in one place, and production refuses local disk (#806)

*2026-10-12T12:55:00Z by Showboat 0.6.1*
<!-- showboat-id: dbace09e-6895-4c98-8cc2-9f0dccdff7b0 -->

The storage provider for uploaded covers and avatars was chosen three ways: settings fields nothing read, a check of the process environment that needed every value of a provider, and a check for the static mount that looked at one value of each. This demo starts the real backend from main and from this branch with different storage settings and uploads a small picture. No storage provider is contacted: every case here ends on local disk or before it. Authentication is bypassed; this is about where a file goes.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo806/env.sh; echo "main:   $(git -C $MAIN log --oneline -1 | cut -c1-7)"; echo "branch: $(git -C $WT rev-parse --abbrev-ref HEAD)"; file $D/avatar.png | sed 's|.*/||'
```

```output
main:   9c669ab
branch: feature/issue-806-upload-storage
color RGB, non-interlaced
```

Half a configuration: one of the three Cloudinary values is set. On main the upload service decides "not Cloudinary" and writes the file to local disk, while the mount decides "Cloudinary" and does not serve local files: the upload succeeds and the picture is a 404. On this branch both ask the same question, so the file that was written is served. (Main had a second way to the same 404, with nothing configured at all: the mount was skipped when the directory did not exist yet at startup, and the first upload is what creates it. The third request below starts main in a fresh directory with no provider.)

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo806/env.sh; echo '--- main'; boot $MAIN $D/work-main CLOUDINARY_CLOUD_NAME=demo 2>/dev/null; upload; echo '--- branch'; boot $WT $D/work-branch CLOUDINARY_CLOUD_NAME=demo 2>/dev/null; upload; grep -o 'No complete cloud storage configuration[^"]*' $D/backend.log | head -1; echo '--- main, nothing configured, fresh directory'; rm -rf $D/work-main/uploads; boot $MAIN $D/work-main 2>/dev/null; upload; echo '--- branch, nothing configured, fresh directory'; rm -rf $D/work-branch/uploads; boot $WT $D/work-branch 2>/dev/null; upload; stop 2>/dev/null
```

```output
--- main
the backend started
upload: HTTP 200 -> /uploads/profile_pictures/test-auth-id_<id>.png
fetching it back: HTTP 404 application/json
--- branch
the backend started
upload: HTTP 200 -> /uploads/profile_pictures/test-auth-id_<id>.png
fetching it back: HTTP 200 image/png
No complete cloud storage configuration (not set: CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET), using local storage
--- main, nothing configured, fresh directory
the backend started
upload: HTTP 200 -> /uploads/profile_pictures/test-auth-id_<id>.png
fetching it back: HTTP 404 application/json
--- branch, nothing configured, fresh directory
the backend started
upload: HTTP 200 -> /uploads/profile_pictures/test-auth-id_<id>.png
fetching it back: HTTP 200 image/png
```

The container. In the image the working directory belongs to root, so the uploads directory cannot be created; here that is a read-only working directory. Both versions start, because the upload service is loaded on first use. The first upload fails on both. Main logs a bare PermissionError. This branch logs what is wrong and what to set.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo806/env.sh; ls -ld $D/app-root | cut -c1-10; echo '--- main'; boot $MAIN $D/app-root 2>/dev/null; upload; grep -o 'PermissionError.*' $D/backend.log | tail -1; echo '--- branch'; boot $WT $D/app-root ENVIRONMENT=staging 2>/dev/null; upload; grep -o 'Uploads are not available.*' $D/backend.log | tail -1 | sed "s|$D|<working directory>|" | fold -s -w 150; stop 2>/dev/null
```

```output
dr-xr-xr-x
--- main
the backend started
upload: HTTP 500 {"detail":"An unexpected error occurred"}
PermissionError: [Errno 13] Permission denied: 'uploads'
--- branch
the backend started
upload: HTTP 500 {"detail":"An unexpected error occurred"}
Uploads are not available: no cloud storage is configured and the local directory <working directory>/app-root/uploads cannot be created (Permission 
denied). Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET or AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET.
```

Production. With ENVIRONMENT=production and no provider, main starts and would write uploads to the disk of a container that is replaced at every deploy. This branch refuses to start and names the settings. With half a provider it also names the half that is absent. With a complete provider it starts.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo806/env.sh; P='ENVIRONMENT=production BYPASS_AUTH=false E2E_ALLOW_BYPASS='; echo '--- main, no provider'; boot $MAIN $D/work-main $P 2>/dev/null; echo '--- branch, no provider'; boot $WT $D/work-branch $P 2>/dev/null | fold -s -w 150; echo '--- branch, half of Cloudinary'; boot $WT $D/work-branch $P CLOUDINARY_CLOUD_NAME=demo 2>/dev/null | fold -s -w 150; echo '--- branch, all of Cloudinary (placeholder values)'; boot $WT $D/work-branch $P CLOUDINARY_CLOUD_NAME=demo CLOUDINARY_API_KEY=placeholder CLOUDINARY_API_SECRET=placeholder 2>/dev/null; echo '--- branch, all of S3 (placeholder values)'; boot $WT $D/work-branch $P AWS_ACCESS_KEY_ID=placeholder AWS_SECRET_ACCESS_KEY=placeholder AWS_S3_BUCKET=demo 2>/dev/null; stop 2>/dev/null
```

```output
--- main, no provider
the backend started
--- branch, no provider
the backend did not start: RuntimeError: Application startup blocked: no upload storage is configured, so uploads would go to local disk in 
production. Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET or AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET.
--- branch, half of Cloudinary
the backend did not start: RuntimeError: Application startup blocked: no upload storage is configured, so uploads would go to local disk in 
production. Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET or AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET. Not set: 
CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET.
--- branch, all of Cloudinary (placeholder values)
the backend started
--- branch, all of S3 (placeholder values)
the backend started
```

The same behaviour as tests, with one more: the test session empties the six storage settings before the app is imported, so a developer .env that names a real bucket cannot send test uploads to it.

```bash
cd /home/frankbria/projects/worktrees/issue-806-upload-storage/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo806 uv run pytest tests/test_services/test_storage_provider.py -q -p no:cacheprovider --no-cov 2>&1 | tail -1 | sed 's/ in [0-9.]*s//'
```

```output
============================== 22 passed ==============================
```
