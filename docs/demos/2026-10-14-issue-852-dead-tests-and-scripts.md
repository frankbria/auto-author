# Issue #852: dead backend tests and scripts are gone, and CI runs each suite once

*2026-10-15T00:58:39Z by Showboat 0.6.1*
<!-- showboat-id: 0dadaaaf-876b-4535-a558-5d91b6f3636b -->

`$DEMO/check.sh` reads one checkout. It counts the tracked dead test and script files this issue removes, the full test passes each CI run makes per stack, the Python CI sets up for the backend against what the backend requires, and what pytest collects.

main:

```bash
"$DEMO/check.sh" "$MAIN"
```

```output
dead test/script files tracked:          20
full backend pytest passes per CI run:   2
full frontend jest passes per CI run:    2
backend CI python:                       python-version: '3.11'
backend requires:                        requires-python = ">=3.13"
pytest collects:                         ======================== 2130 tests collected in 0.43s =========================
```

this branch:

```bash
"$DEMO/check.sh" "$PWD"
```

```output
dead test/script files tracked:          0
full backend pytest passes per CI run:   1
full frontend jest passes per CI run:    1
backend CI python:                       python-version-file: backend/.python-version
backend requires:                        requires-python = ">=3.13"
pytest collects:                         ======================== 2119 tests collected in 0.43s =========================
```

The 11 fewer collected tests are the seven in the three debug files, the three skipped error-handling tests, and the one in test_e2e_no_mocks.py, which ran only with an OpenAI key and asserted nothing. The concurrent-edit file skipped itself at import, so pytest never collected its three. A full coverage run with and without those debug files came out at 94.29% both times, with no line of app/ executed only by them.
