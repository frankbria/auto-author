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

Review A's run and the newer push that cancelled it:

```bash
gh run view 36947804343 --json headSha,conclusion,createdAt,updatedAt,jobs -q "\"run 36947804343 on \(.headSha[:7]): \(.conclusion), \(.createdAt[11:19])-\(.updatedAt[11:19])\", ([.jobs[].steps[]|select(.name|test(\"GLM bug-hunting review|Report an incomplete\"))|\"  step \(.name): \(.conclusion)\"]|.[])"; gh run view 36947929608 --json headSha,createdAt -q "\"superseded by run 36947929608 on \(.headSha[:7]), created \(.createdAt[11:19])\""
```

```output
run 36947804343 on 5f4341b: cancelled, 00:48:08-00:51:01
  step GLM bug-hunting review: cancelled
  step Report an incomplete review: success
  step Post GLM bug-hunting review: success
superseded by run 36947929608 on 87d3302, created 00:49:39
```

The notice A posted on the PR. At the old pin, this same event read "the step timeout, or a hung API call":

```bash
gh api repos/frankbria/auto-author/issues/747/comments -q ".[]|select(.user.login==\"github-actions[bot]\" and (.body|contains(\"36947804343\")))|.body" | grep -E "^### |^Reason:"
```

```output
### ⚠️ GLM review did not complete
Reason: the run was cancelled before the agent finished — usually a newer push superseding it, since this workflow cancels in-progress runs for the same pull request. Nothing is wrong with the review itself: the newest commit is reviewed by its own run, which posts its verdict as a separate comment. This notice is not replaced by that run and can be disregarded once it appears.
### GLM precision review — in progress
```

## Criterion: a review on the new pin still completes

Review B ran on the superseding commit, under the same new pin:

```bash
gh run view 36947929608 --json conclusion,createdAt,updatedAt -q "\"run 36947929608: \(.conclusion), \(.createdAt[11:19])-\(.updatedAt[11:19])\""; gh api repos/frankbria/auto-author/issues/747/comments -q ".[]|select(.user.login==\"github-actions[bot]\" and (.body|contains(\"36947929608\")))|.body" | grep -E "GLM review: no defects found|Claude finished"
```

```output
run 36947929608: success, 00:49:39-00:58:10
**Claude finished @frankbria's task in 6m 32s** —— [View job](https://github.com/frankbria/auto-author/actions/runs/36947929608)
✅ GLM review: no defects found.
```

## Record: what September's notices actually were

Every `glm-review.yml` run created in September. A cancelled run counts as superseded when another run on the same branch started within 180s before it ended. A failure counts as a step timeout when it ran 35 minutes:

```bash
gh run list --workflow glm-review.yml --limit 400 --created 2026-09-01..2026-09-30 --json databaseId,conclusion,createdAt,updatedAt,headBranch | jq -r ". as \$all | ([.[]|select(.conclusion==\"cancelled\")]|map(. as \$c|(\$c.updatedAt|fromdate) as \$e|[\$all[]|select(.headBranch==\$c.headBranch and .databaseId!=\$c.databaseId and ((.createdAt|fromdate)<=\$e+5) and ((.createdAt|fromdate)>=\$e-180))]|length>0)) as \$s | \"cancelled: \(\$s|length), superseded: \(\$s|map(select(.))|length)\", \"35m step timeouts: \([.[]|select(.conclusion==\"failure\" and (((.updatedAt|fromdate)-(.createdAt|fromdate))>=2100))|.databaseId]|join(\", \"))\""
```

```output
cancelled: 36, superseded: 33
35m step timeouts: 34439383436, 34425433212, 34403229853, 34299360608
```

## Evidence summary

| Criterion | Action | Outcome evidence | Status |
|---|---|---|---|
| Pin is `9c7577a` and the caller satisfies its interface | read the pin; parse the callee at that SHA | one required secret (`ZHIPU_API_KEY`), no required inputs, `contents: read` + `pull-requests: write`, all of which this caller grants; 107 guards pass | VERIFIED |
| A superseded review says it was superseded | push a commit while review A's agent is mid-review | A `cancelled`; its notice reads "cancelled before the agent finished, usually a newer push superseding it" | VERIFIED |
| A review on the new pin still completes | review B on the superseding commit | `success` in 6m32s; posted "✅ GLM review: no defects found." | VERIFIED |
