# Issue #846: deploy docs describe the container deploy

*2026-10-14T15:27:00Z by Showboat 0.6.1*
<!-- showboat-id: 8180a76f-1908-4806-8f7e-ce21cac89198 -->

The operator docs said no workflow writes the staging box's .env and pointed at a PM2 rollback workflow that was deleted in #656. This shows the stale phrases on main, their absence on the branch, and the workflow that does write the file.

```bash
git grep -c -F -e 'No workflow writes' -e 'yml.disabled' main -- ':!docs/CHANGELOG.md' ':!archive' ':!docs/demos' | sed 's/^main://'
```

```output
.github/DEPLOYMENT.md:4
.github/workflows/deploy-staging-containers.yml:1
CLAUDE.md:2
docs/CI_CD_RECOVERY_PLAN.md:1
docs/PM2-DEPLOYMENT-FIXES.md:2
docs/STAGING-DEPLOYMENT.md:3
```

```bash
git grep -c -F -e 'No workflow writes' -e 'yml.disabled' -- ':!docs/CHANGELOG.md' ':!archive' ':!docs/demos' ':!scripts/test_deploy_docs_current.py'; echo "matches on branch: $(git grep -F -e 'No workflow writes' -e 'yml.disabled' -- ':!docs/CHANGELOG.md' ':!archive' ':!docs/demos' ':!scripts/test_deploy_docs_current.py' | wc -l)"
```

```output
matches on branch: 0
```

The workflow the old docs denied exists, and writes exactly one key:

```bash
grep -n 'MONGODB_URI=' .github/workflows/sync-staging-env.yml | head -3; grep -n 'sync-staging-env' CLAUDE.md .github/DEPLOYMENT.md docs/STAGING-DEPLOYMENT.md DEPLOYMENT.md | cut -c1-120
```

```output
85:          # MONGODB_URI= to the box and take staging down on the next recreate.
153:              grep -v "^MONGODB_URI=" .env > "$tmp" || true
154:              printf "MONGODB_URI=%s\n" "$VALUE" >> "$tmp"
CLAUDE.md:95:- **Application secrets live in `/opt/auto-author/.env` on the box, not in GitHub secrets.** The one workfl
.github/DEPLOYMENT.md:19:> **The one exception is `MONGODB_URI`.** `sync-staging-env.yml` (manual
.github/DEPLOYMENT.md:43:| `sync-staging-env.yml` | the same server-access secrets, plus `MONGODB_URI` (staging environm
docs/STAGING-DEPLOYMENT.md:69:**One workflow writes one key of it:** `sync-staging-env.yml` (manual dispatch,
DEPLOYMENT.md:191:`sync-staging-env.yml` writes to it, and only the `MONGODB_URI` key; see
```

```bash
git cat-file -e main:ecosystem.config.template.js && echo 'main: PM2 template present'; test -e ecosystem.config.template.js || echo 'branch: PM2 template deleted'
```

```output
main: PM2 template present
branch: PM2 template deleted
```

The guard keeps the stale phrases out (both tests failed on main's content before the fix; four mutations, one per doc plus the template, were each caught):

```bash
uvx --with pytest pytest scripts/test_deploy_docs_current.py -q 2>&1 | tail -1
```

```output
2 passed in 0.02s
```
