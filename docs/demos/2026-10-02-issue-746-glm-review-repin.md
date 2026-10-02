# glm-review re-pinned: a superseded review is no longer reported as a timeout (#746)

*2026-10-02T00:47:57Z by Showboat 0.6.1*
<!-- showboat-id: 058cc5f0-f884-4312-8d49-7f65c150b788 -->

PR #747. A `pull_request` run uses the PR's own workflow file, so every review on this PR runs the **new** pin (`9c7577a`).

## Local checks: the pin, and the interface it calls

```bash
grep -n "uses: frankbria/glm-review/.github/workflows/review.yml" .github/workflows/glm-review.yml | sed "s/ *#.*//"; uvx -q --with pytest --with pyyaml pytest scripts/ -q -p no:cacheprovider 2>&1 | grep -E "passed|failed"
```

```output
97:    uses: frankbria/glm-review/.github/workflows/review.yml@9c7577a45e3a49bc44cc0f57330e3069ef97adc4
107 passed, 5 skipped in 1.85s
```

The callee's permissions and required secret at the new pin are what this caller grants (`contents: read`, `pull-requests: write`, `ZHIPU_API_KEY`):

```bash
gh api "repos/frankbria/glm-review/contents/.github/workflows/review.yml?ref=9c7577a45e3a49bc44cc0f57330e3069ef97adc4" -H "Accept: application/vnd.github.raw" | python3 -c "
import sys, yaml
w = yaml.safe_load(sys.stdin)
call = w[True][\"workflow_call\"]
print(\"secrets required:\", [k for k, v in call[\"secrets\"].items() if v.get(\"required\")])
print(\"inputs without a default:\", [k for k, v in call[\"inputs\"].items() if \"default\" not in v])
for name, job in w[\"jobs\"].items(): print(\"job\", name, \"permissions:\", job.get(\"permissions\"))
"
```

```output
secrets required: ['ZHIPU_API_KEY']
inputs without a default: []
job review permissions: {'contents': 'read', 'pull-requests': 'write'}
```

## Criterion: a review cancelled by a newer push says so

Review A ran on `5f4341b`, the first head over the 20-line size gate. While A's agent was mid-review (progress stub posted, `GLM bug-hunting review` step in progress), this section was pushed as `5f4341b`'s successor. `cancel-in-progress` should cancel A, and the new pin should report that as a supersession, not as a timeout.
