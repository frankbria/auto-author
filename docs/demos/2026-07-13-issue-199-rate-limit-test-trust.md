# Issue #199: real rate-limit test coverage — mutation differential (main vs branch)

*2026-07-13T05:49:06Z*

Issue #199 complaint: tests/conftest.py monkeypatches the rate limiter to a no-op for the whole backend suite, and the one endpoint-level rate-limit test is skipped — so deleting `Depends(get_rate_limiter(...))` from any AI-generation or export endpoint (the cost/abuse/DoS surface, 26 wired call sites) passes the ENTIRE suite green. This demo proves the complaint on a pristine main worktree, then shows the same mutation failing RED on the PR #285 branch, plus the new per-endpoint-class 429 integration tests. Setup: main is checked out at ecd6187 in a scratch worktree with its own synced venv; the branch is the repo working tree.

Step 1 — mutate MAIN: comment out the rate limiter dependency on the PDF export endpoint (a real cost-surface route: 10 exports/hour in production). The guard makes the mutation idempotent so this demo can be re-verified.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/2e2c7de4-fce1-4f1f-8e6f-6752f58deca6/scratchpad/main-199/backend && grep -q "^#MUTATION" app/api/endpoints/export.py || sed -i "/rate_limit_info: Dict = Depends(get_rate_limiter(limit=10, window=3600)),  # 10 exports per hour/{0,/rate_limit_info/s/^/#MUTATION /}" app/api/endpoints/export.py; git diff app/api/endpoints/export.py | head -12
```

```output
diff --git a/backend/app/api/endpoints/export.py b/backend/app/api/endpoints/export.py
index 26efdd4..132dab9 100644
--- a/backend/app/api/endpoints/export.py
+++ b/backend/app/api/endpoints/export.py
@@ -88,7 +88,7 @@ async def export_book_pdf(
     custom_options: Optional[str] = Query(
         None, description="JSON object of template overrides (font_size, margins, ...)"
     ),
-    rate_limit_info: Dict = Depends(get_rate_limiter(limit=10, window=3600)),  # 10 exports per hour
+#MUTATION     rate_limit_info: Dict = Depends(get_rate_limiter(limit=10, window=3600)),  # 10 exports per hour
 ):
     """
```

Step 2 — run the ENTIRE backend suite on the mutated main. The issue claims this ships green: a real DoS/cost-control regression with zero failing tests.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/2e2c7de4-fce1-4f1f-8e6f-6752f58deca6/scratchpad/main-199/backend && uv run pytest tests/ -q 2>&1 | tail -1 | grep -oE "[0-9]+ passed, [0-9]+ skipped, [0-9]+ warnings"
```

```output
1111 passed, 13 skipped, 11 warnings
```

GREEN: 1111 passed / 13 skipped with the export rate limiter deleted. The regression ships silently — exactly the issue #199 complaint. Step 3 — apply the IDENTICAL mutation to the PR #285 branch and run the new test file.

```bash
cd /home/frankbria/projects/auto-author/backend && grep -q "^#MUTATION" app/api/endpoints/export.py || sed -i "/rate_limit_info: Dict = Depends(get_rate_limiter(limit=10, window=3600)),  # 10 exports per hour/{0,/rate_limit_info/s/^/#MUTATION /}" app/api/endpoints/export.py; echo "mutated source lines: $(grep -c "^#MUTATION" app/api/endpoints/export.py)"; uv run pytest tests/test_api/test_rate_limit_routes.py -q 2>&1 | grep -E "AssertionError: The following|FAILED|failed, .* passed" | sed -E "s/ in [0-9.]+s//; s/=+//g; s/^ +//; s/ +$//"
```

```output
mutated source lines: 1
E   AssertionError: The following routes no longer declare Depends(get_rate_limiter(...)): [('GET', '/api/v1/books/{book_id}/export/pdf')]
FAILED tests/test_api/test_rate_limit_routes.py::TestRateLimitDrivesReal429::test_export_pdf_rate_limited
FAILED tests/test_api/test_rate_limit_routes.py::TestRateLimiterWiringCompleteness::test_every_expected_route_still_declares_the_rate_limiter
2 failed, 4 passed
```

RED on the branch: the behavioral export test fails (3rd request returned 200, not 429) AND the wiring-completeness test names the exact mutated route. Step 4 — restore both source trees and confirm the branch tests go green, with each test name mapping to an acceptance-criteria endpoint class (AI generate, TOC analyze, export, avatar upload).

```bash
cd /home/frankbria/projects/auto-author/backend && git checkout app/api/endpoints/export.py && cd /tmp/claude-1000/-home-frankbria-projects-auto-author/2e2c7de4-fce1-4f1f-8e6f-6752f58deca6/scratchpad/main-199/backend && git checkout app/api/endpoints/export.py && echo "both trees restored; main worktree dirty files: $(git status --porcelain | wc -l)"
```

```output
Updated 1 path from the index
Updated 1 path from the index
both trees restored; main worktree dirty files: 0
```

```bash
cd /home/frankbria/projects/auto-author/backend && uv run pytest tests/test_api/test_rate_limit_routes.py -v 2>&1 | grep -E "PASSED|passed" | sed -E "s/ in [0-9.]+s//; s/ \[ *[0-9]+%\]//; s/=+//g; s/^ +//; s/ +$//"
```

```output
tests/test_api/test_rate_limit_routes.py::TestRateLimitDrivesReal429::test_chapter_generate_questions_rate_limited PASSED
tests/test_api/test_rate_limit_routes.py::TestRateLimitDrivesReal429::test_analyze_summary_rate_limited PASSED
tests/test_api/test_rate_limit_routes.py::TestRateLimitDrivesReal429::test_export_pdf_rate_limited PASSED
tests/test_api/test_rate_limit_routes.py::TestRateLimitDrivesReal429::test_avatar_upload_rate_limited PASSED
tests/test_api/test_rate_limit_routes.py::TestRateLimiterWiringCompleteness::test_every_expected_route_still_declares_the_rate_limiter PASSED
tests/test_api/test_rate_limit_routes.py::TestRateLimiterWiringCompleteness::test_no_unexpected_routes_appeared PASSED
6 passed
```

Step 5 — the acceptance criterion also requires no skipped rate-limit endpoint test remaining: the old @pytest.mark.skip test_export_rate_limiting exists on main but is gone from the branch (superseded by the real test above).

```bash
echo "--- main ---" && git -C /tmp/claude-1000/-home-frankbria-projects-auto-author/2e2c7de4-fce1-4f1f-8e6f-6752f58deca6/scratchpad/main-199 grep -n "test_export_rate_limiting" -- backend/tests | head -1 && echo "--- branch ---" && (git -C /home/frankbria/projects/auto-author grep -n "test_export_rate_limiting" -- backend/tests || echo "no matches on branch")
```

```output
--- main ---
backend/tests/test_api/test_export_endpoints.py:465:    async def test_export_rate_limiting(self, test_book_with_content):
--- branch ---
no matches on branch
```

Demo complete. Outcome evidence per AC: (1) un-skipped integration tests exist for all four protected endpoint classes, each driving the REAL Mongo-backed limiter (small cap of 2) through a production route and asserting the 3rd request returns 429 with the X-RateLimit-*/Retry-After contract; (2) the mutation differential shows the exact regression class the issue names shipping green on main (1111 passed) and failing RED by route name on the branch; (3) the skipped test is removed. The wiring-completeness test extends protection to all 26 rate-limited routes.
