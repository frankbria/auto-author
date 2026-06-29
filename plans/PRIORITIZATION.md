# Combined Backlog Prioritization (PX.Y)

Single ordered view of the **whole** open backlog — the 10 advisor plans plus
the 24 pre-existing GitHub issues — as of 2026-06-21.

- **PX** = importance tier: P0 (foundational / security / blockers) → P3 (low / debt).
- **.Y** = order within the tier by dependency and sequence (lower runs first).
- Every issue carries a matching `[PX.Y]` title prefix and a `PX.Y` label.
- The old `critical/high/medium/low` priority labels were removed in favor of this scheme.

## P0 — Foundational, security & blockers

| PX.Y | Issue | Title | Source |
|------|-------|-------|--------|
| P0.1 | #85 | Establish a single verification command + discoverable backend tests | advisor 001 |
| P0.2 | #86 | Stop logging auth tokens and PII to logs/stdout | advisor 002 |
| P0.3 | #87 | Stop leaking internal exception detail in API error responses | advisor 003 |
| P0.4 | #88 | Prevent path traversal in local cover-image deletion | advisor 004 |
| P0.5 | #45 | Complete API endpoints — remove mock data | existing |
| P0.6 | #44 | Fix broken UI elements | existing |
| P0.7 | #83 | Implement comprehensive E2E test suite | existing |

## P1 — High-priority core functionality

| PX.Y | Issue | Title | Source |
|------|-------|-------|--------|
| P1.1 | #48 | Fix TOC generation flow | existing |
| P1.2 | #54 | Fix question response integration | existing |
| P1.3 | #92 | Make cascade book-delete atomic | advisor 008 (dep: #85) |
| P1.4 | #49 | Export error recovery | existing |
| P1.5 | #46 | Comprehensive error feedback UI | existing |
| P1.6 | #55 | AI draft generation from Q&A | existing |
| P1.7 | #89 | Correct README to better-auth | advisor 005 |
| P1.8 | #93 | Tests for transcription + cover-upload | advisor 009 (dep: #85) |
| P1.9 | #68 | Flaky test fix + frontend coverage to 85% | existing |
| P1.10 | #81 | Fix duplicate button selectors (E2E) | existing |
| P1.11 | #65 | Migrate UI to shadcn nova | existing |

## P2 — Medium priority

| PX.Y | Issue | Title | Source |
|------|-------|-------|--------|
| P2.1 | #91 | Split runtime vs test/load dependencies | advisor 007 (dep: #85) |
| P2.2 | #59 | Professional export templates (PDF/DOCX) | existing |
| P2.3 | #60 | EPUB export | existing |
| P2.4 | #58 | Writing style transformation | existing |
| P2.5 | #57 | Content enhancement features | existing |
| P2.6 | #56 | Voice input AI analysis | existing |
| P2.7 | #53 | Progress tracking for chapter questions | existing |
| P2.8 | #52 | Loading indicators / progress | existing |
| P2.9 | #51 | Mobile responsiveness | existing |
| P2.10 | #50 | Accessibility (WCAG 2.1 AA) | existing |

## P3 — Low priority / tech debt / nice-to-have

| PX.Y | Issue | Title | Source |
|------|-------|-------|--------|
| P3.1 | #94 | Decompose books.py (map + first extraction) | advisor 010 (dep: #85) |
| P3.2 | #90 | Repo hygiene (stale dump, unused @dnd-kit) | advisor 006 |
| P3.3 | #61 | Markdown export | existing |
| P3.4 | #62 | Question regeneration quality | existing |
| P3.5 | #63 | User profile editing | existing |
| P3.6 | #64 | Account settings | existing |

## Key dependencies

- **#85 (P0.1) is the keystone** — #92, #93, #91, #94 (advisor data/test/dep/refactor
  plans) all assume a trustworthy test gate. Do #85 first.
- **#88 (P0.4) ↔ #93 (P1.8)** — the cover-upload tests should include a path-traversal
  rejection case; sequence whichever lands first to cover the other.
- **#83 (P0.7) ↔ #81 (P1.10) ↔ #68 (P1.9)** — all test-infrastructure; #85 lays their
  foundation.
- Export cluster (#59/#60/#61) overlaps advisor direction finding DIR-B (export depth).
