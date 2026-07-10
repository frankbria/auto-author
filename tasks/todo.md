# Issue #191 [P1.11] — e2e-staging workflow runs fork PR code with live staging secrets (pwn-request)

**Plan source**: self-authored (no plan comment on the issue — only CodeRabbit boilerplate).
**Approved**: autonomously (no architectural fork — AC branch 1 (env approval) would gate the 6-hour cron too and break it; branch 3 removes the documented labeled-PR path; branch 2 (same-repo head guard) is the only sound choice).

## Premise verification (done)
- Repo is **public** → GitHub already withholds all secrets (incl. `staging` environment secrets) from `pull_request` runs on fork PRs. The headline "exfiltrate staging creds" attack is **not exploitable today** via this trigger.
- Residual real risks the fix closes: fork PR code still *executes* (npm ci lifecycle scripts + Playwright specs) against live staging; and the config is one drift step (`pull_request_target` swap, repo going private with fork-secrets enabled) from a genuine credential leak. Defense-in-depth per AC.
- `staging` environment has **no protection rules** — AC branch 1 (required reviewers) would also gate every scheduled run (protection rules apply to all runs referencing the environment) → breaks the 6-hourly cron. **Rejected.**
- AC branch 3 (workflow_dispatch-only) removes the documented, in-use labeled-PR path. **Rejected.**
- **Chosen: AC branch 2** — restrict the label-gated job to same-repo head.

## Plan
- [x] Verify premise (repo visibility, env protection, trigger semantics)
- [ ] Branch `fix/issue-191-staging-pwn-request`
- [ ] RED: with `act --list` + synthetic fork-PR-labeled event, show the *current* workflow schedules `e2e-staging` for a fork PR
- [ ] Edit `.github/workflows/e2e-staging-tests.yml`: job `if:` adds `github.event.pull_request.head.repo.full_name == github.repository` AND'd with the label check for PR events; update header + inline comments
- [ ] GREEN: same synthetic fork event → job skipped; same-repo labeled event → job still runs; schedule/dispatch unaffected
- [ ] `actionlint` clean
- [ ] opencode (GLM) pre-PR review on branch diff
- [ ] PR with Known Limitations (public-repo default already withholds fork secrets; this is defense-in-depth + fork-code-execution/abuse prevention)
- [ ] Demo (showboat): actionlint + act job-plan truth table old vs new (fork-labeled / same-repo-labeled / schedule)
- [ ] opencode post-PR review posted as PR comment; triage bot findings
- [ ] CI green; docs sync (CLAUDE.md changelog); merge
- [ ] Follow-up issue (prioritized): `glm-review.yml` same latent class (`pull_request` + `ZHIPU_API_KEY` on fork-runnable trigger)

## Notes
- No unit-test framework exists for workflow YAML; the #189 precedent (config-only, evidence-is-verification) applies. RED/GREEN is done with `act --list` event evaluation.
- `load-smoke` job untouched: already gated to `workflow_dispatch` only.
