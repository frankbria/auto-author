# Documentation Index

Project guide for coding agents: [`../CLAUDE.md`](../CLAUDE.md). Quality gates and the PR checklist: [`references/quality-standards.md`](references/quality-standards.md).

## Folders

| Folder | Contents |
|--------|----------|
| [`user-guide/`](user-guide/) | End-user guides and troubleshooting: the user manual, auth, book metadata, summary, TOC, question answering, chapter tabs, profile |
| [`api/`](api/) | API reference for books, chapter tabs, profile, questions, summary and TOC |
| [`development/`](development/) | Developer notes: error handling, export, session management, database indexes, question data model, OpenAI and cloud storage setup, UI flow, accessibility testing |
| [`testing/`](testing/) | Testing setup guide, best practices and the editing/auto-save E2E flow |
| [`references/`](references/) | On-demand deep dives: quality standards, testing infrastructure, performance monitoring, component documentation |
| [`adr/`](adr/) | Architecture decision records, one per decision, dated in the filename |
| [`plans/`](plans/) | Written plans for larger refactors (the `books.py` decomposition map) |
| [`demos/`](demos/) | Evidence from pull requests: a demo write-up and screenshots per issue |

## Top-level files

| File | Contents |
|------|----------|
| [`CHANGELOG.md`](CHANGELOG.md) | Detailed per-issue changelog; new entries go here |
| [`STAGING-DEPLOYMENT.md`](STAGING-DEPLOYMENT.md) | Staging deployment guide |
| [`DATABASE_CONNECTION_STANDARD.md`](DATABASE_CONNECTION_STANDARD.md) | How the backend connects to MongoDB |
| [`INCIDENT-2025-10-18-exposed-secrets.md`](INCIDENT-2025-10-18-exposed-secrets.md) | Postmortem for the exposed-secrets incident |

## Where new docs go

| Kind of doc | Location |
|-------------|----------|
| User guide or user-facing troubleshooting | `docs/user-guide/` |
| API reference | `docs/api/` |
| Developer notes | `docs/development/` |
| Testing | `docs/testing/` |
| A decision and its reasoning | `docs/adr/` |
| What changed, per issue | `docs/CHANGELOG.md` |
| Tasks and follow-ups | GitHub issues with a `[PX.Y]` title prefix, not markdown files |

Before writing a new file, check whether an existing doc already covers the topic and update it instead. Do not add planning or TODO markdown files.
