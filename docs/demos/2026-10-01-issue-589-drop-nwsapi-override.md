# nwsapi override removed: 2.2.28 fixes the :modal recursion (#589)

*2026-10-01T23:23:03Z by Showboat 0.6.1*
<!-- showboat-id: 072aad72-b915-4f02-bb20-525d6d8e4730 -->

Branch `fix/589-drop-nwsapi-override`. The close condition in #589: drop the `nwsapi` override, then confirm `ChapterTab.keyboard.test.tsx` completes in about 1s rather than about 220s.

## Criterion 1 — the override is gone and the lockfile floats

```bash
cd frontend && echo "overrides: $(jq -c .overrides package.json)"; echo "locked nwsapi: $(jq -r ".packages[\"node_modules/nwsapi\"].version" package-lock.json)"; echo "installed nwsapi: $(node -p "require(\"./node_modules/nwsapi/package.json\").version")"; git diff main --stat -- package.json package-lock.json
```

```output
overrides: {"js-yaml@^3":"3.15.2","js-yaml@^4":"4.3.2","@babel/core":"^7.29.0","sharp":"^0.35.4"}
locked nwsapi: 2.2.28
installed nwsapi: 2.2.28
 frontend/package-lock.json | 6 +++---
 frontend/package.json      | 1 -
 2 files changed, 3 insertions(+), 4 deletions(-)
```

## Criterion 2 — the keyboard test runs in about a second

The test runs on this branch's tree with `nwsapi` 2.2.28:

```bash
cd frontend && s=$(date +%s.%N); npx jest src/components/chapters/__tests__/ChapterTab.keyboard.test.tsx 2>&1 | sed "s/\x1b\[[0-9;]*m//g" | grep -E "^Tests:"; printf "wall: %.1fs\n" "$(echo "$(date +%s.%N) - $s" | bc)"
```

```output
Tests:       23 passed, 23 total
wall: 1.8s
```

The control is the same tree with only `nwsapi` swapped to 2.2.27, the last broken release, and restored afterwards. This proves the speed comes from 2.2.28, and that the test still trips if nwsapi regresses:

```bash
cd frontend && T=$(mktemp -d) && cp -r node_modules/nwsapi "$T/keep" && trap "rm -rf node_modules/nwsapi && cp -r \"$T/keep\" node_modules/nwsapi && rm -rf \"$T\"" EXIT && (cd "$T" && npm pack -q nwsapi@2.2.27 >/dev/null && tar xzf nwsapi-2.2.27.tgz) && rm -rf node_modules/nwsapi && cp -r "$T/package" node_modules/nwsapi && echo "swapped in nwsapi $(node -p "require(\"./node_modules/nwsapi/package.json\").version")" && s=$(date +%s) && npx jest src/components/chapters/__tests__/ChapterTab.keyboard.test.tsx 2>&1 | sed "s/\x1b\[[0-9;]*m//g" | grep -E "^Tests:|Exceeded timeout" | sort | uniq -c | sed "s/^ *//"; echo "wall: $(( $(date +%s) - s ))s"
```

```output
swapped in nwsapi 2.2.27
16         thrown: "Exceeded timeout of 5000 ms for a test.
16     thrown: "Exceeded timeout of 5000 ms for a test.
1 Tests:       16 failed, 7 passed, 23 total
wall: 202s
```

## Criterion 3 — the speedup is the upstream fix, not chance

The installed 2.2.28 carries the fix for the reentry described in `claudedocs/nwsapi-2.2.26-modal-recursion.md`: the host matcher is captured once at load, so jsdom's `node.matches` can no longer call back into nwsapi.

```bash
cd frontend/node_modules/nwsapi/src && grep -n "NATIVE_MATCHES = " nwsapi.js && grep -n "node.matches is never consulted" nwsapi.js
```

```output
47:  NATIVE_MATCHES = (function(proto) {
40:  // node.matches is never consulted at match time. A host is free to wire
```

## Evidence summary

| Criterion | Action | Outcome evidence | Status |
|---|---|---|---|
| Override removed; nwsapi floats | read `overrides`, the lockfile and `node_modules` | no `nwsapi` key; locked and installed 2.2.28; diff is 2 files, 3+/4- | VERIFIED |
| Keyboard test completes in about 1s | run `ChapterTab.keyboard.test.tsx` on the branch | 23/23 passed in 1.8s | VERIFIED |
| The difference is nwsapi, and the tripwire still works | same tree, only nwsapi swapped to 2.2.27 | 16 failed (each `Exceeded timeout of 5000 ms`), 7 passed, 202s; restored to 2.2.28 | VERIFIED |
| 2.2.28 contains the upstream fix | grep the installed source | `NATIVE_MATCHES` captured at load; the comment states `node.matches` is never consulted | VERIFIED |
