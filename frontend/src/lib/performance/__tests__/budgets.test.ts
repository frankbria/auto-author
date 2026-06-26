/**
 * Performance Budgets Test Suite
 *
 * Covers PERFORMANCE_BUDGETS structure, all helper functions, and edge cases.
 */

import {
  PERFORMANCE_BUDGETS,
  getBudget,
  getBudgetsByPriority,
  checkBudget,
  getBudgetStatus,
  getCriticalOperations,
  generateBudgetReport,
  type PerformanceBudget,
} from '../budgets';

// ============================================================================
// PERFORMANCE_BUDGETS structure
// ============================================================================

describe('PERFORMANCE_BUDGETS', () => {
  it('is a non-empty object', () => {
    expect(typeof PERFORMANCE_BUDGETS).toBe('object');
    expect(Object.keys(PERFORMANCE_BUDGETS).length).toBeGreaterThan(0);
  });

  it('contains at least 18 named operations', () => {
    expect(Object.keys(PERFORMANCE_BUDGETS).length).toBeGreaterThanOrEqual(18);
  });

  it('every entry has the required PerformanceBudget fields', () => {
    const requiredFields: (keyof PerformanceBudget)[] = [
      'name',
      'target',
      'warningThreshold',
      'description',
      'priority',
    ];
    for (const [key, budget] of Object.entries(PERFORMANCE_BUDGETS)) {
      for (const field of requiredFields) {
        expect(budget).toHaveProperty(field,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          expect.anything()
        );
        if (budget[field] === undefined || budget[field] === null) {
          throw new Error(`${key}.${field} is null/undefined`);
        }
      }
    }
  });

  it('every entry has a valid priority value of 1, 2, or 3', () => {
    for (const [key, budget] of Object.entries(PERFORMANCE_BUDGETS)) {
      expect([1, 2, 3]).toContain(budget.priority);
    }
  });

  it('every entry has a positive target (> 0)', () => {
    for (const [key, budget] of Object.entries(PERFORMANCE_BUDGETS)) {
      expect(budget.target).toBeGreaterThan(0);
    }
  });

  it('every entry has a warningThreshold between 0 and 1', () => {
    for (const [key, budget] of Object.entries(PERFORMANCE_BUDGETS)) {
      expect(budget.warningThreshold).toBeGreaterThan(0);
      expect(budget.warningThreshold).toBeLessThanOrEqual(1);
    }
  });

  it('includes toc-generation with target 3000ms and priority 1', () => {
    expect(PERFORMANCE_BUDGETS['toc-generation']).toMatchObject({
      name: 'toc-generation',
      target: 3000,
      priority: 1,
    });
  });

  it('includes export-pdf with target 5000ms and priority 1', () => {
    expect(PERFORMANCE_BUDGETS['export-pdf']).toMatchObject({
      name: 'export-pdf',
      target: 5000,
      priority: 1,
    });
  });

  it('includes export-docx with target 5000ms and priority 1', () => {
    expect(PERFORMANCE_BUDGETS['export-docx']).toMatchObject({
      name: 'export-docx',
      target: 5000,
      priority: 1,
    });
  });

  it('includes auto-save with target 1000ms and priority 1', () => {
    expect(PERFORMANCE_BUDGETS['auto-save']).toMatchObject({
      name: 'auto-save',
      target: 1000,
      priority: 1,
    });
  });

  it('includes chapter-load with target 500ms', () => {
    expect(PERFORMANCE_BUDGETS['chapter-load']).toMatchObject({
      name: 'chapter-load',
      target: 500,
    });
  });

  it('includes generate-draft with target 4000ms', () => {
    expect(PERFORMANCE_BUDGETS['generate-draft']).toMatchObject({
      name: 'generate-draft',
      target: 4000,
    });
  });

  it('entry name matches its record key', () => {
    for (const [key, budget] of Object.entries(PERFORMANCE_BUDGETS)) {
      expect(budget.name).toBe(key);
    }
  });
});

// ============================================================================
// getBudget
// ============================================================================

describe('getBudget', () => {
  it('returns the budget for a known operation', () => {
    const budget = getBudget('toc-generation');
    expect(budget).toBeDefined();
    expect(budget!.name).toBe('toc-generation');
    expect(budget!.target).toBe(3000);
  });

  it('returns undefined for an unknown operation', () => {
    expect(getBudget('non-existent-op')).toBeUndefined();
  });

  it('returns undefined for an empty string', () => {
    expect(getBudget('')).toBeUndefined();
  });

  it('returns budgets for all expected known operations', () => {
    const known = ['export-pdf', 'export-docx', 'auto-save', 'book-load', 'chapter-load'];
    for (const op of known) {
      expect(getBudget(op)).toBeDefined();
    }
  });
});

// ============================================================================
// getBudgetsByPriority
// ============================================================================

describe('getBudgetsByPriority', () => {
  it('returns only priority-1 budgets when priority=1', () => {
    const results = getBudgetsByPriority(1);
    expect(results.length).toBeGreaterThan(0);
    for (const budget of results) {
      expect(budget.priority).toBe(1);
    }
  });

  it('returns only priority-2 budgets when priority=2', () => {
    const results = getBudgetsByPriority(2);
    expect(results.length).toBeGreaterThan(0);
    for (const budget of results) {
      expect(budget.priority).toBe(2);
    }
  });

  it('returns only priority-3 budgets when priority=3', () => {
    const results = getBudgetsByPriority(3);
    expect(results.length).toBeGreaterThan(0);
    for (const budget of results) {
      expect(budget.priority).toBe(3);
    }
  });

  it('priority-1 set includes toc-generation and export-pdf', () => {
    const p1 = getBudgetsByPriority(1).map((b) => b.name);
    expect(p1).toContain('toc-generation');
    expect(p1).toContain('export-pdf');
  });

  it('all three priority sets together cover all budgets', () => {
    const total =
      getBudgetsByPriority(1).length +
      getBudgetsByPriority(2).length +
      getBudgetsByPriority(3).length;
    expect(total).toBe(Object.keys(PERFORMANCE_BUDGETS).length);
  });
});

// ============================================================================
// checkBudget
// ============================================================================

describe('checkBudget', () => {
  it('returns exceeded=false when duration is below the target', () => {
    const result = checkBudget('toc-generation', 2000);
    expect(result.exceeded).toBe(false);
    expect(result.overrun).toBe(0);
  });

  it('returns exceeded=true when duration exceeds the target', () => {
    const result = checkBudget('toc-generation', 3500);
    expect(result.exceeded).toBe(true);
    expect(result.overrun).toBe(500);
  });

  it('returns the target as the budget value', () => {
    const result = checkBudget('toc-generation', 1000);
    expect(result.budget).toBe(3000);
  });

  it('calculates the percentage relative to target', () => {
    const result = checkBudget('toc-generation', 2000);
    expect(result.percentage).toBe(67); // 2000/3000 * 100 ≈ 66.67 → 67
  });

  it('calculates percentage > 100 when exceeded', () => {
    const result = checkBudget('toc-generation', 4500);
    expect(result.percentage).toBe(150); // 4500/3000 * 100 = 150
  });

  it('shouldWarn=true when duration exceeds the warningThreshold', () => {
    // toc-generation threshold = 0.8 → warn at 2400ms
    const result = checkBudget('toc-generation', 2500);
    expect(result.shouldWarn).toBe(true);
  });

  it('shouldWarn=false when duration is below the warningThreshold', () => {
    const result = checkBudget('toc-generation', 2000); // < 2400ms
    expect(result.shouldWarn).toBe(false);
  });

  it('shouldWarn=true when the budget is exceeded (implies threshold crossed)', () => {
    const result = checkBudget('toc-generation', 4000);
    expect(result.shouldWarn).toBe(true);
    expect(result.exceeded).toBe(true);
  });

  it('returns all zero/null values for unknown operations', () => {
    const result = checkBudget('no-such-op', 5000);
    expect(result.exceeded).toBe(false);
    expect(result.budget).toBeNull();
    expect(result.overrun).toBe(0);
    expect(result.percentage).toBe(0);
    expect(result.shouldWarn).toBe(false);
  });

  it('overrun is 0 even when budget not set', () => {
    const result = checkBudget('unknown', 9999);
    expect(result.overrun).toBe(0);
  });

  it('handles duration exactly at the target boundary (not exceeded)', () => {
    // duration == target → duration > target is false
    const result = checkBudget('auto-save', 1000); // target = 1000
    expect(result.exceeded).toBe(false);
    expect(result.overrun).toBe(0);
  });

  it('handles duration one ms over the target (exceeded)', () => {
    const result = checkBudget('auto-save', 1001);
    expect(result.exceeded).toBe(true);
    expect(result.overrun).toBe(1);
  });
});

// ============================================================================
// getBudgetStatus
// ============================================================================

describe('getBudgetStatus', () => {
  it('includes the operation name and duration in every message', () => {
    const status = getBudgetStatus('toc-generation', 1500);
    expect(status).toContain('toc-generation');
    expect(status).toContain('1500ms');
  });

  it('returns "no budget defined" for unknown operations', () => {
    const status = getBudgetStatus('no-such-op', 500);
    expect(status).toContain('no budget defined');
    expect(status).toContain('no-such-op');
    expect(status).toContain('500ms');
  });

  it('includes EXCEEDED wording when the budget is exceeded', () => {
    const status = getBudgetStatus('toc-generation', 4000); // > 3000
    expect(status).toContain('EXCEEDED');
    expect(status).toContain('3000ms');
  });

  it('includes the overrun amount when exceeded', () => {
    const status = getBudgetStatus('toc-generation', 3500);
    expect(status).toContain('500ms'); // overrun
  });

  it('includes "Near budget limit" when within budget but above warning threshold', () => {
    // toc-generation: target=3000, warnAt=2400
    const status = getBudgetStatus('toc-generation', 2600);
    expect(status).toContain('Near budget limit');
  });

  it('includes "Within budget" when well under the warning threshold', () => {
    const status = getBudgetStatus('toc-generation', 1000);
    expect(status).toContain('Within budget');
  });

  it('includes the budget target in the message for known operations', () => {
    const status = getBudgetStatus('auto-save', 500);
    expect(status).toContain('1000ms'); // auto-save target
  });

  it('includes the percentage in the status message', () => {
    const status = getBudgetStatus('toc-generation', 1500);
    // 1500/3000*100 = 50%
    expect(status).toContain('50%');
  });
});

// ============================================================================
// getCriticalOperations
// ============================================================================

describe('getCriticalOperations', () => {
  it('returns an array', () => {
    expect(Array.isArray(getCriticalOperations())).toBe(true);
  });

  it('returns only priority-1 operations', () => {
    const ops = getCriticalOperations();
    for (const op of ops) {
      expect(op.priority).toBe(1);
    }
  });

  it('includes known critical operations', () => {
    const names = getCriticalOperations().map((o) => o.name);
    expect(names).toContain('toc-generation');
    expect(names).toContain('export-pdf');
    expect(names).toContain('auto-save');
    expect(names).toContain('generate-draft');
  });

  it('is the same set as getBudgetsByPriority(1)', () => {
    const critical = getCriticalOperations().map((o) => o.name).sort();
    const p1 = getBudgetsByPriority(1).map((o) => o.name).sort();
    expect(critical).toEqual(p1);
  });
});

// ============================================================================
// generateBudgetReport
// ============================================================================

describe('generateBudgetReport', () => {
  it('returns an array with all budget entries', () => {
    const report = generateBudgetReport();
    expect(report.length).toBe(Object.keys(PERFORMANCE_BUDGETS).length);
  });

  it('sorts by priority first (priority 1 before priority 2)', () => {
    const report = generateBudgetReport();
    const p1End = report.findIndex((b) => b.priority !== 1);
    const p2End = report.findIndex((b) => b.priority !== 1 && b.priority !== 2);

    // All p1 entries come before p2 entries
    if (p1End > -1 && p2End > -1) {
      expect(p1End).toBeLessThan(p2End);
    }
  });

  it('sorts priority 2 before priority 3', () => {
    const report = generateBudgetReport();
    const p3Start = report.findIndex((b) => b.priority === 3);
    const p2Start = report.findIndex((b) => b.priority === 2);
    if (p3Start > -1 && p2Start > -1) {
      expect(p2Start).toBeLessThan(p3Start);
    }
  });

  it('within the same priority, sorts by target (ascending)', () => {
    const report = generateBudgetReport();
    const p1Ops = report.filter((b) => b.priority === 1);
    for (let i = 1; i < p1Ops.length; i++) {
      expect(p1Ops[i].target).toBeGreaterThanOrEqual(p1Ops[i - 1].target);
    }
  });

  it('first entry is a priority-1 operation', () => {
    const report = generateBudgetReport();
    expect(report[0].priority).toBe(1);
  });

  it('all entries are PerformanceBudget-shaped', () => {
    const report = generateBudgetReport();
    for (const entry of report) {
      expect(entry).toHaveProperty('name');
      expect(entry).toHaveProperty('target');
      expect(entry).toHaveProperty('warningThreshold');
      expect(entry).toHaveProperty('description');
      expect(entry).toHaveProperty('priority');
    }
  });

  it('contains the same entries as PERFORMANCE_BUDGETS (just reordered)', () => {
    const report = generateBudgetReport().map((b) => b.name).sort();
    const all = Object.keys(PERFORMANCE_BUDGETS).sort();
    expect(report).toEqual(all);
  });
});
