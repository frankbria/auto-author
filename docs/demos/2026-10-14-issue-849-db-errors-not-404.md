# Issue #849: a database that cannot be asked is not a book that is not there

*2026-10-14T21:57:59Z by Showboat 0.6.1*
<!-- showboat-id: b88509c0-53f8-47b4-966e-3eec6eaac9d3 -->

Each checkout's backend is started for real (bypass auth) against a scratch mongod on port 27117 started with `--setParameter enableTestCommands=1`. A book is created. Then MongoDB's own `failCommand` failpoint makes every `find` on that database's `books` collection fail with ShutdownInProgress (code 91), while every other collection keeps answering, and the book is requested. `$DEMO/run.sh` does all of it and turns the failpoint off again.

main:

```bash
"$DEMO/run.sh" "$MAIN/backend" 8147 demo849-main
```

```output
database answering:  GET /books/{id}/toc  -> 200
books find failing:  GET /books/{id}     {"detail":"Book not found"} -> 404
books find failing:  GET /books/{id}/chapters/tab-state {"detail":"Book not found"} -> 404
book still stored:   1
```

this branch:

```bash
"$DEMO/run.sh" "$PWD/backend" 8148 demo849-branch
```

```output
database answering:  GET /books/{id}/toc  -> 200
books find failing:  GET /books/{id}     {"detail":"Failed to retrieve book"} -> 500
books find failing:  GET /books/{id}/chapters/tab-state {"detail":"Failed to retrieve tab state"} -> 500
book still stored:   1
```

On main a book that is still stored is answered 404 "Book not found" while the database cannot be read, and the client stops retrying. On this branch the same moment is a 500 with the route's fixed message, and no MongoDB text reaches the response.
