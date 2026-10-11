---
description: Staging is the only environment
globs: [".github/workflows/**", "docker-compose*.yml", "frontend/Dockerfile", "backend/Dockerfile", "docs/STAGING-DEPLOYMENT.md"]
prompt: ["production", "deploy"]
priority: 80
---
There is no production host and no GitHub `production` environment. The owner is not deploying to
production yet, and said so when PR #899 held `main` behind one (2026-10-10).

- Build, test and deploy for staging only. Ship a per-environment mechanism with the environments that
  exist. Do not add a production matrix entry, job or required variable for completeness.
- Nothing on `main` may depend on a production environment, secret or owner-supplied production value.
  A main build that fails closed on one is a defect in the change that added it.
- Work that is only about production (#782, PR #911) stays a draft PR with a note on its issue. It must
  not gate anything else.
- Before reporting "blocked on the owner", check whether the change itself created the blocker. If it
  did, remove the blocker instead of reporting it.
- A staging deploy is a `Deploy Staging (Containers)` dispatch with the backend's `sha-<short>` tag from
  a build made after #779; the frontend image is `<tag>-staging`. Check `/api/v1/health` before and
  after, and wait for the post-deploy E2E run before calling it deployed.
