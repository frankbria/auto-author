# A failure the backend handles and carries on from is still reported (#996)

*2026-10-12T21:38:28Z by Showboat 0.6.1*
<!-- showboat-id: 4eb3de20-7754-4da7-a555-beed88fdf9da -->

Since #808 no log line reaches Sentry, and the SDK reports only what is raised. So a failure the code logs and carries on from is in the container log and nowhere else. This demo runs the real backend from main and from this branch against a database of its own, breaks one thing at a time, and reads what the backend sent to a stand-in for Sentry. Every Stripe value and the session token are made up.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo996/env.sh; echo "main:   $(git -C $MAIN log --oneline -1 | cut -c1-7)"; echo "branch: $(git -C $WT rev-parse --abbrev-ref HEAD)"
```

```output
main:   cfd03d3
branch: feature/issue-996-handled-failures
```

A record of who read a chapter that cannot be written. The collection is made to refuse every insert, and the chapter is read three times. The reader gets the chapter each time, which is right. On main the three failures are log lines and nothing else.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo996/env.sh; database; CODE=$MAIN; q "db.dropDatabase().ok" >/dev/null; backend $CODE BYPASS_AUTH=true E2E_ALLOW_BYPASS=1; BOOK=$(curl -s -m 20 -X POST "$API/books/" -H "content-type: application/json" -d "{\"title\":\"The Lighthouse\"}" | python3 -c "import json,sys; print(json.load(sys.stdin)[\"id\"])"); q "db.books.updateOne({_id: ObjectId(\"$BOOK\")}, {\$set: {table_of_contents: {chapters: [{id: \"ch1\", title: \"TITLE The Lamp\", description: \"d\", content: \"<p>Start.</p>\", order: 1, level: 1, parent_id: null, status: \"draft\", word_count: 1, subchapters: []}], total_chapters: 1, estimated_pages: 1, status: \"edited\"}}}).modifiedCount" >/dev/null; q "db.createCollection(\"chapter_access_logs\"); db.runCommand({collMod: \"chapter_access_logs\", validator: {never_present: {\$exists: true}}}).ok" >/dev/null 2>&1; for i in 1 2 3; do curl -s -m 20 -o /dev/null -w "the chapter is read: %{http_code}\n" "$API/books/$BOOK/chapters/ch1/content"; done; echo "log lines saying the record could not be written: $(grep -c "Failed to log chapter content access" $D/backend.log)"; reported "TITLE The Lamp"; stop
```

```output
the chapter is read: 200
the chapter is read: 200
the chapter is read: 200
log lines saying the record could not be written: 3
reports sent to Sentry: 0
  'TITLE The Lamp' is in what was sent: False
```

On this branch the same three failures are one report: this kind of failure is reported once every five minutes, not once per request. The chapter title that was in the record is not in it.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo996/env.sh; database; CODE=$WT; q "db.dropDatabase().ok" >/dev/null; backend $CODE BYPASS_AUTH=true E2E_ALLOW_BYPASS=1; BOOK=$(curl -s -m 20 -X POST "$API/books/" -H "content-type: application/json" -d "{\"title\":\"The Lighthouse\"}" | python3 -c "import json,sys; print(json.load(sys.stdin)[\"id\"])"); q "db.books.updateOne({_id: ObjectId(\"$BOOK\")}, {\$set: {table_of_contents: {chapters: [{id: \"ch1\", title: \"TITLE The Lamp\", description: \"d\", content: \"<p>Start.</p>\", order: 1, level: 1, parent_id: null, status: \"draft\", word_count: 1, subchapters: []}], total_chapters: 1, estimated_pages: 1, status: \"edited\"}}}).modifiedCount" >/dev/null; q "db.createCollection(\"chapter_access_logs\"); db.runCommand({collMod: \"chapter_access_logs\", validator: {never_present: {\$exists: true}}}).ok" >/dev/null 2>&1; for i in 1 2 3; do curl -s -m 20 -o /dev/null -w "the chapter is read: %{http_code}\n" "$API/books/$BOOK/chapters/ch1/content"; done; echo "log lines saying the record could not be written: $(grep -c "Failed to log chapter content access" $D/backend.log)"; reported "TITLE The Lamp"; stop
```

```output
the chapter is read: 200
the chapter is read: 200
the chapter is read: 200
log lines saying the record could not be written: 3
reports sent to Sentry: 1
  fingerprint ['handled', 'access-log'] | WriteError: Document failed validation
  'TITLE The Lamp' is in what was sent: False
```

A customer with a second live subscription, who is probably being billed twice. Stripe delivers an event for a subscription that is not the one on the account. Both answer 200 and log an error that needs a human. On main nobody is told; on the branch it is reported, by the event to look up and not by who the customer is.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo996/env.sh; database; echo 'main:'; CODE=$MAIN; backend $CODE; q "db.users.insertOne({auth_id: \"auth-demo\", email: \"payer@example.com\", plan: \"pro\", is_active: true, stripe_customer_id: \"cus_DEMO_CUSTOMER\", stripe_subscription_id: \"sub_FIRST\", stripe_subscription_status: \"active\"}).acknowledged" >/dev/null; echo "the webhook answers: $(curl -s -m 15 -X POST -H "content-type: application/json" -H "stripe-signature: $(python3 $D/sign.py $D/event.json $SIGNING)" --data-binary @$D/event.json $API/webhooks/stripe)"; echo "log lines about a second subscription: $(grep -c "second live Stripe subscription" $D/backend.log)"; reported cus_DEMO_CUSTOMER auth-demo payer@example.com; echo; echo 'branch:'; q 'db.dropDatabase().ok' >/dev/null; CODE=$WT; backend $CODE; q "db.users.insertOne({auth_id: \"auth-demo\", email: \"payer@example.com\", plan: \"pro\", is_active: true, stripe_customer_id: \"cus_DEMO_CUSTOMER\", stripe_subscription_id: \"sub_FIRST\", stripe_subscription_status: \"active\"}).acknowledged" >/dev/null; echo "the webhook answers: $(curl -s -m 15 -X POST -H "content-type: application/json" -H "stripe-signature: $(python3 $D/sign.py $D/event.json $SIGNING)" --data-binary @$D/event.json $API/webhooks/stripe)"; echo "log lines about a second subscription: $(grep -c "second live Stripe subscription" $D/backend.log)"; reported cus_DEMO_CUSTOMER auth-demo payer@example.com; stop
```

```output
main:
the webhook answers: {"status":"not_current_subscription","event_id":"evt_demo_second_subscription"}
log lines about a second subscription: 1
reports sent to Sentry: 0
  'cus_DEMO_CUSTOMER' is in what was sent: False
  'auth-demo' is in what was sent: False
  'payer@example.com' is in what was sent: False

branch:
the webhook answers: {"status":"not_current_subscription","event_id":"evt_demo_second_subscription"}
log lines about a second subscription: 1
reports sent to Sentry: 1
  fingerprint ['stripe-webhook', 'second-subscription'] | A customer has a second live Stripe subscription and is likely billed twice (event evt_demo_second_subscription)
  'cus_DEMO_CUSTOMER' is in what was sent: False
  'auth-demo' is in what was sent: False
  'payer@example.com' is in what was sent: False
```

A session that cannot be checked because the database is away. The database is stopped and a signed-in request is made twice. Both are answered 401 after the driver gives up, which is its own problem (filed separately): the user is told to sign in for what is our outage. On main Sentry hears nothing. On the branch it hears once, and the session token is not in it.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo996/env.sh; database; echo 'main:'; CODE=$MAIN; backend $CODE; COOKIE="better-auth.session_token=$(python3 $D/cookie.py SESSION-TOKEN-VALUE $AUTH_SECRET)"; stop_port 27996; for i in 1 2; do curl -s -m 90 -o /dev/null -w "a signed-in request: %{http_code} after %{time_total}s\n" -H "Cookie: $COOKIE" "$API/books/" | sed -E "s/after ([0-9]+)\.[0-9]+s/after about \1 seconds/"; done; echo "log lines saying the session could not be checked: $(grep -c "Error validating session" $D/backend.log)"; reported SESSION-TOKEN-VALUE; echo; echo 'branch:'; database; CODE=$WT; backend $CODE; COOKIE="better-auth.session_token=$(python3 $D/cookie.py SESSION-TOKEN-VALUE $AUTH_SECRET)"; stop_port 27996; for i in 1 2; do curl -s -m 90 -o /dev/null -w "a signed-in request: %{http_code} after %{time_total}s\n" -H "Cookie: $COOKIE" "$API/books/" | sed -E "s/after ([0-9]+)\.[0-9]+s/after about \1 seconds/"; done; echo "log lines saying the session could not be checked: $(grep -c "Error validating session" $D/backend.log)"; reported SESSION-TOKEN-VALUE; stop
```

```output
main:
a signed-in request: 401 after about 30 seconds
a signed-in request: 401 after about 30 seconds
log lines saying the session could not be checked: 2
reports sent to Sentry: 0
  'SESSION-TOKEN-VALUE' is in what was sent: False

branch:
a signed-in request: 401 after about 30 seconds
a signed-in request: 401 after about 30 seconds
log lines saying the session could not be checked: 2
reports sent to Sentry: 1
  fingerprint ['handled', 'session-validation'] | ServerSelectionTimeoutError: 127.0.0.1:27996: [Errno 111] Connection refused (configured timeouts: 
  'SESSION-TOKEN-VALUE' is in what was sent: False
```

The same behaviour as tests, with the real Sentry SDK and a real MongoDB: the function every report goes through, and each group of failures it is now called from, including a file the disk or the storage provider would not delete.

```bash
cd /home/frankbria/projects/worktrees/issue-996-handled-failures/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo996 uv run pytest tests/test_handled_failure_reporting.py -q -p no:cacheprovider --no-cov 2>&1 | tail -1 | sed -E 's/ in [0-9.]*s//; s/, [0-9]+ warnings?//'
```

```output
======================= 24 passed ========================
```
