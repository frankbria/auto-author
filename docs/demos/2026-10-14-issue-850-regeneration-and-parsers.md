# Issue #850: regeneration reports what it did, and the parsers keep what the model wrote

*2026-10-14T22:14:37Z by Showboat 0.6.1*
<!-- showboat-id: 7986e9ed-77e9-428a-a2a7-78e0e8c1c8ab -->

`$DEMO/readback.py` runs each checkout's own question service against a scratch local MongoDB database. It seeds a chapter with two answered questions and one unanswered, then regenerates with answers preserved. The model stand-in returns exactly as many questions as it is asked for. Then it parses one numbered question line and one SUGGESTIONS line.

main:

```bash
cd "$MAIN/backend" && DATABASE_URL=mongodb://127.0.0.1:27017 DATABASE_NAME=demo850-main ENVIRONMENT=test PYTHONPATH=. uv run python "$DEMO/readback.py" 2>&1 | grep -E "^(model|reported|stored|question|suggestions)"
```

```output
model asked for       : 3
reported              : preserved=9 new=1 total=10
stored in the chapter : 5
question parsed       : '0. What changed after the move?'
suggestions parsed    : ['Cite Dr', 'Reyes on the 10', '5% figure']
```

this branch:

```bash
cd backend && DATABASE_URL=mongodb://127.0.0.1:27017 DATABASE_NAME=demo850-branch ENVIRONMENT=test PYTHONPATH=. uv run python "$DEMO/readback.py" 2>&1 | grep -E "^(model|reported|stored|question|suggestions)"
```

```output
model asked for       : 1
reported              : preserved=2 new=1 total=3
stored in the chapter : 3
question parsed       : 'What changed after the move?'
suggestions parsed    : ['Cite Dr. Reyes on the 10.5% figure', 'Name the audience']
```

On main one unanswered question became three new ones, so the chapter grew from 3 questions to 5, and the response claimed 9 preserved and 10 in all (the requested 10 minus the 1 deleted, plus 1). On this branch one is replaced by one, and the numbers match the chapter. The other two items in the issue were already fixed on main: the whole-TOC save uses the version guard (#871), and AI_MAX_RETRIES has a floor of 1 (#352). This branch adds a test for the versionless whole-TOC save, which had none.
