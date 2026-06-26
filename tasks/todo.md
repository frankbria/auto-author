# Issue #68 — Fix flaky TabStatePersistence test + raise frontend coverage to 85%

## Reality check (2026-06-25)
- All 65 suites / 896 tests pass; TabStatePersistence currently passes but is flaky (real-timer race on 1s debounce).
- Global coverage: stmt 74.26 / lines 75.33 / func 67.32 / branch 62.26. Targets: stmt 85 / lines 85 / func 85 / branch 75.
- Plan from issue is stale (errorHandler.test.ts & metrics.test.ts already exist; numbers shifted). Reconciled below.

## Task 1 — Flaky test (small)
- Make `saves tab state...` deterministic: fake timers + advanceTimersByTime(1000); restore real timers in afterEach.

## Task 2 — Coverage to 85% global (write tests, by ROI = uncovered lines)
Pure-logic / lib & hooks (best ROI for functions+branches):
- [ ] lib/api/bookClient.ts            (105 uncov, 61%) — biggest win
- [ ] lib/errors/classifier.ts         (49 uncov, 28%)
- [ ] hooks/useTocSync.ts              (42 uncov, 34%)
- [ ] lib/errors/handler.ts            (32 uncov, 8.5%)
- [ ] hooks/usePerformanceTracking.ts  (30 uncov, 42%)
- [ ] lib/security.ts                  (28 uncov, 39%)
- [ ] lib/performance/metrics.ts       (26 uncov, 59%) — expand existing
- [ ] lib/errors/utils.ts              (21 uncov, 16%)
- [ ] lib/loading/timeEstimator.ts     (19 uncov, 59%)
- [ ] lib/errors/index.ts              (18 uncov, 28%)
- [ ] lib/utils/toc-to-tabs-converter.ts (17 uncov, 35%)
- [ ] lib/performance/budgets.ts       (13 uncov, 58%) — expand
Components if still short after libs:
- [ ] components/errors/ErrorNotification.tsx (34 uncov, 15%) — small, easy
- [ ] components/chapters/questions/QuestionDisplay.tsx (56 uncov)

## Task 3 — Verify
- [ ] Full suite green; coverage gate passes with pre-commit thresholds.
- [ ] Flaky test passes repeatedly (determinism confirmed).
