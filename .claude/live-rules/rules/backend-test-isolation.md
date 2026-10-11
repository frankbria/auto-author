---
description: Backend test runs share one MongoDB database
globs: ["backend/tests/**"]
prompt: ["pytest", "opencode", "cross-family review"]
priority: 60
---
Every backend test run uses the `auto-author-test` database unless `TEST_MONGO_URI` says otherwise, and
the fixtures drop it between tests. Two runs at once fail each other on unrelated tests. That happened
on #785: a delegated reviewer ran `pytest` while the commit hook was running, the hook failed on a test
the change never touched, and then flaked one run in three.

- While a reviewer, another agent or a worktree may be running tests, give your own runs and commits
  `TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-s<N>`. The variable reaches the pre-commit
  hook. Drop the scratch database when you are done.
- Tell a delegated reviewer to use its own database and to run no git command that writes. A review
  without `--auto` is still not read-only.
- Run mutation checks in a separate worktree while a reviewer is reading the tree, so it never reviews
  mutated code.
- Fixture files carry the names the service writes (`<owner>_<uuid hex>[_thumb].<ext>` for uploads).
  A fixture that invents its own shape tests a looser contract than production has.
- A stand-in for an exception type uses the real class. `service.ClientError = Exception` makes a
  narrow handler look like a blanket one.
- If `mongod` is down the commit hook hangs instead of failing. Ping it before committing.
