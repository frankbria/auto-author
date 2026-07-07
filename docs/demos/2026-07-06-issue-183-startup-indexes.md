# Issue #183: DB indexes created at startup + 90-day access-log TTL

*2026-07-07T01:00:14Z*

Setup: real local MongoDB, fresh demo database `auto-author-demo-183`, real uvicorn. Act 1 boots the app from `main` (the buggy state); Act 2 boots the PR branch. Same env for both: `DATABASE_NAME=auto-author-demo-183`, `BYPASS_AUTH=false`.

```bash
mongosh --quiet --eval "db.getSiblingDB(\"auto-author-demo-183\").dropDatabase().ok"
```

```output
1
```

## Act 1 — `main`: startup builds no book/access-log indexes

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/d4a52a66-9409-4412-bdb7-4da12ab36cb3/scratchpad/aa-main && git log --oneline -1
```

```output
adc5e14 [P1.2] Surface AI question-generation failures as structured errors; tag template fallbacks (#182) (#233)
```

Real uvicorn booted from `main` on port 8183 against the fresh demo DB (startup log shows only question indexes being created). Seed a book and an access-log row the way the app would, then list the indexes MongoDB actually has:

```bash
curl -s http://localhost:8183/ && echo && mongosh --quiet --eval "
const db2 = db.getSiblingDB(\"auto-author-demo-183\");
db2.books.insertOne({owner_id: \"user-1\", title: \"Demo Book\"});
db2.chapter_access_logs.insertOne({user_id: \"user-1\", book_id: \"b1\", chapter_id: \"c1\", access_type: \"read_content\", timestamp: new Date()});
print(\"books indexes:\", JSON.stringify(db2.books.getIndexes().map(i=>i.name)));
print(\"chapter_access_logs indexes:\", JSON.stringify(db2.chapter_access_logs.getIndexes().map(i=>i.name)));"
```

```output
{"message":"Welcome to the Auto Author API!"}
books indexes: ["_id_"]
chapter_access_logs indexes: ["_id_"]
```

Only the default `_id_` index exists — the dashboard `find({owner_id})` collection-scans, and nothing will ever expire access logs. Confirm with the query planner:

```bash
mongosh --quiet --eval "
const db2 = db.getSiblingDB(\"auto-author-demo-183\");
const plan = db2.books.find({owner_id: \"user-1\"}).explain().queryPlanner.winningPlan;
print(\"winning plan stage:\", plan.stage || plan.inputStage.stage);"
```

```output
winning plan stage: COLLSCAN
```

## Act 2 — PR branch: startup creates the indexes

```bash
git log --oneline -1
```

```output
1d546d9 review: log startup index failure, public get_database(), pin partial filter
```

Same env, same demo DB (still holding the Act 1 data), app booted from the PR branch on port 8184. Startup log now shows the chapter-tab index creation:

```bash
grep -E "indexing_strategy" /tmp/claude-1000/-home-frankbria-projects-auto-author/d4a52a66-9409-4412-bdb7-4da12ab36cb3/scratchpad/branch-uvicorn.log | sed "s/.*INFO - //" | head -9
```

```output
Starting index creation for chapter tabs functionality...
Created index: user_book_timestamp_idx
Created index: book_chapter_timestamp_idx
Created index: user_access_type_timestamp_idx
Created index: user_book_access_type_idx
Created index: access_logs_ttl_idx
Created index: owner_book_id_idx
Created index: owner_updated_idx
Index creation completed successfully
```

MongoDB now has the owner indexes and the 90-day TTL (`expireAfterSeconds: 7776000`), and the dashboard query uses an index scan instead of a collection scan:

```bash
mongosh --quiet --eval "
const db2 = db.getSiblingDB(\"auto-author-demo-183\");
print(\"books indexes:\", JSON.stringify(db2.books.getIndexes().map(i=>i.name)));
const ttl = db2.chapter_access_logs.getIndexes().find(i=>i.name===\"access_logs_ttl_idx\");
print(\"TTL index:\", JSON.stringify({name: ttl.name, key: ttl.key, expireAfterSeconds: ttl.expireAfterSeconds}));
const plan = db2.books.find({owner_id: \"user-1\"}).explain().queryPlanner.winningPlan;
print(\"winning plan stage:\", JSON.stringify(plan.inputStage ? {stage: plan.stage, inputStage: plan.inputStage.stage, index: plan.inputStage.indexName} : plan.stage));"
```

```output
books indexes: ["_id_","owner_book_id_idx","owner_updated_idx"]
TTL index: {"name":"access_logs_ttl_idx","key":{"timestamp":1},"expireAfterSeconds":7776000}
winning plan stage: {"stage":"FETCH","inputStage":"IXSCAN","index":"owner_book_id_idx"}
```

## Act 3 — the TTL genuinely expires old access logs. Insert a row stamped 100 days ago next to the fresh Act 1 row, then wait for the TTL monitor (runs every ~60s):

```bash
mongosh --quiet --eval "
const db2 = db.getSiblingDB(\"auto-author-demo-183\");
db2.chapter_access_logs.insertOne({user_id: \"user-1\", book_id: \"b1\", chapter_id: \"c1\", access_type: \"read_content\", timestamp: new Date(Date.now() - 100*24*3600*1000)});
print(\"access-log rows now:\", db2.chapter_access_logs.countDocuments({}));"
```

```output
access-log rows now: 2
```

```bash
for i in $(seq 1 24); do
  n=$(mongosh --quiet --eval "db.getSiblingDB(\"auto-author-demo-183\").chapter_access_logs.countDocuments({})")
  if [ "$n" = "1" ]; then echo "after ${i}x5s: expired row deleted by TTL monitor — rows remaining: $n (the fresh row survives)"; exit 0; fi
  sleep 5
done; echo "TTL did not fire within 120s — rows: $n"; exit 1
```

```output
after 9x5s: expired row deleted by TTL monitor — rows remaining: 1 (the fresh row survives)
```

## Act 4 — second startup is idempotent. The app was restarted against the same DB (indexes already exist): startup completes cleanly, zero errors, indexes intact:

```bash
grep -E "Startup tasks completed|Application startup complete" /tmp/claude-1000/-home-frankbria-projects-auto-author/d4a52a66-9409-4412-bdb7-4da12ab36cb3/scratchpad/branch-uvicorn-2.log | sed "s/.*INFO[ :-]*//";
echo "ERROR lines in restart log: $(grep -c ERROR /tmp/claude-1000/-home-frankbria-projects-auto-author/d4a52a66-9409-4412-bdb7-4da12ab36cb3/scratchpad/branch-uvicorn-2.log)";
mongosh --quiet --eval "
const db2 = db.getSiblingDB(\"auto-author-demo-183\");
print(\"books indexes:\", JSON.stringify(db2.books.getIndexes().map(i=>i.name)));
print(\"access-log indexes:\", JSON.stringify(db2.chapter_access_logs.getIndexes().map(i=>i.name)));"
```

```output
Startup tasks completed
Application startup complete.
ERROR lines in restart log: 0
books indexes: ["_id_","owner_book_id_idx","owner_updated_idx"]
access-log indexes: ["_id_","user_book_timestamp_idx","book_chapter_timestamp_idx","user_access_type_timestamp_idx","user_book_access_type_idx","access_logs_ttl_idx"]
```

All four acceptance criteria demonstrated: (1) `create_all_indexes()` runs at lifespan startup and is idempotent (Acts 2+4); (2) the 90-day TTL index exists — `expireAfterSeconds: 7776000` — and genuinely deletes expired rows (Act 3); (3) `owner_id` + TTL indexes exist after startup, flipping the dashboard query from COLLSCAN to IXSCAN (Acts 1 vs 2). Automated pin: `backend/tests/test_startup_indexes.py` (4 tests, incl. a real-lifespan run).
