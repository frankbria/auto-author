# Issue #798: rate limits are keyed on the route, and the AI quota charges only real generations

*2026-10-12T03:40:52Z by Showboat 0.6.1*
<!-- showboat-id: 8d752061-2158-43bf-878c-bfe0d1abdd68 -->

Two defects. The rate limiter keyed its buckets on the concrete URL, so every book id was a fresh bucket and "10 exports an hour" meant 10 per book. And the AI quota was charged before validation, ownership and the rate limiter ran, so a refused request still spent the daily allowance. This demo runs the branch with real authentication: better-auth on $WEB, the FastAPI backend on $API, and a throwaway local MongoDB database ($DB). The backend is given a daily AI allowance of one, and a small model on a local server stands in for the provider, so one generation is real. `new_account`, `api` (prints a status) and `charged` (generations charged today) are small wrappers defined for this demo. Nothing here touches staging.

**Criterion: the 11th export across two books in one window returns 429.** An author signs up and creates two books; a seed script gives each one short chapter. Eleven Markdown exports follow, alternating between the two books.

```bash
new_account author@example.com "$D/author"
for title in First Second; do api "$D/author" POST /books/ "{\"title\":\"$title\",\"genre\":\"Non-fiction\",\"target_audience\":\"Adults\"}" >/dev/null; python3 -c "import json;print(json.load(open(\"$D/last-body\"))[\"id\"])"; done > "$D/books"
mongosh --quiet "$DATABASE_URL/$DB" "$D/seed-toc.js"
for n in $(seq 1 11); do book=$(sed -n "$(( (n % 2) + 1 ))p" "$D/books"); echo "export $n (book $(( (n % 2) + 1 ))): HTTP $(api "$D/author" GET /books/$book/export/markdown)"; done
mongosh --quiet "$DATABASE_URL/$DB" --eval "db.usage_counters.find({_id:/:rl:.*export/}).forEach(d => print(\"bucket:\", d._id.replace(/^[^:]+/, \"<user>\").replace(/:[0-9]+\$/, \":<window>\"), \"count:\", d.count))"
```

```output
books given a chapter: 2
export 1 (book 2): HTTP 200
export 2 (book 1): HTTP 200
export 3 (book 2): HTTP 200
export 4 (book 1): HTTP 200
export 5 (book 2): HTTP 200
export 6 (book 1): HTTP 200
export 7 (book 2): HTTP 200
export 8 (book 1): HTTP 200
export 9 (book 2): HTTP 200
export 10 (book 1): HTTP 200
export 11 (book 2): HTTP 429
bucket: <user>:rl:/books/{book_id}/export/markdown:<window> count: 11
```

**Criterion: a 4xx or 429 leaves the usage counters unchanged.** Three requests to AI endpoints that are refused before any model call: a book that does not exist, a body that fails validation, and another account's book. The count of generations charged is read before and after.

```bash
BOOK=$(sed -n 1p "$D/books")
echo "charged before: $(charged)"
echo "a book that does not exist: HTTP $(api "$D/author" POST /books/000000000000000000000000/analyze-summary)"
echo "a body that fails validation: HTTP $(api "$D/author" POST /books/$BOOK/chapters/ch1/generate-questions "{\"count\":\"many\"}")"
new_account stranger@example.com "$D/stranger"
echo "another account asking about this book: HTTP $(api "$D/stranger" POST /books/$BOOK/analyze-summary)"
echo "charged after: $(charged)"
```

```output
charged before: 0
a book that does not exist: HTTP 404
a body that fails validation: HTTP 422
another account asking about this book: HTTP 403
charged after: 0
```

A request that does reach the model is charged once, whether the model answers or fails. The book is given a summary and analysed by the local model. Today's counter is cleared first so the attempt starts from zero.

```bash
BOOK=$(sed -n 1p "$D/books")
api "$D/author" PUT /books/$BOOK/summary "{\"summary\":\"A practical guide to container gardening on small urban balconies, covering soil, light, watering and seasonal planting for beginners.\"}" >/dev/null
mongosh --quiet "$DATABASE_URL/$DB" --eval "db.usage_counters.deleteMany({_id:/:day:/})" >/dev/null
echo "charged before: $(charged)"
echo "analysis sent to the model: HTTP $(api "$D/author" POST /books/$BOOK/analyze-summary), charged: $(charged)"
```

```output
charged before: 0
analysis sent to the model: HTTP 200, charged: 1
```

The model answered and one generation is charged. (On an earlier run of this step the small local model returned a cut-off answer, the backend answered 503, and that attempt stayed charged as well: the provider had been called.) The allowance is one a day, so the next two attempts are refused. They are not counted; before this change each refused attempt pushed the counter higher.

```bash
BOOK=$(sed -n 1p "$D/books")
echo "second attempt: HTTP $(api "$D/author" POST /books/$BOOK/analyze-summary), charged: $(charged)"
echo "third attempt: HTTP $(api "$D/author" POST /books/$BOOK/analyze-summary), charged: $(charged)"
python3 -c "import json; print(json.load(open(\"$D/last-body\"))[\"detail\"])"
```

```output
second attempt: HTTP 429, charged: 1
third attempt: HTTP 429, charged: 1
AI usage limit reached (1 generations per day on the free plan). It resets at midnight UTC. Upgrade to Pro for 50 per day.
```

**Tests.** The named tests for this change, against a private test database:

```bash
cd "$WT/backend" && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-s798demo uv run pytest -p no:cacheprovider --no-cov -o addopts="" -v tests/test_api/test_ai_quota_charging.py 2>&1 | grep -E "PASSED|FAILED|ERROR" | sed "s/ *\[ *[0-9]*%\]//; s/.*test_ai_quota_charging.py:://" | sort
```

```output
TestQuotaIsChargedOnlyForARequestThatMayHaveReachedTheModel::test_a_book_that_does_not_exist_costs_nothing PASSED
TestQuotaIsChargedOnlyForARequestThatMayHaveReachedTheModel::test_a_generation_that_fails_in_the_model_call_stays_charged PASSED
TestQuotaIsChargedOnlyForARequestThatMayHaveReachedTheModel::test_a_request_past_the_cap_is_refused_and_not_counted PASSED
TestQuotaIsChargedOnlyForARequestThatMayHaveReachedTheModel::test_a_request_that_fails_validation_costs_nothing PASSED
TestQuotaIsChargedOnlyForARequestThatMayHaveReachedTheModel::test_a_request_the_rate_limiter_refuses_costs_nothing PASSED
TestQuotaIsChargedOnlyForARequestThatMayHaveReachedTheModel::test_a_successful_generation_is_charged_once PASSED
TestQuotaIsChargedOnlyForARequestThatMayHaveReachedTheModel::test_another_users_book_costs_nothing PASSED
TestRateLimitsAreKeyedOnTheRouteNotTheResource::test_a_request_with_no_matched_route_falls_back_to_its_path PASSED
TestRateLimitsAreKeyedOnTheRouteNotTheResource::test_the_eleventh_export_across_two_books_is_refused PASSED
```

Not shown: a request the rate limiter refuses also costs nothing (covered by a test; here the allowance of one is reached first). Each export format still has its own bucket: the limit is per route, so ten Markdown exports and ten PDF exports are both allowed in an hour.
