# Issue #847: a write that succeeded answers success when its audit row cannot be written

*2026-10-14T20:24:55Z by Showboat 0.6.1*
<!-- showboat-id: 08543091-1226-43a9-8010-2cac65b019e9 -->

Each checkout's backend is started for real (bypass auth, a scratch local database) with its audit_logs collection created under a validator that refuses every insert (`{$expr: false}`), so every audit write genuinely fails. One book is created, then the database is asked what happened. `$DEMO/run.sh` starts the server, sends the request, counts, and stops the server.

main:

```bash
"$DEMO/run.sh" "$MAIN/backend" 8147 demo847-main
```

```output
POST /books           -> 500
books in the database -> 1
audit rows written    -> 0
```

this branch:

```bash
"$DEMO/run.sh" "$PWD/backend" 8148 demo847-branch
```

```output
POST /books           -> 201
books in the database -> 1
audit rows written    -> 0
Could not audit book_create
```
