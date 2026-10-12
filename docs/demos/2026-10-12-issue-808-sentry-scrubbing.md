# A backend error report no longer carries what the user wrote, and one failure is one report (#808)

*2026-10-12T15:25:03Z by Showboat 0.6.1*
<!-- showboat-id: 9c63122d-5d8d-4e9a-a26a-40df215531fd -->

Sentry ran on the SDK defaults: every frame's local variables, the request body, every INFO log line. This demo runs the real backend app with the real Sentry SDK, started the way the app starts it, and sends it one request that fails. The SDK's transport is a list, so the reports can be read and nothing leaves the machine; staging has no DSN (#992), so there is no real project to look at. MongoDB is the local one. The probe runs from an empty directory, as a container does: no git to ask for a release.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo808/env.sh; echo "main:   $(git -C $MAIN log --oneline -1 | cut -c1-7)"; echo "branch: $(git -C $WT rev-parse --abbrev-ref HEAD)"; echo 'what the user typed, sent in the request (the probe looks for each value in everything the SDK sends):'; cat $D/typed.json
```

```output
main:   fd764f0
branch: feature/issue-808-sentry-scrub
what the user typed, sent in the request (the probe looks for each value in everything the SDK sends):
{
 "content": "MANUSCRIPT: it was a dark and stormy night",
 "title": "TITLE: The Lighthouse",
 "prompt": "PROMPT: rewrite my chapter about the lighthouse",
 "email": "writer@example.com",
 "cookie": "SESSION-COOKIE-VALUE",
 "query": "SEARCH-TERM"
}```
```

Before. The request saves a chapter, logs a line, and fails on a duplicate key in MongoDB. Main sends two reports for the one failure, with no release, and every value the user typed is in them.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo808/env.sh; probe $MAIN fail GIT_SHA=0123abc
```

```output
one failed request -> HTTP 500, reports sent to Sentry: 2
  report: a log line via app.api.request_validation, release: None
  report: DuplicateKeyError via logging, release: None
  FOUND   the manuscript text
  FOUND   the chapter title
  FOUND   the email address
  FOUND   the session cookie
  FOUND   the query string
```

After. One report, carrying the release, and none of the values.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo808/env.sh; probe $WT fail GIT_SHA=0123abc
```

```output
one failed request -> HTTP 500, reports sent to Sentry: 1
  report: DuplicateKeyError via logging, release: 0123abc
  absent  the manuscript text
  absent  the chapter title
  absent  the email address
  absent  the session cookie
  absent  the query string
```

What the report still says: the error with MongoDB's message cut before the colliding value, where it happened, the request without its body or query, the cookie filtered, and the database commands with every value replaced. The last breadcrumb carries the request id.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo808/env.sh; probe $WT show GIT_SHA=0123abc
```

```output
what the report still says:
  error:    DuplicateKeyError: E11000 duplicate key error collection: aa_demo_808.users index: email_1
  where:    the route's frame is there: True | innermost: _raise_last_write_error
  locals:   none
  request:  POST http://testserver/__demo/save | body: '' | query: None
  headers:  {'user-agent': 'testclient', 'cookie': '[Filtered]', 'content-type': 'application/json'}
  release:  0123abc | environment: staging
  crumb:    query | {"insert": "chapters", "ordered": true, "documents": [{"title": "%s", "content": "%s", "_id": "%s"}]}
  crumb:    query | {"createIndexes": "users", "indexes": [{"unique": true, "name": "email_1", "key": {"email": 1}}]}
  crumb:    query | {"insert": "users", "ordered": true, "documents": [{"email": "%s", "_id": "%s"}]}
  crumb:    query | {"insert": "users", "ordered": true, "documents": [{"email": "%s", "_id": "%s"}]}
  crumb:    app.api.request_validation | Request failed: POST /__demo/save [ID: efc101b4-c273-4737-af77-ef43f0f11d0e] - Error: DuplicateKeyError, Took:
```

A prompt sent to the model. The call fails (nothing listens on that port) and the app handles it. The SDK's model-client integration reports that failure on its own; on main the prompt is in that report, in the client's frame locals. The report is still sent on this branch, without the prompt.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo808/env.sh; echo 'main:'; probe $MAIN model; echo 'branch:'; probe $WT model
```

```output
main:
a model call that fails and is handled -> HTTP 200, reports sent to Sentry: 1
  report: APIConnectionError via openai
  FOUND   the prompt sent to the model
branch:
a model call that fails and is handled -> HTTP 200, reports sent to Sentry: 1
  report: APIConnectionError via openai
  absent  the prompt sent to the model
```

A refused request. Main logs it as an error, which is a report to Sentry for a client's mistake. The branch logs a warning and sends nothing. The value is in neither log (#800 took it out).

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo808/env.sh; echo 'main:'; probe $MAIN refuse; echo 'branch:'; probe $WT refuse
```

```output
main:
a refused request -> HTTP 422, reports sent to Sentry: 1
  log: ERROR   Validation error: body -> title: Input should be a valid string
  the rejected value is in the log: False
branch:
a refused request -> HTTP 422, reports sent to Sentry: 0
  log: WARNING Validation error: body -> title: Input should be a valid string
  the rejected value is in the log: False
```

The release. The container has no git, so the image build passes the commit in and the image keeps it. Built here from each checkout with the same build argument the workflow now passes.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo808/env.sh; for c in $MAIN $WT; do docker build -q --build-arg GIT_SHA=$(git -C $WT rev-parse HEAD) -t aa-demo-808 $c/backend >/dev/null 2>&1; echo "$([ $c = $MAIN ] && echo main || echo branch) image, GIT_SHA: $(docker run --rm aa-demo-808 printenv GIT_SHA || echo '(not set)')"; done; docker rmi -f aa-demo-808 >/dev/null 2>&1; grep -n 'GIT_SHA' $WT/.github/workflows/build-images.yml | tail -1 | sed 's/^ *//'
```

```output
main image, GIT_SHA: (not set)
branch image, GIT_SHA: fd764f012991a8bfbd65e0b606f8f5f8c54d38a8
134:            GIT_SHA=${{ github.sha }}
```

The same behaviour as tests, with the real SDK, a real MongoDB and the real model client.

```bash
cd /home/frankbria/projects/worktrees/issue-808-sentry-scrub/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo808 uv run pytest tests/test_sentry_scrubbing.py tests/test_sentry_observability.py -q -p no:cacheprovider --no-cov 2>&1 | tail -1 | sed -E 's/ in [0-9.]*s//; s/, [0-9]+ warnings//'
```

```output
======================= 19 passed ========================
```
