# Upstream report draft — nwsapi `:modal` self-recursion under jsdom

**Not filed.** This is ready to post verbatim at <https://github.com/dperini/nwsapi/issues> and is
kept here because filing publishes under the repo owner's identity. Tracked by
[#589](https://github.com/frankbria/auto-author/issues/589); nothing in this repo depends on it —
the `nwsapi: "2.2.25"` override in `frontend/package.json` is the working fix and stays until
upstream ships one.

Everything below the line is the report. Suggested title:

> `:modal` recurses into itself under jsdom since 2.2.26 — ~500ms per `matches(':modal')` call

---

## Summary

Since `2.2.26`, `Element.prototype.matches(':modal')` under jsdom costs roughly **500ms per call**
on a document containing a single `div`, against **0.01–0.15ms** on `2.2.25` — four orders of
magnitude. `:fullscreen`, `:open`, `:closed`, `:picture-in-picture` and `:popover` share the same
code path and are affected the same way.

The cause is that `matchesNative()` calls back into nwsapi itself under jsdom, recursing until the
JS stack overflows. The resulting `RangeError` is caught and discarded, so the return value is
correct and nothing is logged — the only symptom is the time.

## Reproduction

```js
import { JSDOM } from 'jsdom';                       // jsdom 26.1.0
const dom = new JSDOM('<!doctype html><html><body><div id="x"></div></body></html>');
const el = dom.window.document.getElementById('x');

const t0 = process.hrtime.bigint();
for (let i = 0; i < 5; i++) el.matches(':modal');
console.log(`${(Number(process.hrtime.bigint() - t0) / 1e6 / 5).toFixed(1)} ms/call`);
```

| nwsapi | ms per `matches(':modal')` |
| ------ | ------------------------- |
| 2.2.25 | 0.01 – 0.15               |
| 2.2.26 | ~550                      |
| 2.2.27 | ~500                      |

## It scales with stack size, not DOM size

Nesting depth is irrelevant — a 5-deep and a 25-deep tree both cost ~500ms. The JS stack limit is
what moves it:

| `node --stack-size` | ms per call |
| ------------------- | ----------- |
| 200                 | 17.3        |
| default (~984)      | 367.9       |
| 2000                | 1568.8      |

Linear in stack size, which is the signature of recursion terminated by a stack overflow rather
than by a base case.

## Cause

`2.2.26` introduced `matchesNative` and routed the display-state pseudo-classes through it:

```js
matchesNative =
  function(node, selector) {
    var matcher = _matches || node.matches || node.webkitMatchesSelector ||
      node.mozMatchesSelector || node.msMatchesSelector;
    if (!matcher) return false;
    try {
      return matcher.call(node, selector);
    } catch (e) {
      return false;
    }
  },

isFullscreen =
  function(node) {
    var doc = node.ownerDocument;
    return matchesNative(node, ':fullscreen') || !!(doc && (…));
  },

isModal =
  function(node) {
    return matchesNative(node, ':modal') || isFullscreen(node);
  },
```

`_matches` is assigned in exactly one place — inside `install()`, which the source marks
*"overrides QSA methods (only for browsers)"*:

```js
install =
  function(all) {
    _closest = Element.prototype.closest;
    _matches = Element.prototype.matches;
    …
```

**jsdom does not call `install()`.** It calls nwsapi's `match()` from its own
`Element.prototype.matches` implementation. So `_matches` is `undefined`, `matcher` falls through
to `node.matches`, and `node.matches` *is* nwsapi.

Each `:modal` evaluation therefore re-enters nwsapi, reaches `isModal`, and calls itself again,
several thousand frames deep, until `RangeError: Maximum call stack size exceeded`. `catch (e) {
return false; }` swallows it, `isFullscreen` then runs the same loop for `:fullscreen`, and the
function returns the right answer having burned two full stack unwinds.

In a browser the guard works as intended, because `_matches` holds a genuinely native `matches`.
Under jsdom the fallback chain has no native rung and its first candidate is the caller.

## Observed impact

In a Next.js/React test suite, one `userEvent` keypress against a component that Testing Library
checks for visibility took **12–15 seconds**, with `Element.prototype.matches` call counts of:

```
matches(':fullscreen')   n = 29,999,829
matches(':modal')        n = 30,581
```

A 23-test file went from **1.1s** to **~220s**, with 16 of 23 exceeding a 5000ms timeout. jsdom
reaches nwsapi on a `^2.2.x` range transitively (`jest-environment-jsdom → jsdom → nwsapi`), so a
routine lockfile regeneration is enough to pick this up with no direct dependency on nwsapi
anywhere in the project.

## Suggested fix

`matchesNative` needs to refuse to call back into nwsapi. Any of:

- only use it when `install()` actually captured a native implementation, i.e. drop the
  `node.matches` rung from the fallback chain;
- compare the candidate against the method nwsapi installed and skip it if they are the same
  function;
- guard with a re-entrancy flag around the display-state resolvers.

A regression test that would have caught it: assert that `matches(':modal')` on a plain element in
a non-browser DOM completes in single-digit milliseconds, or that it does not throw and catch a
`RangeError` internally.

## Environment

- nwsapi 2.2.26, 2.2.27 (2.2.25 unaffected)
- jsdom 26.1.0
- Node 24.12.0, Linux
